"""Real browser failures must never become downloadable filing packages."""

import copy
import json

import pytest
from app.models.database import jobs
from app.services.downloads import availability, content_disposition, private_artifact, read_processing
from conftest import upload_one
from converter.errors import ConversionFailure
from converter.packaging.engine import create_package, visual_evidence_consistent
from converter.pdf_export.validation import validate_pdf
from converter.sec_validation.models import SubmissionContext
from converter.sec_validation.validator import validate_files
from converter.visual_validation.engine import compare_visuals
from converter.visual_validation.models import VisualResult
from layout_fixtures import simple_pdf
from sqlalchemy import update


@pytest.fixture(scope="module")
def failed_evidence(tmp_path_factory):
    root = tmp_path_factory.mktemp("actual-package-gates")
    filing = root / "filing"
    filing.mkdir()
    htm = filing / "filing.htm"
    htm.write_bytes(b"<html><body><p>Actual different disclosure</p></body></html>")
    pdf = simple_pdf(root / "source.pdf")
    submission = SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
    proof = validate_pdf(pdf, pdf)
    sec = validate_files(htm, submission=submission)
    assert proof["passed"] and sec.strict_passed
    visual = compare_visuals(pdf, htm, (), proof, sec, root / "visual", submission=submission)
    assert visual.checks_complete and not visual.strict_passed
    return pdf, htm, proof, sec, visual, submission


@pytest.mark.parametrize("mutation", ["none", "top_level_flags", "stale_html", "failed_pdf", "failed_sec"])
def test_packager_rejects_actual_failed_or_stale_evidence(failed_evidence, tmp_path, mutation):
    pdf, original, proof, sec, visual, submission = failed_evidence
    # A new filing root keeps the module fixture immutable.
    filing = tmp_path / "filing"
    filing.mkdir()
    htm = filing / original.name
    htm.write_bytes(original.read_bytes())
    proof = copy.deepcopy(proof)
    if mutation == "top_level_flags":
        adversarial = visual.model_dump(mode="json")
        adversarial.update(strict_passed=True, comparison_passed=True, diagnostics=[])
        for page in adversarial["pages"]:
            page["passed"] = True
        visual = VisualResult.model_validate(adversarial)
        # Flipping flags cannot erase the genuine underlying measurements.
        assert not visual_evidence_consistent(visual)
    elif mutation == "stale_html":
        htm.write_bytes(b"<html><body>Changed after validation</body></html>")
    elif mutation == "failed_pdf":
        proof["passed"] = False
    elif mutation == "failed_sec":
        sec = sec.model_copy(update={"strict_passed": False})
    output = tmp_path / "package"
    with pytest.raises(ConversionFailure):
        create_package("filing.docx", pdf, htm, (), proof, sec, visual, output, submission)
    assert not output.exists()


def test_packaged_flags_alone_fail_job_completion(client):
    job = upload_one(client)
    repository = client.app.state.repository
    record = repository.claim(job["id"])
    assert repository.finish_processing(
        job["id"],
        record["attempt_id"],
        {
            "status": "packaged",
            "final_conversion_complete": True,
            "source_unchanged": True,
            "diagnostics": [],
        },
    )
    result = client.get(f"/api/v1/conversions/{job['id']}").json()
    assert result["state"] == "failed" and not result["download_available"]
    assert result["diagnostic_code"] == "PACKAGE_COMPLETION_INVALID"
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409


@pytest.mark.parametrize("contents", [b"[]", b"{", b"null", b"{}", b" " * (8 * 1024 * 1024 + 1)])
def test_corrupt_completed_metadata_cannot_enable_download(client, contents):
    job = upload_one(client)
    repository, storage = client.app.state.repository, client.app.state.storage
    record = repository.claim(job["id"])
    attempt = storage.attempt(job["id"], record["attempt_id"])
    attempt.mkdir(parents=True, exist_ok=True)
    (attempt / "processing.json").write_bytes(contents)
    # Fault injection: even a corrupted completed database row grants no artifact access.
    with client.app.state.database.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(state="completed"))
    record = repository.get(job["id"], "alice")
    assert read_processing(storage, record) is None and not availability(storage, record)
    route = f"/api/v1/conversions/{job['id']}"
    assert not client.get(route).json()["download_available"]
    assert not client.get(route + "/validation").json()["complete"]
    assert client.get(route + "/download").status_code == 409


def test_stale_attempt_or_source_metadata_is_not_read(client):
    job = upload_one(client)
    storage = client.app.state.storage
    record = client.app.state.repository.claim(job["id"])
    attempt = storage.attempt(job["id"], record["attempt_id"])
    attempt.mkdir(parents=True, exist_ok=True)
    (attempt / "processing.json").write_text(json.dumps({"source_sha256": "0" * 64}))
    assert read_processing(storage, record) is None


@pytest.mark.parametrize(
    "relative", ["../secret", "/secret", "C:/secret", "filing/../../secret", "filing\\secret"]
)
def test_download_artifact_paths_remain_in_attempt(tmp_path, relative):
    with pytest.raises(ValueError):
        private_artifact(tmp_path, relative)


def test_unicode_download_name_is_rfc5987_encoded():
    header = content_disposition("রিপোর্ট final.zip")
    assert header.startswith("attachment; filename*=utf-8''")
    assert "%20" in header and "\r" not in header and "\n" not in header
    assert "র" not in header
