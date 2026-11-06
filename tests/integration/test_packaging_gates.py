"""Real browser failures must never become downloadable filing packages."""

import copy

import pytest
from converter.errors import ConversionFailure
from converter.packaging.engine import create_package, visual_evidence_consistent
from converter.pdf_export.validation import validate_pdf
from converter.sec_validation.models import SubmissionContext
from converter.sec_validation.validator import validate_files
from converter.visual_validation.engine import compare_visuals
from converter.visual_validation.models import VisualResult
from layout_fixtures import simple_pdf


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
