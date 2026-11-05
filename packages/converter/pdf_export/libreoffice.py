from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from converter.context import ProcessingContext
from converter.errors import fail
from converter.ooxml import sha256
from converter.pdf_export.process import run_process
from converter.pdf_export.provider import RenderedPDF


def font_fingerprint(directories: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        {
            p.resolve()
            for directory in directories
            if directory.exists()
            for p in directory.rglob("*")
            if p.is_file() and p.suffix.lower() in {".ttf", ".otf", ".ttc"}
        }
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


class LibreOfficeProvider:
    def __init__(
        self,
        executable: Path | None = None,
        timeout_seconds: int = 180,
        memory_limit_bytes: int = 1024 * 1024 * 1024,
        max_pdf_bytes: int = 64 * 1024 * 1024,
        font_directories: list[Path] | None = None,
    ):
        detected = shutil.which("soffice") if executable is None else None
        self.executable = executable or (Path(detected) if detected else None)
        self.timeout_seconds, self.memory_limit_bytes, self.max_pdf_bytes = (
            timeout_seconds,
            memory_limit_bytes,
            max_pdf_bytes,
        )
        self.font_directories = font_directories or (
            [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"]
            if os.name == "nt"
            else [Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
        )

    def render(self, accepted_docx: Path, workspace: Path, context: ProcessingContext) -> RenderedPDF:
        if not self.executable or not self.executable.is_file():
            raise fail(
                "PDF_RENDERER_UNAVAILABLE",
                "generating_pdf",
                "LibreOffice executable is not configured or installed",
                "Install free LibreOffice and configure its absolute executable path",
            )
        executable = self.executable.resolve()
        workspace.mkdir(mode=0o700, parents=True, exist_ok=False)
        profile = workspace / "profile"
        user = profile / "user"
        user.mkdir(mode=0o700, parents=True)
        # Fresh profile: no document macros, Java runtime, update checks or remembered connections.
        (user / "registrymodifications.xcu").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="AllowMacroExecution" oor:op="fuse"><value>false</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Java/VirtualMachine"><prop oor:name="Enable" oor:op="fuse"><value>false</value></prop></item>'
            "</oor:items>",
            encoding="utf-8",
        )
        version = (
            run_process([str(executable), "--version"], workspace, context, 15)
            .decode(errors="replace")
            .strip()
        )
        if not version.startswith("LibreOffice ") or len(version) > 256:
            raise fail(
                "UNRECOGNIZED_RENDERER",
                "generating_pdf",
                "Renderer identity could not be verified",
                "Configure a supported LibreOffice executable",
            )
        options = {
            "UseLosslessCompression": {"type": "boolean", "value": "true"},
            "ExportFormFields": {"type": "boolean", "value": "false"},
            "ExportNotes": {"type": "boolean", "value": "false"},
            "ExportBookmarks": {"type": "boolean", "value": "false"},
        }
        output = workspace / "pdf"
        output.mkdir(mode=0o700)
        run_process(
            [
                str(executable),
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--norestore",
                "--nofirststartwizard",
                "--convert-to",
                "pdf:writer_pdf_Export:" + json.dumps(options, separators=(",", ":")),
                "--outdir",
                str(output),
                str(accepted_docx.resolve()),
            ],
            workspace,
            context,
            self.timeout_seconds,
            self.memory_limit_bytes,
            artifact_directory=output,
            artifact_limit_bytes=self.max_pdf_bytes,
        )
        context.check()
        candidate = output / (accepted_docx.stem + ".pdf")
        if (
            not candidate.is_file()
            or candidate.stat().st_size == 0
            or candidate.stat().st_size > self.max_pdf_bytes
        ):
            raise fail(
                "INVALID_PDF_OUTPUT",
                "generating_pdf",
                "Renderer produced no bounded PDF output",
                "Inspect renderer and document support",
            )
        return RenderedPDF(
            candidate, "libreoffice", version, sha256(executable), font_fingerprint(self.font_directories)
        )
