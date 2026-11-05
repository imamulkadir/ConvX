import hashlib

import pymupdf
import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.layout.models import DocumentLayout
from converter.ooxml import sha256
from converter.pdf_analysis.extract import analyze_pdf, inspect_pdf, write_layout
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_export.validation import validate_pdf
from layout_fixtures import complex_pdf, merged_table_pdf, simple_pdf
from pydantic import ValidationError


def all_spans(layout):
    return [
        span
        for page in layout.pages
        for block in page.text_blocks
        for line in block.lines
        for span in line.spans
    ]


def test_character_ledger_exact_whitespace_and_determinism(tmp_path):
    path = simple_pdf(tmp_path / "source.pdf")
    first, second = inspect_pdf(path), inspect_pdf(path)
    assert first.model_dump_json() == second.model_dump_json()
    page = first.pages[0]
    text = "".join(s.text for s in all_spans(first))
    assert text == "Hello  world" and page.character_count == 12
    assert page.character_sha256 == hashlib.sha256(text.encode()).hexdigest()
    assert not first.reconstruction_eligible and first.mode == "inspection_only"
    assert all(c.glyph_ids for s in all_spans(first) for c in s.characters)
    assert all_spans(first)[0].color_rgb == 0xFF0000


def test_validated_source_required_and_bound_to_hash(tmp_path):
    path = simple_pdf(tmp_path / "source.pdf")
    proof = validate_pdf(path, path)
    result = analyze_pdf(path, proof)
    assert result.reconstruction_eligible and result.validation_report_sha256
    assert result.source_pdf_sha256 == sha256(path)
    changed = simple_pdf(tmp_path / "changed.pdf", text="Changed")
    with pytest.raises(ConversionFailure, match="PDF_LAYOUT_SOURCE_CHANGED"):
        analyze_pdf(changed, proof)


@pytest.mark.parametrize(
    "mutation", ["failed", "missing_reference", "nonstrict", "partial_pages", "page_failed", "method"]
)
def test_no_prior_gate_bypass(tmp_path, mutation):
    path = simple_pdf(tmp_path / "source.pdf")
    proof = validate_pdf(path, path)
    if mutation == "failed":
        proof["passed"] = False
    elif mutation == "missing_reference":
        proof["reference_compared"] = False
    elif mutation == "nonstrict":
        proof["policy"]["require_reference"] = False
    elif mutation == "partial_pages":
        proof["pages"] = []
    elif mutation == "page_failed":
        proof["pages"][0]["passed"] = False
    else:
        proof["method"] = "unknown"
    with pytest.raises(ConversionFailure, match="PDF_LAYOUT_GATE_REQUIRED"):
        analyze_pdf(path, proof)


def test_crop_and_rotation_coordinates_are_reversible(tmp_path):
    path = tmp_path / "crop.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((100, 100), "Crop", fontsize=12)
        page.set_cropbox(pymupdf.Rect(50, 75, 350, 525))
        page.set_rotation(90)
        document.save(path)
    before = sha256(path)
    layout = inspect_pdf(path)
    geometry = layout.pages[0].geometry
    assert geometry.rotation_degrees == 90
    assert geometry.unrotated_bounds == (0, 0, 300, 450)
    assert geometry.display_bounds == (0, 0, 450, 300)
    assert all_spans(layout)[0].origin == pytest.approx((50, 25))
    projected = pymupdf.Point(100, 500) * pymupdf.Matrix(geometry.pdf_to_page_matrix)
    assert tuple(projected) == pytest.approx((50, 25))
    original = pymupdf.Point(50, 25)
    roundtrip = (
        original
        * pymupdf.Matrix(geometry.page_to_display_matrix)
        * pymupdf.Matrix(geometry.display_to_page_matrix)
    )
    assert tuple(roundtrip) == pytest.approx(tuple(original)) and sha256(path) == before


