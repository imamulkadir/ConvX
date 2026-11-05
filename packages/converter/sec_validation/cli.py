from __future__ import annotations

import argparse
import json
from pathlib import Path

from converter.sec_validation.models import SubmissionContext
from converter.sec_validation.validator import validate_files


def main():
    parser = argparse.ArgumentParser(
        description="Local versioned ordinary-HTM validation; not SEC acceptance"
    )
    parser.add_argument("htm", type=Path)
    parser.add_argument("--assets", type=Path, nargs="*", default=[])
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
    result = validate_files(args.htm, tuple(args.assets), submission)
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=True))
    raise SystemExit(0 if result.strict_passed else 2)


if __name__ == "__main__":
    main()
