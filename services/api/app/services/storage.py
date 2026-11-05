from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path
from uuid import UUID

from starlette.datastructures import UploadFile

from app.core.config import Settings
from app.core.errors import Problem


def safe_filename(name: str | None) -> str:
    if not name or len(name.encode("utf-8")) > 240 or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise Problem(422, "INVALID_FILENAME", "Filename is missing or invalid")
    if any(c in name for c in '/\\:<>"|?*') or name.endswith((" ", ".")) or name.startswith("."):
        raise Problem(422, "INVALID_FILENAME", "Filename must be a plain basename")
    if not name.lower().endswith(".docx") or len(name) <= 5:
        raise Problem(415, "UNSUPPORTED_FILE_TYPE", "Only DOCX documents are accepted")
    return name


class Storage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.storage_root
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise RuntimeError("Storage root cannot be a symbolic link")

    def directory(self, job_id: str) -> Path:
        canonical = str(UUID(job_id))
        if canonical != job_id:
            raise ValueError("Noncanonical job ID")
        candidate = self.root / canonical
        if candidate.is_symlink() or candidate.resolve().parent != self.root:
            raise ValueError("Storage containment violation")
        return candidate

    def source(self, job_id: str) -> Path:
        path = self.directory(job_id) / "source.docx"
        if path.is_symlink():
            raise ValueError("Source cannot be a symbolic link")
        return path

    async def save(self, job_id: str, upload: UploadFile) -> tuple[int, str]:
        directory = self.directory(job_id)
        directory.mkdir(mode=0o700)
        part = directory / "source.part"
        count, digest = 0, hashlib.sha256()
        try:
            with part.open("xb") as output:
                os.chmod(part, 0o600)
                while chunk := await upload.read(64 * 1024):
                    count += len(chunk)
                    if count > self.settings.max_upload_bytes:
                        raise Problem(413, "FILE_TOO_LARGE", "Document exceeds the configured upload limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if count == 0:
                raise Problem(422, "EMPTY_FILE", "Document is empty")
            part.replace(self.source(job_id))
            return count, digest.hexdigest()
        except BaseException:
            self.remove(job_id)
            raise

    def remove(self, job_id: str) -> None:
        # Only a canonical UUID child of the dedicated storage root may be removed.
        directory = self.directory(job_id)
        if directory.exists():
            shutil.rmtree(directory)

    def cleanup_orphans(self, known_ids: set[str], grace_seconds: int) -> int:
        removed = 0
        cutoff = time.time() - grace_seconds
        for candidate in self.root.iterdir():
            try:
                if candidate.name not in known_ids and candidate.stat().st_mtime < cutoff:
                    self.remove(candidate.name)
                    removed += 1
            except (ValueError, FileNotFoundError):
                continue
        return removed
