import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.pdf_export.validation import validate_pdf
from converter.sec_validation.models import SubmissionContext
from converter.sec_validation.validator import validate_files
from converter.visual_validation.browser import render_browser
from converter.visual_validation.engine import compare_visuals, inspect_visuals
from converter.visual_validation.models import VisualPolicy, VisualResult
from layout_fixtures import simple_pdf
from pydantic import ValidationError


@pytest.fixture
def baseline(tmp_path):
    markup = b'<html><body bgcolor="#ffffff"></body></html>'
    htm = tmp_path / "filing.htm"
    htm.write_bytes(markup)
    result = render_browser(
        {htm.name: markup}, htm.name, (300, 450), tmp_path / "baseline", VisualPolicy(), ProcessingContext()
    )
    assert result["browser_version"] == "156.0.8078.4"
    return tmp_path / "baseline/chromium.pdf", htm


def test_actual_chromium_gate_preserves_unexplained_screen_differences(tmp_path):
    markup = b"<html><body><p>Actual Chromium disclosure</p></body></html>"
    htm = tmp_path / "filing.htm"
    htm.write_bytes(markup)
    render_browser(
        {htm.name: markup}, htm.name, (300, 450), tmp_path / "baseline", VisualPolicy(), ProcessingContext()
    )
    pdf = tmp_path / "baseline/chromium.pdf"
    submission = SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
    report = compare_visuals(
        pdf,
        htm,
        (),
        validate_pdf(pdf, pdf),
        validate_files(htm, submission=submission),
        tmp_path / "visual",
        submission=submission,
    )
    assert report.checks_complete
    unexplained = report.pages[0]["screen_pixels"]["unexplained_difference_pixels"]
    assert report.strict_passed is (unexplained == 0)
    assert report.pdf_gate_sha256 and report.sec_gate_sha256
    assert report.renderer["javascript_enabled"] is False and report.renderer["denied_requests"] == 0
    assert report.renderer["sandbox_enabled"] and report.renderer["font_environment_sha256"]
    assert report.pages[0]["print_pixels"]["unexplained_difference_pixels"] == 0
    assert {"page0001.pdf.png", "page0001.print.png", "page0001.screen.png", "page0001.overlay.png"} <= set(
        report.artifacts
    )
    assert (tmp_path / "visual/visual.json").is_file()
    assert not report.sec_acceptance_confirmed


def test_inspection_never_authorizes_packaging_even_for_identical_images(baseline, tmp_path):
    pdf, htm = baseline
    report = inspect_visuals(pdf, htm, (), tmp_path / "inspection")
    assert report.comparison_passed and not report.strict_passed
    assert report.mode == "inspection_only" and report.pdf_gate_sha256 is None
    with pytest.raises(ValidationError):
        VisualResult.model_validate({**report.model_dump(), "strict_passed": True})


@pytest.mark.parametrize("change", ["content", "font", "displacement", "wrapping", "page_count"])
def test_real_browser_detects_structural_discrepancies(tmp_path, change):
    original = b"<html><body><p>Source disclosure text for comparison.</p></body></html>"
    htm = tmp_path / "filing.htm"
    htm.write_bytes(original)
    render_browser(
        {htm.name: original}, htm.name, (300, 450), tmp_path / "baseline", VisualPolicy(), ProcessingContext()
    )
    if change == "content":
        updated = "<html><body><p>Changed disclosure</p></body></html>"
    elif change == "font":
        updated = '<html><body><p style="font-family:Arial;font-size:20pt">Source disclosure text for comparison.</p></body></html>'
    elif change == "displacement":
        updated = (
            '<html><body><p style="margin-left:1px">Source disclosure text for comparison.</p></body></html>'
        )
    elif change == "wrapping":
        updated = '<html><body><p style="width:50px">Source disclosure text for comparison.</p></body></html>'
    else:
        updated = '<html><body><div style="height:450pt;page-break-after:always">Source disclosure text for comparison.</div><p>Extra page</p></body></html>'
    htm.write_text(updated, encoding="ascii")
    report = inspect_visuals(tmp_path / "baseline/chromium.pdf", htm, (), tmp_path / "difference")
    assert not report.comparison_passed and not report.strict_passed
    codes = {d.code for d in report.diagnostics}
    assert codes & {"VISUAL_CONTENT_MISMATCH", "VISUAL_GEOMETRY_MISMATCH", "VISUAL_PAGE_COUNT_MISMATCH"}
    if change == "font":
        assert codes & {
            "VISUAL_FONT_SUBSTITUTION",
            "VISUAL_FONT_SIZE_MISMATCH",
            "VISUAL_FONT_RESOURCE_DIFFERENCE",
            "VISUAL_FONT_SIZE_DIFFERENCE",
        }


