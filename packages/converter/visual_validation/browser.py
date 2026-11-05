from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from converter.errors import ConversionFailure, fail
from converter.pdf_export.process import run_process


def browser_cache():
    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if configured == "0":
        import playwright

        return Path(playwright.__file__).parent / "driver/package/.local-browsers"
    if configured:
        return Path(configured).resolve()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "ms-playwright"
    return (
        Path.home() / "Library/Caches/ms-playwright"
        if sys.platform == "darwin"
        else Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "ms-playwright"
    )


def render_browser(resources, htm_name, page_size, workspace, policy, context):
    workspace = workspace.resolve()
    workspace.mkdir(mode=0o700)
    inputs = workspace / "input"
    inputs.mkdir(mode=0o700)
    for name, data in resources.items():
        with (inputs / name).open("xb") as stream:
            os.chmod(inputs / name, 0o600)
            stream.write(data)
    request = {
        "workspace": str(workspace.resolve()),
        "browser_cache": str(browser_cache().resolve()),
        "resources": list(resources),
        "htm_name": htm_name,
        "page_size_pt": page_size,
        "policy": policy.model_dump(mode="json"),
    }
    path = workspace / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    os.chmod(path, 0o600)
    try:
        data = run_process(
            [sys.executable, "-m", "converter.visual_validation.browser_worker", str(path.resolve())],
            workspace,
            context,
            policy.browser_timeout_seconds,
            policy.browser_memory_bytes,
            65536,
            workspace,
            policy.max_evidence_bytes + policy.max_input_bytes + policy.max_pdf_bytes,
        )
    except ConversionFailure as exc:
        if exc.diagnostic.code in {"PROCESSING_CANCELLED", "PROCESSING_TIMEOUT"}:
            raise
        raise fail(
            "VISUAL_" + exc.diagnostic.code,
            "comparing_formatting",
            "Isolated browser process exceeded resources or failed",
            "Review the private browser/worker profile without exposing disclosure text",
        ) from exc
    try:
        result = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise fail(
            "VISUAL_BROWSER_FAILED",
            "comparing_formatting",
            "Browser returned invalid control metadata",
            "Review the pinned browser environment",
        ) from exc
    if result.get("error"):
        raise fail(
            result["error"],
            "comparing_formatting",
            "Browser could not produce bounded render evidence",
            "Install the pinned Chromium build or inspect the isolated environment",
        )
    return json.loads((workspace / "browser.json").read_text(encoding="utf-8"))
