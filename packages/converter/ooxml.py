from __future__ import annotations

import hashlib
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

from lxml import etree

from converter.context import ProcessingContext
from converter.errors import ConversionFailure, fail

WORD_NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
REL_NAMESPACES = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "http://purl.oclc.org/ooxml/officeDocument/relationships",
}


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def local(element) -> str:
    return etree.QName(element).localname if element is not None and isinstance(element.tag, str) else ""


def word(element, name: str) -> bool:
    return (
        element is not None
        and isinstance(element.tag, str)
        and etree.QName(element).namespace in WORD_NAMESPACES
        and local(element) == name
    )


def parse_xml(payload: bytes, part: str):
    try:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
        root = etree.fromstring(payload, parser)
        if root.getroottree().docinfo.doctype:
            raise ValueError("DTD")
        return root
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise fail(
            "UNSAFE_OR_INVALID_XML",
            "revisions",
            "Package XML cannot be safely parsed",
            "Repair the document using a trusted editor",
            file=part,
        ) from exc


@dataclass(frozen=True)
class PackageLimits:
    max_entries: int = 2048
    max_entry_bytes: int = 16 * 1024 * 1024
    max_expanded_bytes: int = 128 * 1024 * 1024
    max_ratio: int = 200


def read_package(
    path: Path, context: ProcessingContext | None = None, limits: PackageLimits | None = None
) -> dict[str, bytes]:
    context, limits = context or ProcessingContext(), limits or PackageLimits()
    parts, seen, total = {}, set(), 0
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > limits.max_entries:
                raise ValueError("entry limit")
            for entry in entries:
                context.check()
                name = entry.filename
                if (
                    name.startswith("/")
                    or "\\" in name
                    or ":" in name
                    or ".." in PurePosixPath(name).parts
                    or name.casefold() in seen
                    or stat.S_ISLNK(entry.external_attr >> 16)
                    or entry.flag_bits & 1
                    or entry.compress_type not in {ZIP_STORED, ZIP_DEFLATED}
                ):
                    raise ValueError("unsafe ZIP")
                seen.add(name.casefold())
                total += entry.file_size
                if (
                    entry.file_size > limits.max_entry_bytes
                    or total > limits.max_expanded_bytes
                    or entry.file_size / max(entry.compress_size, 1) > limits.max_ratio
                ):
                    raise ValueError("expansion limit")
                if entry.is_dir():
                    continue
                with archive.open(entry) as stream:
                    value = stream.read(limits.max_entry_bytes + 1)
                if len(value) != entry.file_size or len(value) > limits.max_entry_bytes:
                    raise ValueError("size mismatch")
                parts[name] = value
        if not {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}.issubset(parts):
            raise ValueError("missing main parts")
        for name, value in parts.items():
            if name.lower().endswith((".xml", ".rels")):
                parse_xml(value, name)
        return parts
    except ConversionFailure:
        raise
    except (BadZipFile, ValueError, KeyError, RuntimeError) as exc:
        raise fail(
            "INVALID_DOCX_PACKAGE",
            "revisions",
            "DOCX package is unsafe or invalid",
            "Provide a valid nonencrypted DOCX within configured limits",
        ) from exc


def visible_text(root) -> str:
    pieces = []
    for element in root.iter():
        if any(word(element, name) for name in ("t", "instrText")):
            pieces.append(element.text or "")
        elif word(element, "tab"):
            pieces.append("\t")
        elif any(word(element, name) for name in ("br", "cr")):
            pieces.append("\n")
        elif (
            isinstance(element.tag, str)
            and etree.QName(element).namespace == "http://schemas.openxmlformats.org/drawingml/2006/main"
            and local(element) == "t"
        ):
            pieces.append(element.text or "")
    return "".join(pieces)