def test_text_print_and_screen_disagreement_is_not_silently_relaxed(tmp_path):
    markup = b"<html><body><p>Actual Chromium disclosure</p></body></html>"
    htm = tmp_path / "filing.htm"
    htm.write_bytes(markup)
    render_browser(
        {htm.name: markup}, htm.name, (300, 450), tmp_path / "baseline", VisualPolicy(), ProcessingContext()
    )
    result = inspect_visuals(tmp_path / "baseline/chromium.pdf", htm, (), tmp_path / "evidence")
    assert result.pages[0]["print_pixels"]["raw_difference_pixels"] == 0
    assert result.pages[0]["geometry"]["content_equal"]
    if result.pages[0]["screen_pixels"]["unexplained_difference_pixels"]:
        assert not result.comparison_passed
    assert not result.strict_passed


@pytest.mark.parametrize("kind", ["pdf", "sec", "stale"])
def test_missing_or_stale_gates_never_launch_browser(baseline, tmp_path, monkeypatch, kind):
    pdf, htm = baseline
    pdf = simple_pdf(tmp_path / "text-source.pdf")
    submission = SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
    proof = validate_pdf(pdf, pdf)
    assert proof["passed"]
    sec = validate_files(htm, submission=submission)
    if kind == "pdf":
        proof["passed"] = False
    elif kind == "sec":
        sec = sec.model_copy(update={"strict_passed": False})
    else:
        htm.write_bytes(b"<p>Changed</p>")

    def forbidden(*args, **kwargs):
        raise AssertionError("Gate bypass reached renderer")

    monkeypatch.setattr("converter.visual_validation.engine.render_browser", forbidden)
    with pytest.raises(ConversionFailure):
        compare_visuals(pdf, htm, (), proof, sec, tmp_path / "output", submission=submission)
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "markup",
    [
        b"<script>alert(1)</script>",
        b'<img src="https://example.com/private.jpg">',
        b'<p style="background:url(https://example.com/x)">Text</p>',
    ],
)
def test_inspection_still_rejects_active_or_remote_content(baseline, tmp_path, markup):
    pdf, htm = baseline
    htm.write_bytes(markup)
    with pytest.raises(ConversionFailure, match="VISUAL_INSPECTION_UNSAFE"):
        inspect_visuals(pdf, htm, (), tmp_path / "unsafe")


def test_evidence_truncation_and_raster_budget_are_explicit(baseline, tmp_path):
    pdf, htm = baseline
    result = inspect_visuals(pdf, htm, (), tmp_path / "limited", VisualPolicy(max_evidence_bytes=1))
    assert result.evidence_truncated and not result.comparison_passed
    with pytest.raises(ConversionFailure, match="VISUAL_PIXEL_LIMIT"):
        inspect_visuals(pdf, htm, (), tmp_path / "pixels", VisualPolicy(max_total_pixels=1))


def test_owned_browser_memory_and_timeout_limits(baseline, tmp_path):
    pdf, htm = baseline
    with pytest.raises(ConversionFailure):
        inspect_visuals(
            pdf, htm, (), tmp_path / "memory", VisualPolicy(browser_memory_bytes=128 * 1024 * 1024)
        )
    with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
        inspect_visuals(pdf, htm, (), tmp_path / "cancel", context=ProcessingContext(cancelled=lambda: True))


def test_fidelity_success_still_does_not_enable_download(client):
    from conftest import upload_one

    job = upload_one(client)
    repository = client.app.state.repository
    record = repository.claim(job["id"])
    assert repository.finish_processing(
        job["id"], record["attempt_id"], {"status": "visual_validated", "diagnostics": []}
    )
    result = repository.get(job["id"], "alice")
    assert result["state"] == "blocked" and result["stage"] == "awaiting_packaging"
    assert result["diagnostic_code"] == "PACKAGING_ENGINE_NOT_AVAILABLE"
    assert client.get(f"/api/v1/conversions/{job['id']}/download").status_code == 409


def test_renderer_itself_blocks_document_scripts_and_remote_requests(tmp_path):
    markup = b'<html><body>Visible<script>document.body.textContent="executed"</script><img src="https://example.com/must-not-fetch.jpg"></body></html>'
    result = render_browser(
        {"filing.htm": markup},
        "filing.htm",
        (300, 450),
        tmp_path / "browser",
        VisualPolicy(),
        ProcessingContext(),
    )
    # CSP prevents the remote image before it even reaches the deny-all route hook.
    assert result["denied_requests"] == 0 and result["visible_text_characters"] == 7
    assert result["javascript_enabled"] is False and result["images"][0]["loaded"] is False


def test_overlapping_page_containers_are_not_accepted_as_page_mapping(tmp_path):
    markup = b'<html><body style="margin:0"><div style="width:300pt;height:450pt;page-break-after:always"></div><div style="margin:-450pt 0 0 0;width:300pt;height:450pt;page-break-after:always"></div></body></html>'
    result = render_browser(
        {"filing.htm": markup},
        "filing.htm",
        (300, 450),
        tmp_path / "browser",
        VisualPolicy(),
        ProcessingContext(),
    )
    assert result["screen_page_mapping"] == "unresolved"
