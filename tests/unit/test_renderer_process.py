import sys
import time

import psutil
import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.pdf_export.process import run_process


def test_process_timeout_and_bounded_error_output(tmp_path):
    with pytest.raises(ConversionFailure, match="RENDERER_TIMEOUT"):
        run_process([sys.executable, "-c", "import time; time.sleep(20)"], tmp_path, ProcessingContext(), 0.4)
    with pytest.raises(ConversionFailure, match="RENDERER_OUTPUT_LIMIT"):
        run_process(
            [sys.executable, "-c", "print('x'*10000)"],
            tmp_path,
            ProcessingContext(),
            5,
            output_limit_bytes=100,
        )


def test_cancellation_terminates_owned_child(tmp_path):
    marker = tmp_path / "child.pid"
    script = tmp_path / "spawn.py"
    script.write_text(
        "import subprocess,sys,time\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\nPath('child.pid').write_text(str(p.pid))\ntime.sleep(60)\n"
    )
    try:
        with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
            run_process(
                [sys.executable, str(script)],
                tmp_path,
                ProcessingContext(cancelled=lambda: marker.exists()),
                10,
            )
        assert marker.exists()
        pid = int(marker.read_text())
        assert not psutil.pid_exists(pid)
    finally:
        # Cleanup only this test's identified child if the assertion exposes a platform defect.
        if marker.exists():
            pid = int(marker.read_text())
            try:
                process = psutil.Process(pid)
                if process.create_time() > time.time() - 30 and process.name().lower().startswith("python"):
                    process.kill()
            except psutil.NoSuchProcess:
                pass


def test_renderer_memory_limit_is_enforced(tmp_path):
    with pytest.raises(ConversionFailure, match="RENDERER_MEMORY_LIMIT"):
        run_process(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            tmp_path,
            ProcessingContext(),
            5,
            memory_limit_bytes=1,
        )
