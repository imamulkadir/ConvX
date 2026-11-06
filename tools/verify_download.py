"""Read-only QA verification of real saved ZIPs against current source/evidence.

This tool is for integration tests, not a new application service or approval gate.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pymupdf
from lxml import html


def verify_archive(archive_path, pdf_path, report):
    if not __debug__:
        raise RuntimeError("Archive QA requires Python assertions enabled")
    from converter.ooxml import sha256

    package, mode = report["packaging"], report["mode"]
    assert report["status"] == "packaged" and report["final_conversion_complete"] is True
    assert report["source_unchanged"] is True and package["mode"] == mode
    assert not archive_path.is_symlink() and archive_path.stat().st_size <= 128 * 1024 * 1024
    assert sha256(archive_path) == package["sha256"] and archive_path.stat().st_size == package["bytes"]
    assert sha256(pdf_path) == package["source_pdf_sha256"]
    filename = package["document_filename"]
    expected = {f["filename"]: f for f in package["files"]}
    assert filename.endswith(".html" if mode == "standard" else ".htm")
    assert package["download_filename"] == Path(report["original_filename"]).stem + ".zip"
    if mode == "standard":
        assert filename == Path(report["original_filename"]).stem + ".html"
    else:
        assert len(filename) <= 32 and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.htm", filename)
    with ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == len(expected) and set(names) == set(expected)
        assert len([n for n in names if n.lower().endswith((".html", ".htm"))]) == 1
        assert all("/" not in n and "\\" not in n and ":" not in n for n in names)
        assert all(
            n == filename
            or n.endswith(
                (".jpg", ".gif") if mode == "edgar" else (".jpg", ".png", ".gif", ".webp", ".svg", ".jpeg")
            )
            for n in names
        )
        actual = archive.read(filename)
        from hashlib import sha256 as digest

        for name in names:
            data = archive.read(name)
            assert digest(data).hexdigest() == expected[name]["sha256"]
            assert len(data) == expected[name]["bytes"]
    tree = html.document_fromstring(actual, parser=html.HTMLParser(no_network=True))
    if mode == "standard":
        pages = tree.xpath("//section[contains(concat(' ',normalize-space(@class),' '),' page ')]")
        output = ["".join("".join(t.itertext()) for t in p.xpath(".//*[local-name()='text']")) for p in pages]
    else:
        pages = tree.xpath("/html/body/div")
        output = ["".join(p.itertext()) for p in pages]
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES & ~pymupdf.TEXT_MEDIABOX_CLIP
    source_pages, source_lines = [], []
    with pymupdf.open(pdf_path) as pdf:
        assert len(pages) == len(pdf)
        for page in pdf:
            page.set_rotation(0)
            raw = page.get_text("rawdict", flags=flags, clip=pymupdf.INFINITE_RECT(), sort=False)
            lines = [
                "".join(c["c"] for s in line["spans"] for c in s["chars"])
                for block in raw["blocks"]
                if block["type"] == 0
                for line in block["lines"]
            ]
            source_lines.extend(lines)
            source_pages.append("".join(lines))
    if mode == "standard":
        assert source_pages == output, "Saved HTML text differs from authoritative PDF character ledger"
    else:
        assert [Counter(t) for t in source_pages] == [Counter(t) for t in output], (
            "EDGAR disclosure characters changed"
        )
        actual_lines = ["".join(p.itertext()) for p in tree.xpath("/html/body//p")]
        assert Counter(re.findall(r"\S+", "\n".join(source_lines))) == Counter(
            re.findall(r"\S+", "\n".join(actual_lines))
        ), "EDGAR words or financial figures changed"
    visual = report[mode + "_visual_validation"]
    return {
        "mode": mode,
        "input_type": report["input_type"],
        "pages": len(pages),
        "characters": sum(map(len, output)),
        "source_unchanged": True,
        "archive_sha256": package["sha256"],
        "archive_bytes": package["bytes"],
        "members": names,
        "crc_verified": True,
        "source_text_verified": True,
        "text_check": "exact_ordered_character_ledger"
        if mode == "standard"
        else "per_page_characters_and_word_multiset",
        "screen_max_mean_channel_error": max(
            p["screen"]["mean_absolute_channel_error"] for p in visual["pages"]
        ),
        "print_max_mean_channel_error": max(
            p["print"]["mean_absolute_channel_error"] for p in visual["pages"]
        ),
        "pixel_equivalence_verified": visual["pixel_equivalence_verified"],
        "sec_acceptance_confirmed": False,
    }


def verify_saved_download(archive_path, job_root):
    from converter.artifacts import audit_download, private_path
    from converter.sec_validation.validator import read_bounded

    report = json.loads(read_bounded(job_root / "result.json", 8 * 1024 * 1024))
    fresh = audit_download(job_root, report)
    workspace = private_path(job_root, report["workspace"])
    summary = verify_archive(archive_path, private_path(workspace, report["generated_pdf_artifact"]), report)
    assert summary["archive_sha256"] == fresh["sha256"] and summary["archive_bytes"] == fresh["bytes"]
    summary["download_filename"] = fresh["filename"]
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("job_root", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))
    try:
        result = verify_saved_download(args.archive, args.job_root)
    except Exception:
        print(json.dumps({"verified": False, "error": "SAVED_ZIP_VERIFICATION_FAILED"}))
        return 1
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
