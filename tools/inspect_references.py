"""Read-only Stage 1 fixture inspection; no revision acceptance or layout engine."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REVISION_NAMES = {
    "ins", "del", "moveFrom", "moveTo", "moveFromRangeStart", "moveFromRangeEnd",
    "moveToRangeStart", "moveToRangeEnd", "pPrChange", "rPrChange", "tblPrChange",
    "tblGridChange", "trPrChange", "tcPrChange", "sectPrChange", "numberingChange",
    "cellIns", "cellDel", "cellMerge", "customXmlInsRangeStart", "customXmlInsRangeEnd",
    "customXmlDelRangeStart", "customXmlDelRangeEnd", "customXmlMoveFromRangeStart",
    "customXmlMoveFromRangeEnd", "customXmlMoveToRangeStart", "customXmlMoveToRangeEnd",
}


def inspect() -> dict:
    files = []
    for path in sorted((ROOT / "tests/fixtures").iterdir()):
        if path.suffix.lower() not in {".pdf", ".docx"}:
            continue
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        record = {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                  "sha256": digest}
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(path)
            record.update(page_count=len(reader.pages), encrypted=reader.is_encrypted,
                          pages=[{"page": i + 1, "media_box_pt": [float(x) for x in page.mediabox],
                                  "rotation": page.rotation,
                                  "extracted_characters": len(page.extract_text() or "")}
                                 for i, page in enumerate(reader.pages)])
            if path.name.startswith("edgarfm"):
                record["title_page_text"] = reader.pages[0].extract_text()
        else:
            with ZipFile(path) as archive:
                record["zip_crc_failure"] = archive.testzip()
                revisions, changes, totals = {}, {}, Counter()
                for name in sorted(archive.namelist()):
                    if not (name.startswith("word/") and name.endswith(".xml")):
                        continue
                    root = ET.fromstring(archive.read(name))
                    counts = Counter(e.tag[len(W):] for e in root.iter() if e.tag.startswith(W))
                    found = {k: v for k, v in sorted(counts.items()) if k in REVISION_NAMES}
                    if found:
                        revisions[name] = found
                    # Inventory evidence only; not a claim of comprehensive revision support.
                    other = {k: v for k, v in sorted(counts.items())
                             if k.endswith("Change") and k not in REVISION_NAMES}
                    if other:
                        changes[name] = other
                    totals.update(counts)
                record.update(revisions=revisions, other_change_elements=changes,
                              tables=totals["tbl"], sections=totals["sectPr"],
                              media=sorted(n for n in archive.namelist() if n.startswith("word/media/")))
        files.append(record)
    return {"schema_version": 1, "scope": "Stage 1 inventory; no conversion or acceptance testing", "files": files}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = json.dumps(inspect(), ensure_ascii=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
