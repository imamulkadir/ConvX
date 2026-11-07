import json
import os
import subprocess
import sys

import pytest
from conftest import ROOT, docx_bytes
from converter.admission import validate_docx
from converter.artifacts import private_path
from converter.runtime_config import AdmissionError, Limits


def test_supervisor_revokes_published_completion_after_monitor_failure(tmp_path, monkeypatch):
    """A deliberately untrusted completion sentinel must never grant success."""
    import signal

    from converter import runtime
    from converter.errors import fail
    from converter.visual_validation.browser import browser_cache

    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browser_cache().resolve()))

    def monitor_failure(*args, **kwargs):
        runtime.write_report(
            tmp_path / "result.json",
            {"status": "packaged", "final_conversion_complete": True, "diagnostics": []},
        )
        raise fail(
            "RENDERER_MEMORY_LIMIT",
            "processing",
            "Memory monitor rejected the child",
            "Review the resource budget",
        )

    monkeypatch.setattr(runtime, "run_process", monitor_failure)
    handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        assert runtime.supervise(tmp_path / "request.json") == 2
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["status"] == "failed" and not report["final_conversion_complete"]
    assert report["diagnostics"][-1]["code"] == "CONVERSION_RENDERER_MEMORY_LIMIT"
    assert json.loads((tmp_path / "supervision.json").read_text())["error_type"] == "ConversionFailure"


def test_pure_admission_accepts_real_docx_and_rejects_active_package(tmp_path):
    source = tmp_path / "input.docx"
    source.write_bytes(docx_bytes())
    validate_docx(source, Limits())
    source.write_bytes(docx_bytes({"word/vbaProject.bin": b"active"}))
    with pytest.raises(AdmissionError, match="ACTIVE_CONTENT"):
        validate_docx(source, Limits())


def test_direct_python_process_runs_real_revision_acceptance_without_web_imports(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(docx_bytes())
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"original_filename": "test.docx"}))
    environment = dict(
        os.environ,
        CONVX_LIBREOFFICE_EXECUTABLE=str(tmp_path / "not-installed"),
        PYTHONPATH=str(ROOT / "packages"),
    )
    result = subprocess.run(  # noqa: S603 - fixed trusted converter invocation
        [sys.executable, "-m", "converter.runtime", str(request)],
        cwd=ROOT,
        env=environment,
        timeout=30,
        capture_output=True,
    )  # noqa: S603 - fixed trusted converter invocation
    assert result.returncode == 2
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["revision_acceptance"]["after"]["total"] == 0
    assert report["source_unchanged"] and not report["final_conversion_complete"]
    assert report["diagnostics"][0]["code"] == "PDF_RENDERER_UNAVAILABLE"
    assert (tmp_path / "attempt001/accepted.docx").is_file()


@pytest.mark.parametrize("value", ["../secret", "/absolute", "C:/secret", "a\\b"])
def test_private_artifacts_reject_escape(tmp_path, value):
    with pytest.raises(ValueError):
        private_path(tmp_path, value)


def test_converter_entry_has_no_service_dependency():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import converter.runtime,sys; assert not any(n in sys.modules for n in ('app.main','workers.worker','fastapi','sqlalchemy','celery'))",
        ],
        capture_output=True,
        timeout=20,
    )  # noqa: S603 - fixed import-isolation test
    assert result.returncode == 0, result.stderr
