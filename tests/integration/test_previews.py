import json
import shutil

import pytest
from app.models.database import jobs
from conftest import TOKEN_B, upload_one
from converter.pdf_export.validation import validate_pdf
from converter.sec_validation.models import SubmissionContext
from converter.sec_validation.validator import validate_files
from converter.visual_validation.engine import compare_visuals
from layout_fixtures import simple_pdf
from sqlalchemy import update


@pytest.fixture(scope="module")
def actual_visual_failure(tmp_path_factory):
    root = tmp_path_factory.mktemp("preview-failure")
    pdf = simple_pdf(root / "source.pdf")
    htm = root / "filing.htm"
    htm.write_bytes(b"<html><body>Different actual disclosure</body></html>")
    submission = SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
    proof = validate_pdf(pdf, pdf)
    result = compare_visuals(
        pdf,
        htm,
        (),
        proof,
        validate_files(htm, submission=submission),
        root / "visual",
        submission=submission,
    )
    assert result.checks_complete and not result.strict_passed
    return root, proof, result


@pytest.fixture
def diagnostic_job(client, actual_visual_failure):
    root, proof, visual = actual_visual_failure
    job = upload_one(client)
    storage, repository = client.app.state.storage, client.app.state.repository
    record = repository.claim(job["id"])
    attempt = storage.attempt(job["id"], record["attempt_id"])
    attempt.mkdir(parents=True)
    shutil.copyfile(root / "source.pdf", attempt / "generated.pdf")
    shutil.copytree(root / "visual", attempt / "visual")
    report = {
        "source_sha256": record["source_sha256"],
        "source_unchanged": True,
        "status": "failed",
        "generated_pdf_artifact": "generated.pdf",
        "pdf_validation": proof,
        "visual_validation": visual.model_dump(mode="json"),
        "diagnostics": [{"code": "VISUAL_STRICT_VALIDATION_FAILED", "stage": "comparing_formatting"}],
    }
    (attempt / "processing.json").write_text(json.dumps(report), encoding="utf-8")
    repository.finish_processing(job["id"], record["attempt_id"], report)
    return job, attempt, report


def test_authenticated_session_exposes_actual_admission_limits(client, settings):
    response = client.get("/api/v1/conversions/session")
    assert response.status_code == 200
    assert response.json()["max_upload_bytes"] == settings.max_upload_bytes
    assert response.json()["max_batch_files"] == settings.max_batch_files
    client.headers.clear()
    assert client.get("/api/v1/conversions/session").status_code == 401


def test_failed_actual_visual_evidence_can_be_reviewed_but_not_downloaded(client, diagnostic_job):
    job, attempt, _ = diagnostic_job
    route = f"/api/v1/conversions/{job['id']}"
    meta = client.get(route + "/preview").json()
    assert meta["diagnostic_only"] and not meta["conversion_eligible"]
    assert meta["pages"] == 1 and meta["available_pages"]["htm"] == [1]
    for kind in ("pdf", "htm", "overlay", "difference"):
        response = client.get(route + f"/preview?kind={kind}&page=1")
        assert response.status_code == 200, (kind, response.text[:200], meta)
        assert "no-store" in response.headers["cache-control"]
        assert response.content.startswith(b"%PDF-" if kind == "pdf" else b"\x89PNG")
    assert client.get(route + "/preview?kind=pdf").content == (attempt / "generated.pdf").read_bytes()
    assert not client.get(route).json()["download_available"]
    assert client.get(route + "/download").status_code == 409


@pytest.mark.parametrize("mutation", ["pdf", "original", "pdf_path", "png", "unlisted"])
def test_changed_or_undeclared_preview_artifacts_fail(client, diagnostic_job, mutation):
    job, attempt, report = diagnostic_job
    kind = "htm"
    if mutation == "pdf":
        (attempt / "generated.pdf").write_bytes(b"%PDF- changed")
    elif mutation == "original":
        client.app.state.storage.source(job["id"]).write_bytes(b"changed source")
    elif mutation == "pdf_path":
        report["generated_pdf_artifact"] = "../../secret.pdf"
    elif mutation == "png":
        (attempt / "visual/page0001.screen.png").write_bytes(b"<script>active</script>")
    else:
        report["visual_validation"]["artifacts"] = []
    (attempt / "processing.json").write_text(json.dumps(report), encoding="utf-8")
    assert client.get(f"/api/v1/conversions/{job['id']}/preview?kind={kind}").status_code == 409


def test_preview_ownership_expiry_cancellation_and_page_bounds(client, diagnostic_job):
    job, _, _ = diagnostic_job
    route = f"/api/v1/conversions/{job['id']}/preview"
    for page in (0, 2, 999999):
        assert client.get(route + f"?kind=pdf&page={page}").status_code == 422
    assert client.get(route + "?kind=../../accepted.docx").status_code == 409
    client.headers["Authorization"] = f"Bearer {TOKEN_B}"
    assert client.get(route).status_code == 404
    client.headers["Authorization"] = "Bearer " + "a" * 40
    with client.app.state.database.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(expires_at=0))
    assert client.get(route).status_code == 410


def test_live_job_has_no_preview(client):
    job = upload_one(client)
    assert client.get(f"/api/v1/conversions/{job['id']}/preview").status_code == 409
