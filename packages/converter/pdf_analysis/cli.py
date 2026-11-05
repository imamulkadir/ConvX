from __future__ import annotations

import argparse
from pathlib import Path

from converter.pdf_analysis.extract import inspect_pdf, write_layout


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Private diagnostic PDF layout inspection; never authorizes reconstruction"
    )
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output", type=Path, help="A new private JSON path outside reference fixtures")
    parser.add_argument("--inspection-only", action="store_true", required=True)
    args = parser.parse_args()
    layout = inspect_pdf(args.pdf)
    summary = write_layout(args.output, layout)
    print(
        f"Inspection only: {summary['pages']} pages, {summary['characters']} characters; reconstruction eligible: false"
    )


if __name__ == "__main__":
    main()
