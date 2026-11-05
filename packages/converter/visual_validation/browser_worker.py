"""Trusted child process. Never executes document scripts or opens document paths in Chromium."""

from __future__ import annotations

import io
import json
import math
import os
import sys
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

import pymupdf
from PIL import Image
from playwright.sync_api import sync_playwright

from converter.ooxml import sha256

ORIGIN = "https://convx.invalid"
FLAGS = [
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-gpu",
    "--disable-lcd-text",
    "--no-first-run",
]


def render(request):
    root = Path(request["workspace"])
    policy = request["policy"]
    if version("playwright") != "1.64.1":
        return {"error": "VISUAL_BROWSER_PROFILE_MISMATCH", "phase": "version"}
    manifest = json.loads(
        files("playwright").joinpath("driver/package/browsers.json").read_text(encoding="utf-8")
    )
    expected = next(item for item in manifest["browsers"] if item["name"] == "chromium")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = request["browser_cache"]
    resources = {name: (root / "input" / name).read_bytes() for name in request["resources"]}
    width, height = request["page_size_pt"]
    css_width, css_height = width * 96 / 72, height * 96 / 72
    denied = []
    phase = "launch"
    with sync_playwright() as p:
        executable = Path(p.chromium.executable_path)
        if not executable.is_file():
            return {"error": "VISUAL_BROWSER_UNAVAILABLE", "phase": phase}
        browser = p.chromium.launch(
            headless=True,
            executable_path=str(executable),
            chromium_sandbox=True,
            args=FLAGS,
            timeout=policy["browser_timeout_seconds"] * 1000,
        )
        try:
            if browser.version != expected["browserVersion"]:
                return {"error": "VISUAL_BROWSER_PROFILE_MISMATCH", "phase": "version"}
            browser_context = browser.new_context(
                java_script_enabled=False,
                service_workers="block",
                accept_downloads=False,
                locale="en-US",
                timezone_id="UTC",
                color_scheme="light",
                reduced_motion="reduce",
                device_scale_factor=policy["dpi"] / 96,
                viewport={"width": math.ceil(css_width), "height": math.ceil(css_height)},
            )

            def route(route):
                url = urlsplit(route.request.url)
                name = url.path[1:] if url.path.startswith("/") else ""
                allowed = (
                    url.scheme == "https"
                    and url.netloc == "convx.invalid"
                    and not url.query
                    and not url.fragment
                    and name in resources
                    and route.request.method == "GET"
                )
                if allowed:
                    mime = (
                        "text/html; charset=us-ascii"
                        if name == request["htm_name"]
                        else "image/gif"
                        if name.lower().endswith(".gif")
                        else "image/jpeg"
                    )
                    route.fulfill(
                        status=200,
                        body=resources[name],
                        content_type=mime,
                        headers={
                            "Cache-Control": "no-store",
                            "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; script-src 'none'; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'",
                            "X-Content-Type-Options": "nosniff",
                        },
                    )
                elif url.netloc == "convx.invalid" and url.path == "/favicon.ico":
                    route.fulfill(status=204, body=b"")
                else:
                    denied.append(route.request.resource_type)
                    route.abort()

            browser_context.route("**/*", route)
            browser_context.set_default_timeout(min(30000, policy["browser_timeout_seconds"] * 1000))
            page = browser_context.new_page()
            phase = "navigation"
            page.goto(ORIGIN + "/" + request["htm_name"], wait_until="load")
            page.emulate_media(media="print")
            # This code is a trusted measurement, not JavaScript from the uploaded file.
            page.evaluate(
                "async () => { await document.fonts.ready; await Promise.all(Array.from(document.images).map(i => i.decode().catch(() => null))); }"
            )
            metrics = page.evaluate("""() => {
              const all=document.getElementsByTagName('*');
              let visible=0, hidden=0, nodes=0, whitespace=0;
              const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
              while(walker.nextNode()) {
                nodes++;
                const n=walker.currentNode, s=getComputedStyle(n.parentElement);
                const r=document.createRange(); r.selectNodeContents(n);
                if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0||r.getClientRects().length===0) { if(n.textContent.trim().length) hidden+=n.textContent.length; else whitespace+=n.textContent.length; }
                else visible+=n.textContent.length;
              }
              const boxes=Array.from(document.body.children).filter(e=>e.tagName==='DIV').map(e=>{const b=e.getBoundingClientRect(); return [b.x,b.y,b.width,b.height];});
              return {nodes:all.length,text_nodes:nodes,visible_text_characters:visible,hidden_text_characters:hidden,nonrendering_whitespace_characters:whitespace,document_width:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth),document_height:Math.max(document.documentElement.scrollHeight,document.body.scrollHeight),images:Array.from(document.images).map(i=>({loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight})),page_boxes:boxes,compat_mode:document.compatMode};
            }""")
            if metrics["nodes"] > policy["max_dom_nodes"]:
                return {"error": "VISUAL_DOM_LIMIT", "phase": "layout"}
            if (
                metrics["document_width"] * metrics["document_height"] * (policy["dpi"] / 96) ** 2
                > policy["max_total_pixels"]
            ):
                return {"error": "VISUAL_SCREEN_PIXEL_LIMIT", "phase": "layout"}
            phase = "print"
            page.pdf(
                path=str(root / "chromium.pdf"),
                width=f"{width / 72}in",
                height=f"{height / 72}in",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                scale=1,
                print_background=True,
                prefer_css_page_size=False,
                display_header_footer=False,
            )
            if (root / "chromium.pdf").stat().st_size > policy["max_pdf_bytes"]:
                return {"error": "VISUAL_PRINT_BYTE_LIMIT", "phase": phase}
            with pymupdf.open(root / "chromium.pdf") as printed:
                count = printed.page_count
            if count > policy["max_pages"]:
                return {"error": "VISUAL_PAGE_LIMIT", "phase": phase}
            boxes = metrics["page_boxes"]
            containers = len(boxes) == count and all(
                abs(b[2] - css_width) <= 0.05 and abs(b[3] - css_height) <= 0.05 for b in boxes
            )
            containers = containers and all(
                abs(b[0]) <= 0.05 and abs(b[1] - index * css_height) <= 0.05 for index, b in enumerate(boxes)
            )
            metrics["screen_page_mapping"] = (
                "source_size_containers"
                if containers
                else "single_page_viewport"
                if count == 1
                else "unresolved"
            )
            phase = "screenshots"
            if containers or count == 1:
                for index in range(count):
                    x, y, w, h = boxes[index] if containers else (0, 0, css_width, css_height)
                    if (
                        x < 0
                        or y < 0
                        or x + w > metrics["document_width"] + 0.05
                        or y + h > metrics["document_height"] + 0.05
                    ):
                        metrics["screen_page_mapping"] = "unresolved"
                        break
                    data = page.screenshot(
                        full_page=True,
                        clip={"x": x, "y": y, "width": w, "height": h},
                        animations="disabled",
                        caret="hide",
                        scale="device",
                    )
                    # Explicitly composite the PNG onto white; never scale/crop/blur it.
                    with Image.open(io.BytesIO(data)) as im:
                        im.convert("RGB").save(root / f"screen{index + 1:04d}.png")
            metrics.update(
                {
                    "pages": count,
                    "denied_requests": len(denied),
                    "browser_version": browser.version,
                    "browser_executable_sha256": sha256(executable),
                    "playwright_version": version("playwright"),
                    "browser_revision": expected["revision"],
                    "launch_flags": FLAGS,
                    "device_scale_factor": policy["dpi"] / 96,
                    "viewport_css_px": [math.ceil(css_width), math.ceil(css_height)],
                    "media": "print",
                    "javascript_enabled": False,
                    "service_workers": "block",
                    "sandbox_enabled": True,
                }
            )
            (root / "browser.json").write_text(json.dumps(metrics, sort_keys=True), encoding="utf-8")
            return {"rendered": True}
        except Exception as exc:
            with (root / "browser-error.json").open("w", encoding="utf-8") as error:
                os.chmod(root / "browser-error.json", 0o600)
                error.write(
                    json.dumps(
                        {"phase": phase, "exception_type": type(exc).__name__, "message": str(exc)[:4096]},
                        ensure_ascii=True,
                    )
                )
            return {"error": "VISUAL_BROWSER_FAILED", "phase": phase, "exception_type": type(exc).__name__}
        finally:
            browser.close()


def main():
    try:
        result = render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    except Exception as exc:
        result = {"error": "VISUAL_BROWSER_FAILED", "phase": "startup", "exception_type": type(exc).__name__}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
