from __future__ import annotations

import hashlib
import os
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from lxml import etree

from converter.context import ProcessingContext
from converter.errors import fail
from converter.ooxml import local, parse_xml, read_package, sha256, visible_text, word
from converter.revisions.inventory import MOVE_RANGES, PROPERTY_CHANGES, inventory, revision_name

BLOCK_OR_INLINE = {
    "p",
    "body",
    "hyperlink",
    "sdtContent",
    "smartTag",
    "customXml",
    "txbxContent",
    "footnote",
    "endnote",
    "hdr",
    "ftr",
    "tc",
    "tbl",
    "tr",
    "ins",
    "del",
    "moveFrom",
    "moveTo",
}


def _unwrap(element) -> None:
    parent = element.getparent()
    position = parent.index(element)
    for child in list(element):
        parent.insert(position, child)
        position += 1
    parent.remove(element)


def _problem(part: str, root, element, detail: str):
    return fail(
        "UNSUPPORTED_REVISION",
        "accepting_revisions",
        detail,
        "Accept this revision in a trusted editor and provide a verified clean DOCX",
        file=part,
        element=root.getroottree().getpath(element),
    )


def _transform(root, part: str, context: ProcessingContext) -> None:
    # Old property snapshots are not current formatting. Never restore them.
    for element in list(root.iter()):
        if local(element) in PROPERTY_CHANGES and element.getparent() is not None:
            expected_parent = (
                "numPr" if local(element) == "numberingChange" else local(element).removesuffix("Change")
            )
            if local(element.getparent()) != expected_parent:
                raise _problem(
                    part, root, element, "Property revision is outside its defined property container"
                )
            element.getparent().remove(element)

    # Reject malformed/unpaired move ranges; payload wrappers supply accepted reading content.
    for kind in ("moveFrom", "moveTo"):
        starts, ends = Counter(), Counter()
        wrappers = [e for e in root.iter() if word(e, kind) and local(e.getparent()) != "rPr"]
        for element in root.iter():
            if word(element, kind + "RangeStart"):
                starts[element.get("{" + etree.QName(element).namespace + "}id")] += 1
            elif word(element, kind + "RangeEnd"):
                ends[element.get("{" + etree.QName(element).namespace + "}id")] += 1
        if starts != ends or any(count != 1 for count in starts.values()) or (starts and not wrappers):
            raise _problem(part, root, root, "Moved-content ranges are ambiguous or unpaired")
    move_from = [e for e in root.iter() if word(e, "moveFrom") and local(e.getparent()) != "rPr"]
    move_to = [e for e in root.iter() if word(e, "moveTo") and local(e.getparent()) != "rPr"]
    if bool(move_from) != bool(move_to) or len(move_from) != len(move_to):
        raise _problem(part, root, root, "Moved content has no verified source/destination pair in its story")

    # Paragraph-mark deletion is a paragraph join, not removal of its disclosure runs.
    for element in list(root.iter()):
        context.check()
        if not word(element, "del") or local(element.getparent()) != "rPr":
            continue
        if any(local(e) in {"del", "moveFrom"} for e in element.iterancestors()):
            continue
        rpr = element.getparent()
        ppr = rpr.getparent()
        paragraph = ppr.getparent() if ppr is not None else None
        following = paragraph.getnext() if paragraph is not None else None
        if (
            not word(ppr, "pPr")
            or not word(paragraph, "p")
            or not word(following, "p")
            or any(local(e) == "sectPr" for e in paragraph.iter())
            or any(local(e) == "sectPr" for e in following.iter())
        ):
            raise _problem(
                part, root, element, "Paragraph deletion crosses an unsupported section/block boundary"
            )
        # The surviving paragraph mark owns the resulting paragraph properties.
        position = 1 if len(following) and word(following[0], "pPr") else 0
        for child in list(paragraph):
            if not word(child, "pPr"):
                following.insert(position, child)
                position += 1
        paragraph.getparent().remove(paragraph)

    # Row deletions remove the row even if its text is not independently marked deleted.
    for element in list(root.iter()):
        if word(element, "del") and local(element.getparent()) == "trPr":
            row = element.getparent().getparent()
            if not word(row, "tr") or row.getparent() is None:
                raise _problem(part, root, element, "Invalid table-row deletion")
            row.getparent().remove(row)

    def visit(parent):
        for element in list(parent):
            context.check()
            name = revision_name(element)
            if name in {"del", "moveFrom"}:
                if local(parent) not in BLOCK_OR_INLINE:
                    raise _problem(part, root, element, "Unsupported deletion/move context")
                parent.remove(element)
            elif name in {"ins", "moveTo"}:
                if local(parent) == "trPr" and name == "ins":
                    parent.remove(element)
                elif local(parent) == "rPr" and word(parent.getparent(), "pPr") and name == "ins":
                    parent.remove(element)  # Accepted inserted paragraph mark stays a paragraph break.
                elif local(parent) in BLOCK_OR_INLINE:
                    visit(element)
                    _unwrap(element)
                else:
                    raise _problem(part, root, element, "Unsupported insertion/move context")
            elif name in MOVE_RANGES:
                parent.remove(element)
            else:
                visit(element)

    visit(root)
    for table in list(root.iter()):
        if word(table, "tbl") and not any(word(e, "tr") for e in table):
            table.getparent().remove(table)
    # A deleted restart row could invalidate a continuing vertical merge. Fail rather than guess.
    for table in root.iter():
        if not word(table, "tbl"):
            continue
        previous = set()
        for row in (e for e in table if word(e, "tr")):
            column, active = 0, set()
            for cell in (e for e in row if word(e, "tc")):
                props = next((e for e in cell if word(e, "tcPr")), None)
                span, merge = 1, None
                for prop in props if props is not None else []:
                    if word(prop, "gridSpan"):
                        try:
                            span = int(prop.get("{" + etree.QName(prop).namespace + "}val", "1"))
                        except ValueError as exc:
                            raise _problem(part, root, prop, "Invalid table grid span") from exc
                    if word(prop, "vMerge"):
                        merge = prop.get("{" + etree.QName(prop).namespace + "}val", "continue")
                if span < 1:
                    raise _problem(part, root, cell, "Invalid table grid span")
                if merge == "continue" and not all(c in previous for c in range(column, column + span)):
                    raise _problem(part, root, cell, "Vertical merge lost its restart cell")
                if merge is not None:
                    active.update(range(column, column + span))
                column += span
            previous = active


