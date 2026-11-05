"""Negative all-page visual accounting, never a generated prospectus or gate bypass."""

from conftest import ROOT
from converter.ooxml import sha256
from converter.visual_validation.engine import inspect_visuals


def test_real_23_page_word_pdf_reports_all_missing_disclosure(tmp_path):
    source = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf"
    before = sha256(source)
    # Deliberately empty comparison document establishes negative all-page coverage only.
    # It is not described as a conversion result and contains no copied filing text.
    htm = tmp_path / "negative.htm"
    htm.write_text(
        '<html><body style="margin:0;padding:0">'
        + ('<div style="width:612pt;height:792pt;page-break-after:always"></div>' * 23)
        + "</body></html>",
        encoding="ascii",
    )
    result = inspect_visuals(source, htm, (), tmp_path / "inspection")
    assert result.source_pages == 23 and len(result.pages) >= 23 and result.checks_complete
    assert not result.comparison_passed and not result.strict_passed
    assert result.mode == "inspection_only" and result.pdf_gate_sha256 is None
    assert sum(p.get("geometry", {}).get("source_characters", 0) for p in result.pages) == 85798
    assert {d.page for d in result.diagnostics if d.code == "VISUAL_CONTENT_MISMATCH"} == set(range(1, 24))
    assert sha256(source) == before == result.source_pdf_sha256
