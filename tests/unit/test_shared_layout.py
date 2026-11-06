import hashlib
from io import BytesIO

import pymupdf
import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.layout.models import DocumentLayout, ImageResource
from converter.ooxml import sha256
from converter.pdf_analysis.extract import analyze_authoritative_pdf, write_layout
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_analysis.resources import extract_resources
from converter.pdf_analysis.verification import verify_layout
from layout_fixtures import complex_pdf, merged_table_pdf, simple_pdf
from PIL import Image


def provenance(path):
    return {
        "method": "direct_uploaded_pdf",
        "source_sha256": sha256(path),
        "pdf_sha256": sha256(path),
        "visual_authority": True,
        "word_equivalence_verified": False,
    }


def analyze(path):
    return analyze_authoritative_pdf(path, provenance(path))


def test_shared_rich_layout_has_source_verified_text_fonts_geometry_and_real_images(tmp_path):
    path = complex_pdf(tmp_path / "independent.pdf")
    before = sha256(path)
    layout = analyze(path)
    assert len(layout.verification.pages) == 3
    assert all(p.images == 2 and p.vectors > 5 and p.characters > 50 for p in layout.verification.pages)
    assert len(layout.fonts) == 3
    assert all({r.kind for r in p.regions} >= {"header", "page_number"} for p in layout.pages)
    first = extract_resources(path, layout, tmp_path / "first", AnalysisPolicy(), ProcessingContext())
    second = extract_resources(path, layout, tmp_path / "second", AnalysisPolicy(), ProcessingContext())
    assert first.model_dump_json() == second.model_dump_json()
    assert len(first.assets) == 1 and first.assets[0].mask and first.assets[0].original
    for asset in first.assets:
        for resource in (asset.original, asset.mask):
            data = (tmp_path / "first" / resource.filename).read_bytes()
            assert len(data) == resource.bytes and hashlib.sha256(data).hexdigest() == resource.sha256
            assert Image.open(BytesIO(data)).size == (8, 6)
    assert len(list((tmp_path / "first").iterdir())) == 2
    summary = write_layout(tmp_path / "layout.json", first)
    assert summary["images"] == 6 and summary["image_resources"] == 1
    assert summary["fonts"] == 3 and summary["resolved_tables"] >= 3
    assert summary["verification"]["source_pdf_sha256"] == before == sha256(path)
    assert not first.reconstruction_eligible and first.validation_report_sha256 is None


def test_shared_merged_table_retains_exact_character_membership(tmp_path):
    layout = analyze(merged_table_pdf(tmp_path / "merged.pdf"))
    table = layout.pages[0].tables[0]
    assert table.grid_resolved and any(cell.column_span == 2 for cell in table.cells)
    identifiers = [identifier for cell in table.cells for identifier in cell.character_ids]
    assert len(identifiers) == len(set(identifiers))
    assert layout.verification.pages[0].characters == layout.pages[0].character_count


def test_original_jpeg_bytes_are_retained_without_recompression(tmp_path):
    stream = BytesIO()
    Image.new("RGB", (17, 11), "orange").save(stream, format="JPEG", quality=91)
    original = stream.getvalue()
    path = tmp_path / "jpeg.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        xref = page.insert_image(pymupdf.Rect(10, 20, 180, 130), stream=original)
        page.insert_image(pymupdf.Rect(200, 40, 285, 95), xref=xref)
        document.save(path)
    layout = extract_resources(
        path, analyze(path), tmp_path / "resources", AnalysisPolicy(), ProcessingContext()
    )
    assert len(layout.assets) == 1
    assert (tmp_path / "resources" / layout.assets[0].original.filename).read_bytes() == original
    assert layout.assets[0].mask is None


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_mixed_page_sizes_crop_rotation_and_columns_are_verified(tmp_path, rotation):
    path = tmp_path / "mixed.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((100, 110), "Cropped content")
        page.set_cropbox(pymupdf.Rect(50, 75, 350, 525))
        page.set_rotation(rotation)
        page = document.new_page(width=600, height=400)
        for x, y, text in [
            (350, 70, "Right top"),
            (50, 70, "Left top"),
            (350, 180, "Right bottom"),
            (50, 180, "Left bottom"),
        ]:
            page.insert_text((x, y), text)
        document.save(path)
    layout = analyze(path)
    assert layout.verification.pages[0].rotation == rotation
    assert layout.pages[0].geometry.crop_offset == (50, 75)
    assert (layout.verification.pages[1].width_pt, layout.verification.pages[1].height_pt) == (600, 400)
    page = layout.pages[1]
    lines = {line.id: "".join(s.text for s in line.spans) for b in page.text_blocks for line in b.lines}
    assert [lines[key] for key in page.reading_order.candidate_line_ids] == [
        "Left top",
        "Left bottom",
        "Right top",
        "Right bottom",
    ]


