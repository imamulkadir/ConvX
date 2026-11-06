import os

import pymupdf
import pytest
from converter.context import ProcessingContext
from converter.ooxml import sha256
from converter.pdf_analysis.extract import analyze_authoritative_pdf
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_analysis.resources import extract_resources
from converter.standard_html import render_standard
from converter.standard_visual import verify_standard
from converter.visual_validation.browser import browser_cache
from layout_fixtures import complex_pdf, merged_table_pdf, simple_pdf
from PIL import Image


def prepare(source, root):
    digest = sha256(source)
    context = ProcessingContext()
    layout = analyze_authoritative_pdf(
        source,
        {
            "method": "direct_uploaded_pdf",
            "source_sha256": digest,
            "pdf_sha256": digest,
            "visual_authority": True,
            "word_equivalence_verified": False,
        },
        context=context,
    )
    layout = extract_resources(source, layout, root / "resources", AnalysisPolicy(), context)
    generation = render_standard(source, layout, root / "resources", root / "html", source.name, context)
    return generation, context


@pytest.mark.parametrize("factory", [simple_pdf, complex_pdf, merged_table_pdf])
def test_real_chromium_screen_and_print_preserve_text_geometry_and_assets(tmp_path, factory):
    source = factory(tmp_path / "source.pdf")
    generation, context = prepare(source, tmp_path)
    result = verify_standard(source, tmp_path / "html", generation, tmp_path / "visual", context)
    assert result["checks_complete"] and result["text_verified"] and result["page_geometry_verified"]
    assert len(result["pages"]) == len(generation["pages"])
    assert result["network_requests_denied"] == 0
    assert result["source_pdf_sha256"] == sha256(source)
    for page in result["pages"]:
        assert page["screen"]["dimensions_match"] and page["print"]["dimensions_match"]
        assert page["screen"]["mean_absolute_channel_error"] < 2
        assert page["print"]["mean_absolute_channel_error"] < 2
    for name in result["artifacts"]:
        assert sha256(tmp_path / "visual" / name) == result["artifact_sha256"][name]
    if not result["pixel_equivalence_verified"]:
        assert any(d["code"] == "STANDARD_VISUAL_DIFFERENCES" for d in result["diagnostics"])


def test_mixed_page_sizes_and_rotated_crop_print_without_blank_pages(tmp_path):
    source = tmp_path / "mixed.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((100, 100), "Cropped and rotated")
        page.set_cropbox(pymupdf.Rect(50, 75, 350, 525))
        page.set_rotation(90)
        page = document.new_page(width=600, height=400)
        page.insert_text((50, 100), "Landscape page")
        document.save(source)
    generation, context = prepare(source, tmp_path)
    result = verify_standard(source, tmp_path / "html", generation, tmp_path / "visual", context)
    assert result["checks_complete"] and len(result["pages"]) == 2


def test_standard_html_opens_offline_with_real_transparent_local_images(tmp_path):
    from playwright.sync_api import sync_playwright

    source = complex_pdf(tmp_path / "source.pdf")
    generation, _ = prepare(source, tmp_path)
    environment_value = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_cache())
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, chromium_sandbox=True)
            try:
                page = browser.new_page(java_script_enabled=False, viewport={"width": 800, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto((tmp_path / "html" / generation["filename"]).resolve().as_uri(), wait_until="load")
                screen = tmp_path / "offline.png"
                page.locator("section.page").first.screenshot(path=str(screen))
                with Image.open(screen) as image:
                    pixel = image.convert("RGB").getpixel((80, 390))
                # Known fixture RGBA over white; native PDF alpha rounding differs
                # by up to two channel levels, which full comparisons report.
                reference = tuple(round(c * 128 / 255 + 255 * (1 - 128 / 255)) for c in (20, 150, 240))
                assert all(abs(a - b) <= 1 for a, b in zip(pixel, reference, strict=True)), (pixel, reference)
                assert not errors
            finally:
                browser.close()
    finally:
        if environment_value is None:
            os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
        else:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = environment_value


def test_control_channel_survives_terminal_colors_and_unrelated_editor_preload(tmp_path, monkeypatch):
    source = simple_pdf(tmp_path / "source.pdf")
    generation, context = prepare(source, tmp_path)
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("NODE_OPTIONS", "--require=convx-unrelated-editor-hook-must-not-run")
    result = verify_standard(source, tmp_path / "html", generation, tmp_path / "visual", context)
    assert result["checks_complete"]


def test_synthetic_word_gap_has_unchanged_visual_positions_in_browser(tmp_path):
    source = tmp_path / "gap.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((40, 100), "Hello")
        page.insert_text((69, 100), "world")
        document.save(source)
    generation, context = prepare(source, tmp_path)
    assert generation["pages"][0]["synthetic_spaces_restored"] == 1
    result = verify_standard(source, tmp_path / "html", generation, tmp_path / "visual", context)
    assert result["text_verified"] and result["pages"][0]["screen"]["mean_absolute_channel_error"] < 0.1
