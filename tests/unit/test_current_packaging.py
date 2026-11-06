import copy
import io
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pymupdf
import pytest
from converter.artifacts import audit_download
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.input_pipeline import process_input
from converter.packaging.archive import _write_archive
from converter.packaging.current import audit_bytes, names, object_hash, verified_payloads
from converter.packaging.models import PackagingPolicy
from converter.sec_validation.validator import digest
from converter.visual_validation.browser import browser_cache
from PIL import Image


@pytest.fixture(scope="module", params=["standard", "edgar"])
def real_package(tmp_path_factory, request):
    root = tmp_path_factory.mktemp("current-" + request.param)
    image = io.BytesIO()
    Image.new("RGB", (8, 6), (30, 120, 220)).save(image, format="PNG")
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=600)
        page.insert_text((40, 60), "Revenue 123.45")
        page.insert_image(pymupdf.Rect(40, 100, 120, 160), stream=image.getvalue())
        doc.save(root / "source.pdf")
    original = "Résumé report's.PDF"
    (root / "request.json").write_text(
        json.dumps({"original_filename": original, "mode": request.param, "attempt": 1}), encoding="utf-8"
    )
    report = process_input(root / "source.pdf", root / "attempt001", original, mode=request.param)
    assert report["status"] == "packaged", report["diagnostics"]
    report["workspace"] = "attempt001"
    return root, report


def test_real_mode_archive_exact_members_bytes_and_fresh_download(real_package):
    root, report = real_package
    package = report["packaging"]
    assert audit_download(root, report)["filename"] == "Résumé report's.zip"
    data = (root / "attempt001/package/result.zip").read_bytes()
    with ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == [
            package["document_filename"],
            *sorted(report["html_generation"]["assets"]),
        ]
        assert (
            archive.read(package["document_filename"])
            == (root / "attempt001" / report["mode"] / report["html_generation"]["filename"]).read_bytes()
        )
        assert all("/" not in n and "\\" not in n for n in archive.namelist())
    if report["mode"] == "edgar":
        assert len(package["document_filename"]) <= 32 and package["document_filename"].endswith(".htm")
        assert not report["sec_validation"]["strict_passed"]
    else:
        assert package["document_filename"] == "Résumé report's.html"
    assert not package["sec_acceptance_confirmed"]