@pytest.mark.parametrize(
    "key,value",
    [
        ("pdf_sha256", "0" * 64),
        ("method", "inspection_only"),
        ("word_equivalence_verified", True),
        ("source_sha256", "invalid"),
    ],
)
def test_authoritative_provenance_cannot_be_stale_or_promoted(tmp_path, key, value):
    path = simple_pdf(tmp_path / "input.pdf")
    proof = provenance(path)
    proof[key] = value
    with pytest.raises(ConversionFailure, match="PDF_PROVENANCE_INVALID"):
        analyze_authoritative_pdf(path, proof)


@pytest.mark.parametrize(
    "mutation,code",
    [("position", "POSITION"), ("typography", "FONT"), ("font_resource", "FONT"), ("geometry", "CONTENT")],
)
def test_independent_audit_rejects_changed_layout_even_with_same_text(tmp_path, mutation, code):
    path = simple_pdf(tmp_path / "source.pdf")
    payload = analyze(path).model_dump()
    payload["verification"] = None
    page = payload["pages"][0]
    span = page["text_blocks"][0]["lines"][0]["spans"][0]
    if mutation == "position":
        char = span["characters"][0]
        char["origin"] = (char["origin"][0] + 10, char["origin"][1])
    elif mutation == "typography":
        span["font_size_pt"] += 3
    elif mutation == "font_resource":
        payload["fonts"][0]["base_font"] = "WrongFont"
    else:
        page["geometry"]["display_bounds"] = (0, 0, 410, 600)
    changed = DocumentLayout.model_validate(payload)
    with pytest.raises(ConversionFailure, match=f"PDF_LAYOUT_{code}_MISMATCH"):
        verify_layout(path, changed, AnalysisPolicy(), ProcessingContext())


def test_image_placement_tampering_is_detected(tmp_path):
    path = complex_pdf(tmp_path / "images.pdf")
    payload = analyze(path).model_dump()
    payload["verification"] = None
    placement = payload["pages"][0]["images"][0]
    matrix = list(placement["transform"])
    matrix[4] += 20
    placement["transform"] = tuple(matrix)
    with pytest.raises(ConversionFailure, match="PDF_LAYOUT_IMAGE_MISMATCH"):
        verify_layout(path, DocumentLayout.model_validate(payload), AnalysisPolicy(), ProcessingContext())


def test_resources_enforce_limits_and_reject_stale_sources(tmp_path):
    path = complex_pdf(tmp_path / "images.pdf")
    layout = analyze(path)
    with pytest.raises(ConversionFailure, match="PDF_IMAGE_RESOURCE_LIMIT"):
        extract_resources(
            path, layout, tmp_path / "small", AnalysisPolicy(max_resource_bytes=1), ProcessingContext()
        )
    assert not list((tmp_path / "small").iterdir())
    path.write_bytes(path.read_bytes() + b"\n%modified\n")
    with pytest.raises(ConversionFailure, match="PDF_LAYOUT_SOURCE_CHANGED"):
        extract_resources(path, layout, tmp_path / "stale", AnalysisPolicy(), ProcessingContext())
    assert not (tmp_path / "stale").exists()


def test_image_resource_names_cannot_escape_analysis_storage():
    with pytest.raises(ValueError):
        ImageResource(
            filename="../secret.png", sha256="0" * 64, bytes=1, format="png", width_px=1, height_px=1
        )


def test_inline_images_remain_explicitly_unresolved_without_invented_assets(tmp_path):
    path = tmp_path / "inline.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=200, height=200)
        content = document.get_new_xref()
        document.update_object(content, "<< >>")
        document.update_stream(
            content, b"q 20 0 0 10 10 10 cm BI /W 2 /H 1 /CS /RGB /BPC 8 /F /AHx ID FF000000FF00> EI Q"
        )
        page.set_contents(content)
        document.save(path)
    layout = extract_resources(
        path, analyze(path), tmp_path / "resources", AnalysisPolicy(), ProcessingContext()
    )
    assert len(layout.assets) == 1 and layout.assets[0].inline
    assert layout.assets[0].original is None
    assert any(d.code == "INLINE_IMAGE_RESOURCE_UNRESOLVED" for d in layout.diagnostics)
    assert not list((tmp_path / "resources").iterdir())


def test_pdf_shading_is_reported_instead_of_silently_missing_from_vectors(tmp_path):
    path = tmp_path / "shading.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=200, height=200)
        shade = document.get_new_xref()
        document.update_object(
            shade,
            "<< /ShadingType 2 /ColorSpace /DeviceRGB /Coords [0 0 200 0] /Function << /FunctionType 2 /Domain [0 1] /C0 [1 0 0] /C1 [0 0 1] /N 1 >> /Extend [true true] >>",
        )
        resources = int(document.xref_get_key(page.xref, "Resources")[1].split()[0])
        document.xref_set_key(resources, "Shading", f"<< /Sh1 {shade} 0 R >>")
        content = document.get_new_xref()
        document.update_object(content, "<< >>")
        document.update_stream(content, b"/Sh1 sh")
        page.set_contents(content)
        document.save(path)
    layout = analyze(path)
    assert any(p.kind == "fill-shade" for p in layout.pages[0].paint_order)
    assert any(d.code == "PDF_SHADING_UNRESOLVED" for d in layout.pages[0].diagnostics)