def test_rich_typography_images_vectors_tables_links_and_regions(tmp_path):
    path = complex_pdf(tmp_path / "complex.pdf")
    layout = inspect_pdf(path)
    assert len(layout.pages) == 3 and len(layout.assets) == 1
    assert layout.assets[0].soft_mask_xref and layout.assets[0].width_px == 8
    spans = all_spans(layout)
    assert any(s.text == "Bold" and s.bold_hint for s in spans)
    assert any(s.text == "Italic" and s.italic_hint and s.font_size_pt == 9.5 for s in spans)
    assert any(s.text == "Underlined" and s.underline_hint for s in spans)
    assert any(abs(line.direction[1]) > 0.9 for p in layout.pages for b in p.text_blocks for line in b.lines)
    for page in layout.pages:
        assert len(page.images) == 2 and page.images[0].asset_id == page.images[1].asset_id
        assert page.images[0].transform != page.images[1].transform
        assert any(i.command == "c" for v in page.vectors for i in v.items)
        assert any(v.properties.get("fill_opacity") == pytest.approx(0.6) for v in page.vectors)
        assert page.links[0].uri.startswith("https://www.sec.gov/")
        table = next(t for t in page.tables if t.method == "native_lines_strict")
        assert table.rows == 2 and table.columns == 2 and table.grid_resolved
        assert all(cell.character_ids and cell.border_path_ids for cell in table.cells)
        assert {r.kind for r in page.regions} >= {"header", "page_number"}


def test_merged_cells_link_to_physical_text_without_duplication(tmp_path):
    layout = inspect_pdf(merged_table_pdf(tmp_path / "merged.pdf"))
    table = layout.pages[0].tables[0]
    assert table.grid_resolved and table.rows == 2 and table.columns == 2
    assert table.grid[0][0] == table.grid[0][1]
    assert any(cell.column_span == 2 for cell in table.cells)
    ids = [c for cell in table.cells for c in cell.character_ids]
    assert len(ids) == len(set(ids))


def test_multi_column_order_preserves_native_and_candidate_orders(tmp_path):
    path = tmp_path / "columns.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=500, height=600)
        for x, y, text in [
            (300, 70, "Right first"),
            (50, 70, "Left first"),
            (300, 180, "Right second"),
            (50, 180, "Left second"),
        ]:
            page.insert_text((x, y), text)
        document.save(path)
    layout = inspect_pdf(path, policy=AnalysisPolicy(detect_borderless_candidates=False))
    page = layout.pages[0]
    by_id = {b.id: "".join(s.text for line in b.lines for s in line.spans) for b in page.text_blocks}
    order = page.reading_order
    assert set(order.native_block_ids) == set(order.candidate_block_ids)
    assert "Left first" in " ".join(by_id[i] for i in order.candidate_block_ids)
    lines = {line.id: "".join(s.text for s in line.spans) for b in page.text_blocks for line in b.lines}
    assert [lines[i] for i in order.candidate_line_ids] == [
        "Left first",
        "Left second",
        "Right first",
        "Right second",
    ]
    assert page.character_count == sum(len(s.characters) for s in all_spans(layout))


def test_borderless_numeric_table_is_only_a_candidate(tmp_path):
    path = tmp_path / "borderless.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=500)
        for row, (label, value) in enumerate(
            [("Asset", "Price"), ("Bond", "100"), ("Note", "200"), ("Share", "300")]
        ):
            page.insert_text((50, 70 + row * 30), label)
            page.insert_text((200, 70 + row * 30), value)
        document.save(path)
    layout = inspect_pdf(path)
    assert any(t.method == "native_text_alignment" and t.confidence < 0.5 for t in layout.pages[0].tables)
    assert any(d.code == "BORDERLESS_TABLE_CANDIDATE" for d in layout.pages[0].diagnostics)


