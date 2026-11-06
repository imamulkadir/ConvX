"""Real Windows sharing locks, not mocked filesystem failures."""

import ctypes
import json
import os
import threading
import time
from ctypes import wintypes

import pytest
from converter.pipeline import write_report

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows file-sharing regression")


def lock_report(path):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # Permit reading/writing, but deny rename/delete until this handle closes.
    handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 128, None)
    assert handle != ctypes.c_void_p(-1).value
    return kernel, handle


def test_progress_publication_recovers_from_a_real_short_reader_lock(tmp_path):
    path = tmp_path / "progress.json"
    write_report(path, {"stage": "validating"})
    kernel, handle = lock_report(path)

    def release():
        time.sleep(0.15)
        kernel.CloseHandle(handle)

    thread = threading.Thread(target=release)
    thread.start()
    try:
        write_report(path, {"stage": "accepting_revisions"})
    finally:
        thread.join(timeout=2)
    assert json.loads(path.read_text()) == {"stage": "accepting_revisions"}
    assert not path.with_suffix(".part").exists()


def test_permanent_reader_lock_fails_bounded_and_preserves_complete_old_json(tmp_path):
    path = tmp_path / "progress.json"
    write_report(path, {"stage": "validating"})
    kernel, handle = lock_report(path)
    started = time.monotonic()
    try:
        with pytest.raises(PermissionError):
            write_report(path, {"stage": "accepting_revisions"})
        assert time.monotonic() - started < 2
        assert json.loads(path.read_text()) == {"stage": "validating"}
    finally:
        kernel.CloseHandle(handle)