def test_actual_renamed_archive_document_opens_offline(tmp_path, real_package, monkeypatch):
    from playwright.sync_api import sync_playwright

    root, report = real_package
    audit_download(root, report)
    offline = tmp_path / "offline"
    offline.mkdir()
    with ZipFile(root / "attempt001/package/result.zip") as archive:
        for name in archive.namelist():
            (offline / name).write_bytes(archive.read(name))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browser_cache()))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
        try:
            page = browser.new_page(java_script_enabled=False, viewport={"width": 800, "height": 1000})
            failures = []
            page.on("requestfailed", lambda request: failures.append(request.url))
            page.goto(
                (offline / report["packaging"]["document_filename"]).resolve().as_uri(), wait_until="load"
            )
            assert "Revenue 123.45" in page.locator("body").text_content()
            capture = tmp_path / "offline.png"
            selector = "section.page" if report["mode"] == "standard" else "body > div"
            page.locator(selector).first.screenshot(path=str(capture))
            with Image.open(capture) as image:
                actual = image.convert("RGB").getpixel((80, 170))
                assert actual == (30, 120, 220), actual
            assert not failures
        finally:
            browser.close()


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "pdf",
        "html",
        "asset",
        "capture",
        "comparison",
        "zip",
        "mode",
        "manifest",
        "completion",
        "extra",
    ],
)
def test_fresh_download_rejects_real_tampered_artifacts(tmp_path, real_package, change):
    source, original = real_package
    root = tmp_path / "job"
    shutil.copytree(source, root)
    report = copy.deepcopy(original)
    work = root / "attempt001"
    mode = report["mode"]
    paths = {
        "source": root / "source.pdf",
        "pdf": work / report["generated_pdf_artifact"],
        "html": work / mode / report["html_generation"]["filename"],
        "asset": work / mode / next(iter(report["html_generation"]["assets"])),
        "capture": work / (mode + "-visual/page0001.screen.png"),
        "comparison": work / (mode + "-visual/comparison.json"),
        "zip": work / "package/result.zip",
    }
    if change in paths:
        with paths[change].open("ab") as stream:
            stream.write(b"changed")
    elif change == "mode":
        request = json.loads((root / "request.json").read_text(encoding="utf-8"))
        request["mode"] = "edgar" if mode == "standard" else "standard"
        (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
    elif change == "manifest":
        report["packaging"]["files"].pop()
    elif change == "completion":
        report["final_conversion_complete"] = False
    else:
        (work / mode / "debug.json").write_text("{}")
    with pytest.raises((ConversionFailure, ValueError, KeyError, json.JSONDecodeError)):
        audit_download(root, report)


def test_inspection_or_incomplete_visual_cannot_authorize_packaging(real_package):
    root, report = real_package
    generation = copy.deepcopy(report["html_generation"])
    generation["method"] = "inspection_only"
    with pytest.raises(ConversionFailure):
        verified_payloads(
            root / "attempt001" / report["generated_pdf_artifact"],
            root / "attempt001" / report["mode"],
            report["mode"],
            generation,
            report[report["mode"] + "_visual_validation"],
            ProcessingContext(),
        )
    generation = report["html_generation"]
    visual = copy.deepcopy(report[report["mode"] + "_visual_validation"])
    visual["pages"].pop()
    with pytest.raises(ConversionFailure):
        verified_payloads(
            root / "attempt001" / report["generated_pdf_artifact"],
            root / "attempt001" / report["mode"],
            report["mode"],
            generation,
            visual,
            ProcessingContext(),
        )


@pytest.mark.parametrize(
    "name", ["report.pdf", "report.DOCX", "a" * 200 + ".pdf", "My report.pdf", "বাংলা.pdf"]
)
def test_mode_names_preserve_zip_basename_and_bound_edgar_name(name):
    for mode in ["standard", "edgar"]:
        document, download = names(name, mode)
        assert download == Path(name).stem + ".zip"
        assert document.endswith(".htm" if mode == "edgar" else ".html")
        if mode == "edgar":
            assert document.isascii() and len(document) <= 32


@pytest.mark.parametrize(
    "name", ["../report.pdf", "CON.pdf", "a/b.docx", ".hidden.pdf", "bad.txt", "a\x00.pdf"]
)
def test_unsafe_source_names_fail(name):
    with pytest.raises(ConversionFailure):
        names(name, "standard")


@pytest.mark.parametrize(
    "change",
    ["extra", "nested", "duplicate", "crc", "trailing", "wrong_extension", "broken_reference", "unused"],
)
def test_actual_archive_bytes_reject_unsafe_members(tmp_path, change):
    payloads = {"report.html": b"<!DOCTYPE html><html><body><p>Disclosure 123.45</p></body></html>"}
    filename = "report.html"
    if change == "extra":
        payloads["report.json"] = b"{}"
    elif change == "nested":
        payloads["dir/image0001.png"] = b"x"
    elif change == "wrong_extension":
        payloads = {"report.htm": payloads.pop(filename)}
        filename = "report.htm"
    elif change == "broken_reference":
        payloads[filename] = b'<html><body><img src="missing.png"></body></html>'
    elif change == "unused":
        payloads["image0001.png"] = b"unused"
    archive = tmp_path / "result.zip"
    _write_archive(archive, payloads, PackagingPolicy(), ProcessingContext())
    data = archive.read_bytes()
    if change == "duplicate":
        with ZipFile(archive, "a") as z:
            z.writestr("REPORT.HTML", b"duplicate")
        data = archive.read_bytes()
    elif change == "crc":
        data = bytearray(data)
        data[45] ^= 1
        data = bytes(data)
    elif change == "trailing":
        data += b"hidden"
    expected = {n: {"sha256": digest(v), "bytes": len(v)} for n, v in payloads.items()}
    with pytest.raises(ConversionFailure):
        audit_bytes(data, "standard", filename, expected)


def test_archive_is_deterministic_and_detects_changed_payload(tmp_path):
    payloads = {"report.html": b"<html><body>123.45</body></html>"}
    for n in ["one", "two"]:
        _write_archive(tmp_path / n, payloads, PackagingPolicy(), ProcessingContext())
    data = (tmp_path / "one").read_bytes()
    assert data == (tmp_path / "two").read_bytes()
    expected = {
        "report.html": {"sha256": digest(payloads["report.html"]), "bytes": len(payloads["report.html"])}
    }
    audit_bytes(data, "standard", "report.html", expected)
    expected["report.html"]["sha256"] = "0" * 64
    with pytest.raises(ConversionFailure):
        audit_bytes(data, "standard", "report.html", expected)
    assert object_hash({"a": 1, "b": 2}) == object_hash({"b": 2, "a": 1})
