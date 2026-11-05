from __future__ import annotations

import argparse
from pathlib import Path

from converter.errors import ConversionFailure
from converter.visual_validation.engine import inspect_visuals


def main():
    parser = argparse.ArgumentParser(
        description="Private diagnostic Chromium/PDF comparison; cannot authorize packaging"
    )
    parser.add_argument("source_pdf", type=Path)
    parser.add_argument("htm", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--assets", type=Path, nargs="*", default=[])
    parser.add_argument("--inspection-only", action="store_true", required=True)
    args = parser.parse_args()
    try:
        result = inspect_visuals(args.source_pdf, args.htm, tuple(args.assets), args.output)
        print(
            f"Inspection only: {len(result.pages)} pages checked; comparison passed: {result.comparison_passed}; strict passed: false"
        )
        raise SystemExit(0 if result.comparison_passed else 2)
    except ConversionFailure as exc:
        print(f"Visual inspection failed: {exc.diagnostic.code}")
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
