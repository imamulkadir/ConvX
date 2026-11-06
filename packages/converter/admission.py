"""Bounded package admission. Does not interpret or accept Word revisions."""

from __future__ import annotations

import re
import stat
import time
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

from lxml import etree

from converter.runtime_config import AdmissionError, Limits

CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WORD_NS = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def invalid(code: str = "INVALID_DOCX") -> AdmissionError:
    return AdmissionError(422, code, "Document package is invalid or contains unsupported unsafe content")


def validate_docx(path: Path, settings: Limits) -> None:
    if path.is_symlink() or not path.is_file():
        raise invalid("UNSAFE_SOURCE")
    if path.stat().st_size > settings.max_upload_bytes:
        raise AdmissionError(413, "FILE_TOO_LARGE", "Document exceeds the configured upload limit")
    deadline = time.monotonic() + settings.validation_timeout_seconds

    def check_deadline():
        if time.monotonic() > deadline:
            raise invalid("VALIDATION_TIMEOUT")

    try:
        with path.open("rb") as source:
            if source.read(4) != b"PK\x03\x04":
                raise invalid()
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if not entries or len(entries) > settings.max_zip_entries:
                raise invalid("ZIP_LIMIT_EXCEEDED")
            names, total = set(), 0
            for entry in entries:
                check_deadline()
                name = entry.filename
                parts = PurePosixPath(name).parts
                if (
                    not parts
                    or name.startswith("/")
                    or "\\" in name
                    or ":" in name
                    or any(p in ("..", ".") for p in parts)
                    or "\x00" in name
                    or name.casefold() in names
                    or stat.S_ISLNK(entry.external_attr >> 16)
                ):
                    raise invalid("UNSAFE_ZIP_PATH")
                names.add(name.casefold())
                if entry.flag_bits & 1 or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
                    raise invalid("UNSUPPORTED_ZIP_ENCODING")
                total += entry.file_size
                if (
                    entry.file_size > settings.max_entry_bytes
                    or total > settings.max_expanded_bytes
                    or entry.file_size / max(entry.compress_size, 1) > settings.max_compression_ratio
                ):
                    raise invalid("ZIP_LIMIT_EXCEEDED")
                if any(
                    term in name.casefold()
                    for term in ("vbaproject", "vbasignature", "activex/", "embeddings/")
                ):
                    raise invalid("ACTIVE_CONTENT")
            expected = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
            if not expected.issubset(archive.namelist()):
                raise invalid()
            roots = {}
            for entry in entries:
                check_deadline()
                if entry.is_dir():
                    continue
                # Read through ZipExtFile to enforce actual expansion bounds and CRC checks.
                payload = bytearray()
                with archive.open(entry) as stream:
                    while chunk := stream.read(64 * 1024):
                        check_deadline()
                        payload.extend(chunk)
                        if len(payload) > settings.max_entry_bytes or len(payload) > entry.file_size:
                            raise invalid("ZIP_LIMIT_EXCEEDED")
                if len(payload) != entry.file_size:
                    raise invalid()
                if not entry.filename.lower().endswith((".xml", ".rels")):
                    continue
                parser = etree.XMLParser(
                    resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
                )
                root = etree.fromstring(bytes(payload), parser)
                if root.getroottree().docinfo.doctype:
                    raise invalid("UNSAFE_XML")
                depth = 0
                for event, _element in etree.iterwalk(root, events=("start", "end")):
                    if event == "start":
                        depth += 1
                        if depth > settings.max_xml_depth:
                            raise invalid("XML_LIMIT_EXCEEDED")
                    else:
                        depth -= 1
                # Field instructions may be split across runs, so inspect their combined text.
                instructions = "".join(root.xpath("//*[local-name()='instrText']/text()"))
                instructions += " " + " ".join(
                    root.xpath("//*[local-name()='fldSimple']/@*[local-name()='instr']")
                )
                if re.search(
                    r"\b(DDEAUTO|DDE|INCLUDETEXT|INCLUDEPICTURE|DATABASE|LINK)\b", instructions, re.I
                ):
                    raise invalid("ACTIVE_FIELD")
                if root.xpath("//*[local-name()='altChunk']"):
                    raise invalid("UNSUPPORTED_EMBEDDED_CONTENT")
                if entry.filename.endswith(".rels"):
                    if root.tag != f"{{{REL_NS}}}Relationships":
                        raise invalid()
                    ids = set()
                    for rel in root:
                        if (
                            rel.tag != f"{{{REL_NS}}}Relationship"
                            or not rel.get("Id")
                            or rel.get("Id") in ids
                        ):
                            raise invalid()
                        ids.add(rel.get("Id"))
                        target = rel.get("Target", "")
                        if rel.get("Type", "").rsplit("/", 1)[-1].lower() in {
                            "oleobject",
                            "package",
                            "control",
                            "vbaproject",
                        }:
                            raise invalid("ACTIVE_CONTENT")
                        if rel.get("TargetMode") == "External":
                            # Inert source hyperlinks remain disclosure data and are never fetched.
                            # External templates, images, OLE and all other relationships are rejected.
                            if not rel.get("Type", "").endswith("/hyperlink") or urlsplit(
                                target
                            ).scheme.lower() not in {"https", "http", "mailto"}:
                                raise invalid("EXTERNAL_RELATIONSHIP")
                        else:
                            decoded = unquote(target).split("#", 1)[0]
                            if "\\" in decoded or ":" in decoded or decoded.startswith("//"):
                                raise invalid("UNSAFE_RELATIONSHIP")
                            # Resolve package-relative internal references without filesystem access.
                            base = (
                                []
                                if entry.filename == "_rels/.rels"
                                else list(PurePosixPath(entry.filename).parent.parent.parts)
                            )
                            if decoded.startswith("/"):
                                base = []
                            for component in decoded.split("/"):
                                if component in ("", "."):
                                    continue
                                if component == "..":
                                    if not base:
                                        raise invalid("UNSAFE_RELATIONSHIP")
                                    base.pop()
                                else:
                                    base.append(component)
                            if decoded and "/".join(base) not in archive.namelist():
                                raise invalid("MISSING_PACKAGE_PART")
                if entry.filename in expected:
                    roots[entry.filename] = root
            content = roots["[Content_Types].xml"]
            if content.tag != f"{{{CONTENT_NS}}}Types":
                raise invalid()
            for child in content:
                value = child.get("ContentType", "").lower()
                # Word can retain a dormant MIME declaration after removing an OLE object.
                used = (
                    child.get("PartName", "").lstrip("/") in archive.namelist()
                    if child.get("PartName")
                    else any(
                        n.lower().endswith("." + child.get("Extension", "").lower())
                        for n in archive.namelist()
                    )
                )
                if used and any(x in value for x in ("macroenabled", "vbaproject", "oleobject", "activex")):
                    raise invalid("ACTIVE_CONTENT")
            if not any(
                c.get("PartName") == "/word/document.xml" and c.get("ContentType") == DOCX_TYPE
                for c in content
            ):
                raise invalid()
            document = roots["word/document.xml"]
            if (
                etree.QName(document).namespace not in WORD_NS
                or etree.QName(document).localname != "document"
            ):
                raise invalid()
            main_links = [r for r in roots["_rels/.rels"] if r.get("Type", "").endswith("/officeDocument")]
            if len(main_links) != 1 or main_links[0].get("Target", "").lstrip("/") != "word/document.xml":
                raise invalid()
    except AdmissionError:
        raise
    except (BadZipFile, etree.XMLSyntaxError, ValueError, KeyError, NotImplementedError, RuntimeError) as exc:
        raise invalid() from exc