def test_annotation_is_retained_and_blocks_reconstruction(tmp_path):
    path = simple_pdf(tmp_path / "plain.pdf")
    annotated = tmp_path / "annotated.pdf"
    with pymupdf.open(path) as document:
        document[0].add_text_annot((200, 200), "Reviewer note")
        document.save(annotated)
    proof = validate_pdf(annotated, annotated)
    layout = analyze_pdf(annotated, proof)
    assert layout.pages[0].annotations and not layout.reconstruction_eligible
    assert any(d.code == "ANNOTATION_APPEARANCE_UNRESOLVED" for d in layout.pages[0].diagnostics)


@pytest.mark.parametrize(
    "policy",
    [
        AnalysisPolicy(max_characters_per_page=2),
        AnalysisPolicy(max_total_characters=2),
        AnalysisPolicy(max_blocks_per_page=1),
        AnalysisPolicy(max_vectors_per_page=1),
        AnalysisPolicy(max_images_per_page=1),
        AnalysisPolicy(max_cells_per_page=1),
        AnalysisPolicy(max_image_pixels=1),
        AnalysisPolicy(max_membership_checks=1),
    ],
)
def test_budgets_fail_without_truncating_output(tmp_path, policy):
    path = complex_pdf(tmp_path / "source.pdf")
    with pytest.raises(ConversionFailure, match="PDF_(?:ANALYSIS|IMAGE)_LIMIT"):
        inspect_pdf(path, policy=policy)


def test_serialization_atomic_private_and_validated(tmp_path):
    layout = inspect_pdf(simple_pdf(tmp_path / "source.pdf"))
    target = tmp_path / "private/layout.json"
    summary = write_layout(target, layout)
    assert summary["sha256"] == sha256(target)
    loaded = DocumentLayout.model_validate_json(target.read_bytes())
    assert loaded == layout and summary["mode"] == "inspection_only"
    assert not target.with_name("layout.json.part").exists()
    with pytest.raises(ConversionFailure, match="LAYOUT_OUTPUT_EXISTS"):
        write_layout(target, layout)
    with pytest.raises(ConversionFailure, match="PDF_LAYOUT_OUTPUT_LIMIT"):
        write_layout(tmp_path / "too-small.json", layout, max_bytes=1)
    assert not (tmp_path / "too-small.json").exists()


@pytest.mark.parametrize("mutation", ["ledger", "font", "id", "bbox", "inspection_eligible", "page"])
def test_model_rejects_dangling_or_corrupt_records(tmp_path, mutation):
    data = inspect_pdf(simple_pdf(tmp_path / "source.pdf")).model_dump(mode="json")
    span = data["pages"][0]["text_blocks"][0]["lines"][0]["spans"][0]
    if mutation == "ledger":
        data["pages"][0]["character_count"] += 1
    elif mutation == "font":
        span["font_ids"] = ["unknown"]
    elif mutation == "id":
        span["characters"][1]["id"] = span["characters"][0]["id"]
    elif mutation == "bbox":
        span["bbox"] = [20, 20, 10, 10]
    elif mutation == "inspection_eligible":
        data["reconstruction_eligible"] = True
    else:
        data["pages"][0]["page_number"] = 2
    with pytest.raises(ValidationError):
        DocumentLayout.model_validate(data)


def test_cancellation_and_deadline_before_native_work(tmp_path):
    path = simple_pdf(tmp_path / "source.pdf")
    with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
        inspect_pdf(path, context=ProcessingContext(cancelled=lambda: True))
    with pytest.raises(ConversionFailure, match="PROCESSING_TIMEOUT"):
        inspect_pdf(path, context=ProcessingContext(timeout_seconds=-1))


def test_superscript_subscript_preserve_baseline_evidence(tmp_path):
    path = tmp_path / "scripts.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_htmlbox(pymupdf.Rect(40, 60, 350, 160), "Base x<sup>2</sup> and H<sub>2</sub>O")
        document.save(path)
    spans = all_spans(inspect_pdf(path))
    assert any(s.text == "2" and s.script_hint == "superscript" for s in spans)
    assert any(s.text == "2" and s.script_hint == "subscript" for s in spans)
    assert all(s.script_evidence != "none" for s in spans if s.script_hint != "normal")
