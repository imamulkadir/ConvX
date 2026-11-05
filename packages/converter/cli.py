from __future__ import annotations

import argparse
from pathlib import Path

from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.pipeline import process_docx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Free DOCX processing, strict PDF gate and private HTM reconstruction"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "workspace", type=Path, help="A new private output directory; never the fixtures directory"
    )
    parser.add_argument("--libreoffice", type=Path)
    parser.add_argument("--reference-pdf", type=Path)
    parser.add_argument("--expected-accepted-docx", type=Path)
    parser.add_argument("--renderer-memory-mib", type=int, default=1024)
    args = parser.parse_args()
    # Complete application admission is kept at the orchestration boundary, not imported by modules.
    from app.core.config import Settings
    from app.services.admission import validate_docx

    settings = Settings(auth_mode="local", _env_file=None)
    validate_docx(args.source, settings)
    result = process_docx(
        args.source,
        args.workspace,
        LibreOfficeProvider(args.libreoffice, memory_limit_bytes=args.renderer_memory_mib * 1024 * 1024),
        args.reference_pdf,
        args.expected_accepted_docx,
    )
    print(f"Document processing result: {result['status']}; report: {args.workspace / 'processing.json'}")
    raise SystemExit(0 if result["status"] == "htm_generated" else 2)


if __name__ == "__main__":
    main()
