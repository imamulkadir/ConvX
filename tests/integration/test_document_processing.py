import os
from pathlib import Path

import pytest
from conftest import ROOT, docx_bytes
from converter.context import ProcessingContext
from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.pipeline import process_docx
from converter.revisions.accept import accept_revisions


@pytest.fixture
def libreoffice():
    configured = os.environ.get("CONVX_TEST_LIBREOFFICE")
    executable = Path(configured) if configured else ROOT / ".tools/libreoffice/program/soffice.com"
    if not executable.is_file():
        pytest.skip("Set CONVX_TEST_LIBREOFFICE to a real free LibreOffice executable")
    return executable


def test_real_libreoffice_render_and_positive_pdf_gate(tmp_path, libreoffice):
    source = tmp_path / "source.docx"
    source.write_bytes(docx_bytes())
    accepted = tmp_path / "accepted.docx"
    accept_revisions(source, accepted)
    provider = LibreOfficeProvider(libreoffice)
    baseline = provider.render(accepted, tmp_path / "baseline", ProcessingContext())
    result = process_docx(source, tmp_path / "result", provider, baseline.path)
    assert result["status"] == "failed", result["diagnostics"]
    assert result["diagnostics"][0]["code"] == "SEC_VALIDATION_FAILED"
    assert result["sec_validation"]["checks_complete"]
    assert not result["sec_validation"]["passed"]
    assert any(d["code"] == "CSS_PERMISSION_UNVERIFIED" for d in result["sec_validation"]["diagnostics"])
    assert result["asset_normalization"]["content_integrity_passed"]
    assert result["visual_validation"] is None
    assert not (tmp_path / "result/visual").exists()
    assert result["pdf_validation"]["passed"]
    assert not result["final_conversion_complete"]
    assert result["provider"]["provider"] == "libreoffice"
    assert result["layout_analysis"]["reconstruction_eligible"]
    assert (tmp_path / "result/layout.json").is_file()
    assert result["html_generation"]["content_integrity_passed"]
    assert not result["html_generation"]["strict_validation_passed"]
    assert (tmp_path / "result/candidate.htm").is_file()


def test_real_23_page_reference_regression_records_failure(tmp_path, libreoffice):
    fixtures = ROOT / "tests/fixtures"
    result = process_docx(
        fixtures / "06749LWD4_prelim_prospectus_automated.docx",
        tmp_path / "regression",
        LibreOfficeProvider(libreoffice),
        fixtures / "06749LWD4_prelim_prospectus_automated.pdf",
        fixtures / "06749LWD4_prelim_prospectus_automated (1).docx",
    )
    assert result["accepted_reference_comparison"]["passed"]
    assert result["revision_acceptance"]["media_preserved"] and result["source_unchanged"]
    assert result["pdf_validation"] is not None, result["diagnostics"]
    assert result["pdf_validation"]["reference_page_count"] == 23
    assert len(result["pdf_validation"]["pages"]) >= 23
    # This is a negative qualification test: it does not claim the fixture passed fidelity.
    assert result["status"] == "failed"
    assert result["diagnostics"][0]["code"] == "PDF_STRICT_VALIDATION_FAILED"
    assert not result["final_conversion_complete"]
    assert result["layout_analysis"] is None
    assert result["html_generation"] is None
    assert result["sec_validation"] is None
    assert result["visual_validation"] is None
    assert not (tmp_path / "regression/candidate.htm").exists()
    assert not (tmp_path / "regression/layout.json").exists()