def accept_revisions(source: Path, destination: Path, context: ProcessingContext | None = None) -> dict:
    context = context or ProcessingContext()
    if source.resolve() == destination.resolve() or destination.exists():
        raise fail(
            "UNSAFE_OUTPUT_PATH",
            "accepting_revisions",
            "Accepted output must be a new file",
            "Choose a new private output path",
        )
    original_hash = sha256(source)
    parts = read_package(source, context)
    before = inventory(parts)
    if before["unsupported"]:
        first = before["unsupported"][0]
        raise fail(
            "UNSUPPORTED_REVISION",
            "accepting_revisions",
            "An unsupported revision was detected",
            "Resolve the reported revision in a trusted editor",
            file=first["file"],
            element=first["element"],
        )
    output, changed_parts = dict(parts), []
    for name, payload in sorted(parts.items()):
        context.check()
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        root = parse_xml(payload, name)
        changed = name in before["parts"]
        if changed:
            _transform(root, name, context)
        for element in list(root.iter()):
            if word(element, "trackRevisions"):
                element.getparent().remove(element)
                changed = True
        if changed:
            output[name] = etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)
            changed_parts.append(name)
    after = inventory(output)
    if after["total"] or after["unsupported"]:
        raise fail(
            "UNRESOLVED_REVISIONS",
            "accepting_revisions",
            "Tracked revisions remain after processing",
            "Inspect the unsupported story/revision",
        )
    media = {n: hashlib.sha256(v).hexdigest() for n, v in parts.items() if n.startswith("word/media/")}
    if any(hashlib.sha256(output[n]).hexdigest() != digest for n, digest in media.items()):
        raise fail(
            "MEDIA_INTEGRITY_FAILED",
            "accepting_revisions",
            "An embedded image changed",
            "Do not use the accepted output",
        )
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    try:
        with temporary.open("xb") as file:
            os.chmod(temporary, 0o600)
            with ZipFile(file, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
                for name, payload in sorted(output.items()):
                    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type, info.external_attr = ZIP_DEFLATED, 0o600 << 16
                    archive.writestr(info, payload)
            file.flush()
            os.fsync(file.fileno())
        context.check()
        verified = read_package(temporary, context)
        if inventory(verified)["total"] or sha256(source) != original_hash:
            raise fail(
                "REVISION_VERIFICATION_FAILED",
                "accepting_revisions",
                "Revision/source integrity verification failed",
                "Do not use this output",
            )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "engine": "convx-ooxml-v1",
        "source_sha256": original_hash,
        "accepted_sha256": sha256(destination),
        "before": before,
        "after": after,
        "changed_parts": changed_parts,
        "media_sha256": media,
        "media_preserved": True,
        "source_unchanged": True,
    }


def compare_accepted_content(actual: Path, expected: Path) -> dict:
    """Content/structure regression, not DOCX byte equivalence or visual proof."""
    left, right = read_package(actual), read_package(expected)

    def stories(parts):
        return {
            n
            for n in parts
            if n.startswith("word/")
            and n.endswith(".xml")
            and (
                n == "word/document.xml" or any(s in n for s in ("header", "footer", "footnotes", "endnotes"))
            )
        }

    differences, records = [], []
    for name in sorted(stories(left) | stories(right)):
        if name not in left or name not in right:
            differences.append({"file": name, "code": "STORY_PART_MISMATCH"})
            continue
        a, b = parse_xml(left[name], name), parse_xml(right[name], name)

        # Compare text paragraph-by-paragraph so identical concatenation cannot hide lost boundaries.
        def signature(root):
            return [
                (local(e), visible_text(e) if word(e, "p") else None)
                for e in root.iter()
                if any(word(e, tag) for tag in ("p", "tbl", "tr", "tc"))
            ]

        match = signature(a) == signature(b)
        records.append({"file": name, "matches": match})
        if not match:
            differences.append({"file": name, "code": "ACCEPTED_CONTENT_MISMATCH"})
    return {
        "passed": not differences,
        "stories": records,
        "diagnostics": differences,
        "method": "ordered-story-paragraph-text-and-table-structure-v1",
    }
