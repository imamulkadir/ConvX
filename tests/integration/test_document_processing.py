import os
from pathlib import Path

import pytest
from conftest import ROOT, docx_bytes, upload_one
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
    assert result["status"] == "htm_generated", result["diagnostics"]
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
    assert not (tmp_path / "regression/candidate.htm").exists()
    assert not (tmp_path / "regression/layout.json").exists()


def test_worker_persists_private_accepted_output_and_report(client, settings, monkeypatch):
    from workers.tasks.admission import admit_document

    job = upload_one(client)
    admit_document(job["id"], settings)
    record = client.app.state.repository.get(job["id"], "alice")
    assert record["diagnostic_code"] == "PDF_RENDERER_UNAVAILABLE"
    workspace = client.app.state.storage.attempt(job["id"], record["attempt_id"])
    assert (workspace / "accepted.docx").is_file() and (workspace / "processing.json").is_file()
    response = client.get(f"/api/v1/conversions/{job['id']}/validation")
    assert response.status_code == 200
    result = response.json()
    assert result["document_processing"]["revision_acceptance"]["source_unchanged"]
    assert not result["complete"] and not result["sec_compliance_passed"]
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409


def test_resume_has_ownership_and_current_attempt_guards(client, settings):
    from conftest import TOKEN_B

    from workers.tasks.admission import admit_document

    job = upload_one(client)
    route = f"/api/v1/conversions/{job['id']}/resume"
    assert client.post(route).status_code == 409
    admit_document(job["id"], settings)
    previous = client.app.state.repository.get(job["id"], "alice")["attempt_id"]
    client.headers["Authorization"] = f"Bearer {TOKEN_B}"
    assert client.post(route).status_code == 404
    from conftest import TOKEN_A

    client.headers["Authorization"] = f"Bearer {TOKEN_A}"
    assert client.post(route).status_code == 202
    assert not client.app.state.repository.finish_processing(
        job["id"], previous, {"status": "pdf_validated", "diagnostics": []}
    )
    admit_document(job["id"], settings)
    assert client.app.state.repository.get(job["id"], "alice")["attempts"] == 2


def test_layout_stage_completion_never_enables_filing_download(client):
    job = upload_one(client)
    repository = client.app.state.repository
    record = repository.claim(job["id"])
    assert repository.finish_processing(
        job["id"], record["attempt_id"], {"status": "layout_analyzed", "diagnostics": []}
    )
    record = repository.get(job["id"], "alice")
    assert record["state"] == "blocked" and record["stage"] == "awaiting_htm_generation"
    assert record["diagnostic_code"] == "HTML_ENGINE_NOT_AVAILABLE"
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409


def test_htm_candidate_stops_before_compliance_and_download(client):
    job = upload_one(client)
    repository = client.app.state.repository
    record = repository.claim(job["id"])
    assert repository.finish_processing(
        job["id"], record["attempt_id"], {"status": "htm_generated", "diagnostics": []}
    )
    record = repository.get(job["id"], "alice")
    assert record["state"] == "blocked" and record["stage"] == "awaiting_sec_validation"
    assert record["diagnostic_code"] == "SEC_ENGINE_NOT_AVAILABLE"
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409
