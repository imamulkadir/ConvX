from __future__ import annotations

from collections import Counter

from lxml import etree

from converter.ooxml import WORD_NAMESPACES, local, parse_xml

PROPERTY_CHANGES = {
    "pPrChange",
    "rPrChange",
    "tblPrChange",
    "tblPrExChange",
    "tblGridChange",
    "trPrChange",
    "tcPrChange",
    "sectPrChange",
    "numberingChange",
}
MOVE_RANGES = {"moveFromRangeStart", "moveFromRangeEnd", "moveToRangeStart", "moveToRangeEnd"}
SUPPORTED = PROPERTY_CHANGES | MOVE_RANGES | {"ins", "del", "moveFrom", "moveTo"}
KNOWN_UNSUPPORTED = {
    "cellIns",
    "cellDel",
    "cellMerge",
    "customXmlInsRangeStart",
    "customXmlInsRangeEnd",
    "customXmlDelRangeStart",
    "customXmlDelRangeEnd",
    "customXmlMoveFromRangeStart",
    "customXmlMoveFromRangeEnd",
    "customXmlMoveToRangeStart",
    "customXmlMoveToRangeEnd",
    "conflictIns",
    "conflictDel",
}


def revision_name(element) -> str | None:
    if not isinstance(element.tag, str):
        return None
    qname, name = etree.QName(element), local(element)
    if name in SUPPORTED | KNOWN_UNSUPPORTED or name.endswith("Change"):
        if qname.namespace in WORD_NAMESPACES or "word" in (qname.namespace or "").lower():
            return name
    return None


def inventory(parts: dict[str, bytes]) -> dict:
    records, unsupported = {}, []
    for part, value in sorted(parts.items()):
        if not part.startswith("word/") or not part.endswith(".xml"):
            continue
        root, counts = parse_xml(value, part), Counter()
        for element in root.iter():
            name = revision_name(element)
            if name:
                counts[name] += 1
                if name not in SUPPORTED or etree.QName(element).namespace not in WORD_NAMESPACES:
                    unsupported.append(
                        {"file": part, "element": root.getroottree().getpath(element), "revision": name}
                    )
            if local(element) in {"delText", "delInstrText"} and not any(
                local(p) in {"del", "moveFrom"} for p in element.iterancestors()
            ):
                unsupported.append(
                    {
                        "file": part,
                        "element": root.getroottree().getpath(element),
                        "revision": "orphan_deleted_text",
                    }
                )
        if counts:
            records[part] = dict(sorted(counts.items()))
    return {
        "parts": records,
        "total": sum(sum(c.values()) for c in records.values()),
        "unsupported": unsupported,
    }
