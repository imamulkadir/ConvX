from __future__ import annotations

import argparse
from pathlib import Path

from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.pipeline import process_docx
from converter.sec_validation.models import SubmissionContext


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
    parser.add_argument("--form-type")
    parser.add_argument("--encoded-submission-bytes", type=int)
    args = parser.parse_args()
    if (args.form_type is None) != (args.encoded_submission_bytes is None):
        parser.error("Supply both form and actual whole MIME-encoded submission size")
    submission = (
        SubmissionContext(form_type=args.form_type, encoded_submission_bytes=args.encoded_submission_bytes)
        if args.form_type
        else None
    )
    # Complete application admission is kept at the orchestration boundary, not imported by modules.
    from converter.admission import validate_docx
    from converter.runtime_config import Limits

    validate_docx(args.source, Limits())
    result = process_docx(
        args.source,
        args.workspace,
        LibreOfficeProvider(args.libreoffice, memory_limit_bytes=args.renderer_memory_mib * 1024 * 1024),
        args.reference_pdf,
        args.expected_accepted_docx,
        submission=submission,
    )
    print(f"Document processing result: {result['status']}; report: {args.workspace / 'processing.json'}")
    raise SystemExit(0 if result["status"] == "packaged" else 2)


if __name__ == "__main__":
    main()
