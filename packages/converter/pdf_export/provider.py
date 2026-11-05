from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from converter.context import ProcessingContext


@dataclass(frozen=True)
class RenderedPDF:
    path: Path
    provider: str
    version: str
    executable_sha256: str
    font_environment_sha256: str


class PDFProvider(Protocol):
    def render(self, accepted_docx: Path, workspace: Path, context: ProcessingContext) -> RenderedPDF: ...
