"""Bounded real Chromium rendering and source-PDF comparisons for Standard HTML."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from converter.errors import fail
from converter.pdf_export.process import run_process
from converter.sec_validation.profile import valid_filename
from converter.sec_validation.validator import read_bounded
from converter.visual_validation.browser import browser_cache


def verify_standard(source, directory, generation, workspace, context):
    workspace = workspace.resolve()
    workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
    inputs = workspace / "input"
    inputs.mkdir(mode=0o700)
    names = [generation["filename"], *generation["assets"]]
    edgar = generation.get("method") in {"efm78-flow-css2-v1", "efm78-layered-css2-v1"}
    valid_names = (
        valid_filename(names[0], (".htm",))
        and all(re.fullmatch(r"image[0-9]{3,}\.(jpg|gif)", n) for n in names[1:])
        if edgar
        else names[0] == "document.html"
        and all(re.fullmatch(r"image[0-9]{4,}\.(jpg|png|gif|webp)", n) for n in names[1:])
    )
    if not valid_names:
        raise ValueError("Invalid Standard resource manifest")
    total = 0
    for name in names:
        data = read_bounded(directory / name, 32 * 1024 * 1024)
        expected = (
            generation["sha256"] if name == generation["filename"] else generation["assets"][name]["sha256"]
        )
        if hashlib.sha256(data).hexdigest() != expected:
            raise fail(
                "STANDARD_OUTPUT_CHANGED",
                "comparing_formatting",
                "Generated HTML or image changed",
                "Regenerate the current attempt",
            )
        total += len(data)
        if total > 160 * 1024 * 1024:
            raise ValueError("Standard capture input budget")
        (inputs / name).write_bytes(data)
    source_data = read_bounded(source, 64 * 1024 * 1024)
    if hashlib.sha256(source_data).hexdigest() != generation["source_pdf_sha256"]:
        raise fail(
            "STANDARD_SOURCE_CHANGED", "comparing_formatting", "Source PDF changed", "Re-analyze the input"
        )
    (inputs / "reference.pdf").write_bytes(source_data)
    request = {
        "workspace": str(workspace.resolve()),
        "names": names,
        "generation": generation,
        "browser_cache": str(browser_cache().resolve()),
    }
    request_path = workspace / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    run_process(
        [sys.executable, "-m", "converter.standard_visual", str(request_path.resolve())],
        workspace,
        context,
        120,
        1280 * 1024 * 1024,
        65536,
        workspace,
        384 * 1024 * 1024,
    )
    result = json.loads(read_bounded(workspace / "control.json", 65536))
    if result.get("error"):
        code = result["error"]
        if edgar and code.startswith("STANDARD_"):
            code = "EDGAR_" + code.removeprefix("STANDARD_")
        raise fail(
            code,
            "comparing_formatting",
            "EDGAR flow loses printed words or moves word origins by more than six points"
            if code == "EDGAR_LAYOUT_INCOMPATIBLE"
            else "Mixed page dimensions cannot be printed by the current EDGAR flow renderer"
            if code == "EDGAR_MIXED_PRINT_GEOMETRY_UNSUPPORTED"
            else "EDGAR browser rendering or source comparison failed"
            if edgar
            else "Standard browser rendering or source comparison failed",
            "Review browser availability and page diagnostics",
        )
    return json.loads((workspace / "comparison.json").read_text(encoding="utf-8"))


def worker(request):
    import mimetypes
    from importlib.metadata import version
    from importlib.resources import files

    import numpy as np
    import pymupdf
    from PIL import Image
    from playwright.sync_api import sync_playwright

    from converter.visual_validation.browser_worker import FLAGS

    if version("playwright") != "1.64.1":
        return {"error": "STANDARD_BROWSER_PROFILE_MISMATCH"}
    profiles = json.loads(
        files("playwright").joinpath("driver/package/browsers.json").read_text(encoding="utf-8")
    )
    expected_version = next(
        item["browserVersion"] for item in profiles["browsers"] if item["name"] == "chromium"
    )

    root = Path(request["workspace"])
    generation = request["generation"]
    edgar = generation.get("method") in {"efm78-flow-css2-v1", "efm78-layered-css2-v1"}
    selector = "body > div" if edgar else "section.page"
    resources = {name: (root / "input" / name).read_bytes() for name in request["names"]}
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = request["browser_cache"]
    # Keep editor preload hooks and terminal color notices out of the renderer.
    for key in ("NODE_OPTIONS", "NODE_PATH", "FORCE_COLOR"):
        os.environ.pop(key, None)
    denied, served, artifacts, results = [], set(), [], []
    dimensions = generation["pages"]
    pixels = sum(math.ceil(p["width_pt"] * 4 / 3) * math.ceil(p["height_pt"] * 4 / 3) for p in dimensions)
    if pixels > 64_000_000:
        return {"error": "STANDARD_VISUAL_PIXEL_LIMIT"}

    def stats(reference, candidate):
        if reference.size != candidate.size:
            return {"dimensions_match": False, "pixel_identical": False}
        difference = np.abs(np.asarray(reference, dtype=np.int16) - np.asarray(candidate, dtype=np.int16))
        return {
            "dimensions_match": True,
            "pixel_identical": not bool(difference.any()),
            "changed_pixels": int(np.any(difference, axis=2).sum()),
            "mean_absolute_channel_error": float(difference.mean()),
            "max_channel_error": int(difference.max()),
        }

    with sync_playwright() as playwright:
        if not Path(playwright.chromium.executable_path).is_file():
            return {"error": "STANDARD_BROWSER_UNAVAILABLE"}
        browser = playwright.chromium.launch(headless=True, chromium_sandbox=True, args=FLAGS)
        try:
            if browser.version != expected_version:
                return {"error": "STANDARD_BROWSER_PROFILE_MISMATCH"}
            context = browser.new_context(
                java_script_enabled=False,
                service_workers="block",
                accept_downloads=False,
                viewport={
                    "width": math.ceil(max(p["width_pt"] for p in dimensions) * 4 / 3) + 32,
                    "height": 1200,
                },
                device_scale_factor=1,
                locale="en-US",
                timezone_id="UTC",
                color_scheme="light",
            )

            def route(route):
                url = urlsplit(route.request.url)
                name = url.path.lstrip("/")
                if (
                    url.scheme == "https"
                    and url.netloc == "convx.invalid"
                    and not url.query
                    and name in resources
                    and route.request.method == "GET"
                ):
                    served.add(name)
                    route.fulfill(
                        status=200,
                        body=resources[name],
                        content_type="text/html; charset=utf-8"
                        if name.endswith((".html", ".htm"))
                        else mimetypes.guess_type(name)[0] or "application/octet-stream",
                    )
                elif url.path == "/favicon.ico" and url.netloc == "convx.invalid":
                    route.fulfill(status=204, body=b"")
                else:
                    denied.append(route.request.resource_type)
                    route.abort()

            context.route("**/*", route)
            page = context.new_page()
            page.set_default_timeout(30000)
            page.goto("https://convx.invalid/" + generation["filename"], wait_until="load")
            page.evaluate("async () => { await document.fonts.ready; }")
            metrics = page.evaluate(
                """({selector,edgar}) => ({nodes:document.getElementsByTagName('*').length,
                pages:Array.from(document.querySelectorAll(selector)).map(p=>({width:p.getBoundingClientRect().width,height:p.getBoundingClientRect().height,
                text:edgar?p.textContent:Array.from(p.querySelectorAll('svg text')).map(t=>t.textContent).join('')}))})""",
                {"selector": selector, "edgar": edgar},
            )
            if metrics["nodes"] > 200000 or len(metrics["pages"]) != len(dimensions):
                return {"error": "STANDARD_BROWSER_LAYOUT_LIMIT"}
            for actual, expected in zip(metrics["pages"], dimensions, strict=True):
                if (
                    hashlib.sha256(actual["text"].encode()).hexdigest() != expected["text_sha256"]
                    or abs(actual["width"] - expected["width_pt"] * 4 / 3) > 0.1
                    or abs(actual["height"] - expected["height_pt"] * 4 / 3) > 0.1
                ):
                    return {"error": "STANDARD_BROWSER_CONTENT_MISMATCH"}
            print_options = {}
            if edgar:
                first = dimensions[0]
                if any(
                    p["width_pt"] != first["width_pt"] or p["height_pt"] != first["height_pt"]
                    for p in dimensions
                ):
                    return {"error": "EDGAR_MIXED_PRINT_GEOMETRY_UNSUPPORTED"}
                print_options = {
                    "width": f"{first['width_pt'] / 72}in",
                    "height": f"{first['height_pt'] / 72}in",
                    "margin": {"top": "0", "bottom": "0", "left": "0", "right": "0"},
                }
            page.pdf(
                path=str(root / "rendered.pdf"),
                print_background=True,
                prefer_css_page_size=True,
                **print_options,
            )
            page.emulate_media(media="screen")
            with (
                pymupdf.open(root / "input/reference.pdf") as source,
                pymupdf.open(root / "rendered.pdf") as printed,
            ):
                if printed.page_count != source.page_count:
                    return {"error": "STANDARD_PRINT_PAGE_MISMATCH"}
                for index, expected in enumerate(dimensions):
                    word_geometry = None
                    if edgar:
                        # Independent actual print check: no blur, shift or tolerance
                        # correction is applied to the raw pixel comparisons below.
                        from converter.edgar_words import word_geometry as measure_words

                        layered = generation.get("method") == "efm78-layered-css2-v1"
                        word_geometry = measure_words(
                            source[index],
                            printed[index],
                            layered,
                            generation.get("reflow_targets", {}).get(str(index + 1)) if layered else None,
                        )
                        if word_geometry["missing_words"] or word_geometry["max_origin_error_pt"] > 6:
                            return {"error": "EDGAR_LAYOUT_INCOMPATIBLE", "page": index + 1, **word_geometry}
                    if any(
                        abs(a - b) > 0.1
                        for a, b in zip(
                            (printed[index].rect.width, printed[index].rect.height),
                            (expected["width_pt"], expected["height_pt"]),
                            strict=True,
                        )
                    ):
                        return {"error": "STANDARD_PRINT_GEOMETRY_MISMATCH"}
                    screen_name = f"page{index + 1:04d}.screen.png"
                    page.locator(selector).nth(index).screenshot(
                        path=str(root / screen_name), animations="disabled"
                    )
                    artifacts.append(screen_name)
                    with Image.open(root / screen_name) as captured:
                        screen = captured.convert("RGB")
                    native = source[index].get_pixmap(
                        matrix=pymupdf.Matrix(4 / 3, 4 / 3), colorspace=pymupdf.csRGB, alpha=False
                    )
                    reference = Image.frombytes("RGB", (native.width, native.height), native.samples)
                    native_print = printed[index].get_pixmap(
                        matrix=pymupdf.Matrix(4 / 3, 4 / 3), colorspace=pymupdf.csRGB, alpha=False
                    )
                    print_image = Image.frombytes(
                        "RGB", (native_print.width, native_print.height), native_print.samples
                    )
                    screen_stats, print_stats = stats(reference, screen), stats(reference, print_image)
                    if screen.size == reference.size:
                        name = f"page{index + 1:04d}.overlay.png"
                        Image.blend(reference, screen, 0.5).save(root / name)
                        artifacts.append(name)
                    if print_image.size == reference.size:
                        name = f"page{index + 1:04d}.print-diff.png"
                        diff = np.abs(
                            np.asarray(reference, dtype=np.int16) - np.asarray(print_image, dtype=np.int16)
                        )
                        Image.fromarray(np.uint8(np.minimum(diff * 4, 255))).save(root / name)
                        artifacts.append(name)
                    results.append(
                        {
                            "page": index + 1,
                            "screen": screen_stats,
                            "print": print_stats,
                            **({"word_geometry": word_geometry} if edgar else {}),
                        }
                    )
            if denied or served != set(resources):
                return {"error": "STANDARD_BROWSER_RESOURCE_MISMATCH"}
            identical = all(p["screen"]["pixel_identical"] and p["print"]["pixel_identical"] for p in results)
            if generation.get("method") == "efm78-layered-css2-v1":
                artifacts.append("rendered.pdf")
            report = {
                "method": "chromium-edgar-flow-screen-print-v1"
                if edgar
                else "chromium-standard-screen-print-v1",
                "checks_complete": True,
                "pages": results,
                "source_pdf_sha256": generation["source_pdf_sha256"],
                "html_sha256": generation["sha256"],
                "pixel_equivalence_verified": identical,
                "artifacts": artifacts,
                "artifact_sha256": {
                    name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in artifacts
                },
                "browser_version": browser.version,
                "text_verified": True,
                "page_geometry_verified": True,
                "network_requests_denied": len(denied),
                "diagnostics": []
                if identical
                else [
                    {
                        "code": "EDGAR_VISUAL_DIFFERENCES" if edgar else "STANDARD_VISUAL_DIFFERENCES",
                        "severity": "warning",
                        "stage": "comparing_formatting",
                        "description": "Actual browser screen/print pixels differ from the source PDF; inspect the measured per-page differences. Exact visual equivalence is not claimed.",
                    }
                ],
            }
            (root / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            return {"ok": True}
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = worker(request)
    except Exception:
        result = {"error": "STANDARD_BROWSER_FAILED"}
    (Path(sys.argv[1]).resolve().parent / "control.json").write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result))
