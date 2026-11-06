import hashlib

import pymupdf
import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.ooxml import sha256
from converter.pdf_analysis.extract import analyze_authoritative_pdf
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_analysis.resources import extract_resources
from converter.standard_html import render_standard
from layout_fixtures import complex_pdf, merged_table_pdf, simple_pdf
from lxml import html


def prepare(path, root):
    digest = sha256(path)
    context = ProcessingContext()
    layout = analyze_authoritative_pdf(
        path,
        {
            "method": "direct_uploaded_pdf",
            "source_sha256": digest,
            "pdf_sha256": digest,
            "visual_authority": True,
            "word_equivalence_verified": False,
        },
        context=context,
    )
    layout = extract_resources(path, layout, root / "resources", AnalysisPolicy(), context)
    return layout, context


@pytest.mark.parametrize("factory", [simple_pdf, complex_pdf, merged_table_pdf])
def test_standard_modern_output_preserves_exact_text_and_local_graphics(tmp_path, factory):
    source = factory(tmp_path / "source.pdf")
    before = sha256(source)
    layout, context = prepare(source, tmp_path)
    result = render_standard(source, layout, tmp_path / "resources", tmp_path / "html", "source.pdf", context)
    data = (tmp_path / "html/document.html").read_bytes()
    assert data.startswith(b"<!DOCTYPE html>") and result["generated"]
    assert hashlib.sha256(data).hexdigest() == result["sha256"]
    parsed = html.fromstring(data)
    assert len(parsed.xpath("//section")) == len(layout.pages)
    assert not parsed.xpath("//script|//link|//iframe|//object")
    assert len(parsed.xpath("//style")) == 1
    assert result["characters"] == sum(page.character_count for page in layout.pages)
    assert sha256(source) == before and result["source_pdf_sha256"] == before
    ids = parsed.xpath("//*[@id]/@id")
    assert len(ids) == len(set(ids)), "SVG fragment identifiers must be scoped per page"
    for name, asset in result["assets"].items():
        assert sha256(tmp_path / "html" / name) == asset["sha256"]
    assert {p.name for p in (tmp_path / "html").iterdir()} == {"document.html", *result["assets"]}
    assert not result["font_embedding"] and not result["pixel_equivalence_verified"]


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_standard_cropped_rotated_mixed_pages_have_named_print_sizes(tmp_path, rotation):
    source = tmp_path / "mixed.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((100, 100), "Rotated report")
        page.set_cropbox(pymupdf.Rect(50, 75, 350, 525))
        page.set_rotation(rotation)
        page = document.new_page(width=600, height=400)
        page.insert_text((50, 100), "Landscape")
        document.save(source)
    layout, context = prepare(source, tmp_path)
    result = render_standard(source, layout, tmp_path / "resources", tmp_path / "html", "mixed.pdf", context)
    assert result["pages"][0]["width_pt"] == (450 if rotation in {90, 270} else 300)
    assert result["pages"][1]["height_pt"] == 400
    assert b"@page sheet2" in (tmp_path / "html/document.html").read_bytes()


def test_disclosure_markup_is_escaped_as_selectable_text(tmp_path):
    source = simple_pdf(tmp_path / "source.pdf", text='<script>alert("x")</script> & 1 < 2')
    layout, context = prepare(source, tmp_path)
    result = render_standard(
        source, layout, tmp_path / "resources", tmp_path / "html", "<img onerror=x>.pdf", context
    )
    parsed = html.fromstring((tmp_path / "html/document.html").read_bytes())
    assert not parsed.xpath("//script")
    assert result["characters"] == layout.pages[0].character_count
    assert parsed.xpath("//title")[0].text == "<img onerror=x>.pdf"


def test_stale_pdf_and_modified_private_resources_cannot_render(tmp_path):
    source = complex_pdf(tmp_path / "source.pdf")
    layout, context = prepare(source, tmp_path)
    resource = tmp_path / "resources" / layout.assets[0].original.filename
    original = resource.read_bytes()
    resource.write_bytes(original + b"changed")
    with pytest.raises(ConversionFailure, match="STANDARD_ASSET_CHANGED"):
        render_standard(source, layout, tmp_path / "resources", tmp_path / "changed", "source.pdf", context)
    resource.write_bytes(original)
    source.write_bytes(source.read_bytes() + b"\n%modified\n")
    with pytest.raises(ConversionFailure, match="STANDARD_SOURCE_REQUIRED"):
        render_standard(source, layout, tmp_path / "resources", tmp_path / "stale", "source.pdf", context)


def test_inspection_and_unverified_models_never_authorize_standard_output(tmp_path):
    from converter.pdf_analysis.extract import inspect_pdf

    source = simple_pdf(tmp_path / "source.pdf")
    with pytest.raises(ConversionFailure, match="STANDARD_SOURCE_REQUIRED"):
        render_standard(source, inspect_pdf(source), tmp_path / "resources", tmp_path / "html", "source.pdf")


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_synthetic_word_gap_spaces_are_preserved_without_moving_real_glyphs(tmp_path, rotation):
    source = tmp_path / "gaps.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((40, 100), "Hello")
        page.insert_text((69, 100), "world")
        page.set_rotation(rotation)
        document.save(source)
    layout, context = prepare(source, tmp_path)
    result = render_standard(source, layout, tmp_path / "resources", tmp_path / "html", "gaps.pdf", context)
    assert result["pages"][0]["synthetic_spaces_restored"] == 1
    parsed = html.fromstring((tmp_path / "html/document.html").read_bytes())
    assert "".join("".join(node.itertext()) for node in parsed.xpath("//text")) == "Hello world"


def test_clipped_source_paint_text_is_retained_with_its_native_clip_scope(tmp_path):
    source = tmp_path / "clipped.pdf"
    message = "Partially clipped source paint"
    with pymupdf.open() as document:
        page = document.new_page(width=200, height=200)
        page.insert_text((20, 100), message)
        xref = page.get_contents()[0]
        document.update_stream(xref, b"q 0 0 50 200 re W n\n" + document.xref_stream(xref) + b"\nQ")
        document.save(source)
    layout, context = prepare(source, tmp_path)
    assert layout.policy["preserve_clipped_text"] is True
    result = render_standard(
        source, layout, tmp_path / "resources", tmp_path / "html", "clipped.pdf", context
    )
    assert result["characters"] == len(message)
    parsed = html.fromstring((tmp_path / "html/document.html").read_bytes())
    assert parsed.xpath("//*[local-name()='clippath']")
