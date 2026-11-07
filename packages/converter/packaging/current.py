"""Source-verified ZIP contract for the revised two-mode pipeline.

Legacy strict Word/SEC packaging remains in engine.py and is never promoted here.
"""

import io
import json
import math
import re
import stat
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from zipfile import ZIP_STORED, BadZipFile, ZipFile

from lxml import html
from pydantic import Field

from converter.context import ProcessingContext
from converter.edgar_html import document_name
from converter.errors import fail
from converter.layout.models import Digest, Record
from converter.ooxml import sha256
from converter.packaging.archive import STAMP, _write_archive
from converter.packaging.models import PackagingPolicy
from converter.sec_validation.models import ValidationPolicy
from converter.sec_validation.profile import valid_filename
from converter.sec_validation.validator import digest, read_bounded, validate_files

METHOD = "source-verified-mode-zip-v1"
ASSET = re.compile(r"image[0-9]{3,}\.(jpg|jpeg|png|gif|svg|webp)\Z")
RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)


class Member(Record):
    filename: str
    sha256: Digest
    bytes: int = Field(gt=0)


class CurrentPackage(Record):
    method: Literal["source-verified-mode-zip-v1"] = METHOD
    validated: Literal[True] = True
    mode: Literal["standard", "edgar"]
    original_filename: str
    download_filename: str
    document_filename: str
    archive_filename: Literal["result.zip"] = "result.zip"
    sha256: Digest
    bytes: int = Field(gt=0)
    files: tuple[Member, ...]
    generation_sha256: Digest
    visual_sha256: Digest
    source_pdf_sha256: Digest
    sec_acceptance_confirmed: Literal[False] = False


def object_hash(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def reject(description):
    raise fail(
        "PACKAGE_VALIDATION_FAILED",
        "packaging_zip",
        description,
        "Regenerate the current conversion from unchanged source and verified output",
    )


def names(original, mode):
    if (
        mode not in {"standard", "edgar"}
        or not isinstance(original, str)
        or len(original.encode("utf-8")) > 240
        or original.startswith(".")
        or any(ord(c) < 32 or ord(c) == 127 or c in '/\\:<>"|?*' for c in original)
        or Path(original).suffix.lower() not in {".docx", ".pdf"}
        or not Path(original).stem.strip()
        or RESERVED.match(original)
    ):
        reject("Original upload filename or conversion mode is unsafe")
    stem = Path(original).stem
    document = stem + ".html" if mode == "standard" else document_name(original)
    return document, stem + ".zip"


def validate_payloads(payloads, mode, filename, context):
    """Inspect actual archived markup/resources, independently of archive manifest flags."""
    if (
        mode not in {"standard", "edgar"}
        or not filename.endswith(".htm" if mode == "edgar" else ".html")
        or Path(filename).name != filename
        or any(c in filename for c in "/\\:")
        or RESERVED.match(filename)
        or mode == "edgar"
        and not valid_filename(filename, (".htm",))
    ):
        reject("Archive document filename violates the selected mode")
    if filename not in payloads or len(payloads[filename]) > 32 * 1024 * 1024:
        reject("Document is missing or too large")
    assets = set(payloads) - {filename}
    if any(not ASSET.fullmatch(n) or mode == "edgar" and not n.endswith((".jpg", ".gif")) for n in assets):
        reject("Archive includes unsupported, nested or non-asset members")
    parsed = html.document_fromstring(payloads[filename], parser=html.HTMLParser(no_network=True))
    nodes = list(parsed.iter())
    if len(nodes) > 200000:
        reject("Document complexity exceeds the bounded profile")
    anchors = {
        value
        for node in nodes
        for key, value in node.attrib.items()
        if key == "id" or key == "name" and node.tag == "a"
    }
    referenced = set()

    def reference(value, link=False):
        if value.startswith("#"):
            if value[1:] not in anchors:
                reject("Document contains an unresolved internal reference")
        elif link and mode == "edgar" and value.startswith("https://www.sec.gov/Archives/edgar/data/"):
            pass  # Full URL grammar is checked by the manual-derived validator below.
        elif value in assets:
            referenced.add(value)
        else:
            reject("Document contains a broken, remote or embedded resource reference")

    for node in nodes:
        context.check()
        if not isinstance(node.tag, str):
            continue
        tag = node.tag.rsplit("}", 1)[-1].lower()
        if tag in {"script", "iframe", "object", "embed", "base", "link", "form", "foreignobject"}:
            reject("Active or external document content is prohibited")
        values = list(node.attrib.items())
        if tag == "style":
            values.append(("css", node.text or ""))
        for key, value in values:
            key = key.rsplit("}", 1)[-1].lower()
            if key.startswith("on"):
                reject("Event handlers are prohibited")
            if key in {"href", "xlink:href", "src"}:
                reference(value, tag == "a")
            if "@import" in value.lower():
                reject("External stylesheets are prohibited")
            for target in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)['\"]?\s*\)", value, re.I):
                reference(target)
    if referenced != assets:
        reject("ZIP contains unused assets or omits referenced assets")
    if mode == "edgar":
        with TemporaryDirectory(prefix="convx-edgar-zip-") as temp:
            root = Path(temp)
            for name, data in payloads.items():
                (root / name).write_bytes(data)
            result = validate_files(
                root / filename,
                tuple(root / n for n in sorted(assets)),
                policy=ValidationPolicy(
                    html_profile="edgar_layers_v1"
                    if parsed.xpath('/html/head/meta[@name="convx-edgar-profile"]/@content')
                    == ["edgar_layers_v1"]
                    else "edgar_flow_v1"
                ),
                context=context,
            )
            if not result.passed:
                reject("Actual archived HTM or graphics fail the local EDGAR profile")


def audit_bytes(data, mode, filename, expected, context=None, policy=None):
    """Read every CRC; validate canonical headers and exact root payloads, never extractall."""
    context, policy = context or ProcessingContext(), policy or PackagingPolicy()
    if (
        len(data) > policy.max_archive_bytes
        or len(data) < 22
        or data[:4] != b"PK\x03\x04"
        or data[-22:-18] != b"PK\x05\x06"
    ):
        reject("Archive envelope or byte budget is invalid")
    try:
        _, disk, cd_disk, disk_count, count, cd_size, cd_offset, comment = struct.unpack(
            "<4s4H2LH", data[-22:]
        )
        if disk or cd_disk or disk_count != count or comment or cd_offset + cd_size != len(data) - 22:
            reject("Archive contains split, appended or hidden metadata")
        with ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            ordered = [i.filename for i in infos]
            if (
                not infos
                or len(infos) > policy.max_members
                or count != len(infos)
                or ordered != [filename, *sorted(n for n in ordered if n != filename)]
                or len(set(n.casefold() for n in ordered)) != len(ordered)
            ):
                reject("Archive order, member count or unique root filenames are invalid")
            if set(ordered) != set(expected):
                reject("Archive members differ from verified output")
            payloads, total, offset = {}, 0, 0
            for info in infos:
                context.check()
                name = info.filename
                if (
                    "/" in name
                    or "\\" in name
                    or ":" in name
                    or name in {".", ".."}
                    or info.is_dir()
                    or info.flag_bits not in {0, 0x800}
                    or info.compress_type != ZIP_STORED
                    or info.date_time != STAMP
                    or info.extra
                    or info.comment
                    or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG
                    or info.header_offset != offset
                    or info.file_size > policy.max_member_bytes
                    or info.file_size != info.compress_size
                ):
                    reject("Archive has unsafe member paths, metadata or compression")
                encoded = name.encode("utf-8" if info.flag_bits & 0x800 else "ascii")
                fields = struct.unpack("<4s5H3L2H", data[offset : offset + 30])
                if (
                    fields[0] != b"PK\x03\x04"
                    or fields[2] != info.flag_bits
                    or fields[3] != ZIP_STORED
                    or fields[4] != 0
                    or fields[5] != 33
                    or fields[6] != info.CRC
                    or fields[7] != info.compress_size
                    or fields[8] != info.file_size
                    or fields[-1] != 0
                    or fields[-2] != len(encoded)
                    or data[offset + 30 : offset + 30 + len(encoded)] != encoded
                ):
                    reject("Local archive header disagrees with its directory")
                offset += 30 + len(encoded) + info.compress_size
                total += info.file_size
                if total > policy.max_uncompressed_bytes:
                    reject("Archive uncompressed byte budget exceeded")
                payload = archive.read(info)
                if (digest(payload), len(payload)) != (expected[name]["sha256"], expected[name]["bytes"]):
                    reject("Archived document or asset bytes changed")
                payloads[name] = payload
            if offset != cd_offset:
                reject("Unaccounted data precedes the central directory")
        validate_payloads(payloads, mode, filename, context)
        return payloads
    except (BadZipFile, ValueError, OSError, UnicodeError, struct.error) as exc:
        raise fail(
            "PACKAGE_VALIDATION_FAILED",
            "packaging_zip",
            "ZIP bytes or member CRC are invalid",
            "Regenerate the archive",
        ) from exc


def verified_payloads(pdf, directory, mode, generation, visual, context):
    expected_methods = (
        {"efm78-flow-css2-v1", "efm78-layered-css2-v1"}
        if mode == "edgar"
        else {"verified-layout-native-svg-html5-v1"}
    )
    if (
        generation.get("method") not in expected_methods
        or generation.get("generated") is not True
        or generation.get("source_pdf_sha256") != sha256(pdf)
        or visual.get("method")
        != ("chromium-edgar-flow-screen-print-v1" if mode == "edgar" else "chromium-standard-screen-print-v1")
        or any(
            visual.get(k) is not True for k in ["checks_complete", "text_verified", "page_geometry_verified"]
        )
        or visual.get("source_pdf_sha256") != generation["source_pdf_sha256"]
        or visual.get("html_sha256") != generation["sha256"]
        or visual.get("network_requests_denied") != 0
        or not generation.get("pages")
        or len(visual.get("pages", [])) != len(generation["pages"])
    ):
        reject("Current authoritative HTML and actual browser evidence are required")
    for i, (measured, page) in enumerate(zip(visual["pages"], generation["pages"], strict=True), 1):
        if measured.get("page") != i or page.get("page") != i:
            reject("Browser evidence page coverage is incomplete")
        for medium in ["screen", "print"]:
            metrics = measured.get(medium, {})
            if metrics.get("dimensions_match") is not True or any(
                type(metrics.get(k)) not in {int, float} or not math.isfinite(metrics[k]) or metrics[k] < 0
                for k in ["mean_absolute_channel_error", "max_channel_error", "changed_pixels"]
            ):
                reject("Browser comparison measurements are incomplete")
        if mode == "edgar" and (
            measured.get("word_geometry", {}).get("missing_words") != 0
            or measured.get("word_geometry", {}).get("max_origin_error_pt", math.inf) > 6
        ):
            reject("EDGAR printed content or position validation failed")
    if generation.get("method") == "efm78-layered-css2-v1":
        import pymupdf

        from converter.edgar_reflow import vertical_plan
        from converter.sec_validation.layer_profile import layer_profile_digest

        if (
            generation.get("sec_validation", {}).get("html_profile") != "edgar_layers_v1"
            or generation["sec_validation"].get("formatting_profile_sha256") != layer_profile_digest()
        ):
            reject("Changed EDGAR layered formatting profile")
        with pymupdf.open(pdf) as source:
            plans = {str(i + 1): vertical_plan(page)["words"] for i, page in enumerate(source)}
        if plans != generation.get("reflow_targets"):
            reject("EDGAR reflow differs from independent source plan")
        from converter.edgar_words import word_geometry

        printed = directory.parent / "edgar-visual/rendered.pdf"
        if sha256(printed) != visual.get("artifact_sha256", {}).get("rendered.pdf"):
            reject("Changed actual EDGAR browser print")
        with pymupdf.open(pdf) as original, pymupdf.open(printed) as output_pdf:
            if len(original) != len(output_pdf):
                reject("Changed browser print page coverage")
            for i, (source_page, printed_page) in enumerate(zip(original, output_pdf, strict=True)):
                measured = word_geometry(source_page, printed_page, True, plans[str(i + 1)])
                if (
                    measured != visual["pages"][i]["word_geometry"]
                    or measured["missing_words"]
                    or measured["max_origin_error_pt"] > 6
                ):
                    reject("Actual browser print loses or displaces source disclosure")
    name = generation["filename"]
    if (
        name != "document.html"
        and mode == "standard"
        or mode == "edgar"
        and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,27}\.htm", name)
    ):
        reject("Generated document filename is unsafe")
    assets = generation.get("assets", {})
    if len(assets) > 1000 or any(not ASSET.fullmatch(n) for n in assets):
        reject("Generated asset manifest is unsafe")
    if directory.is_symlink() or set(p.name for p in directory.iterdir()) != {name, *assets}:
        reject("Generated output root contains undeclared files or directories")
    payloads, total = {}, 0
    for n in [name, *sorted(assets)]:
        context.check()
        data = read_bounded(directory / n, 32 * 1024 * 1024)
        expected = generation["sha256"] if n == name else assets[n]["sha256"]
        if digest(data) != expected:
            reject("Generated HTML or assets changed after browser validation")
        total += len(data)
        if total > 100 * 1024 * 1024:
            reject("Combined output byte budget exceeded")
        payloads[n] = data
    return payloads


def package_current(pdf, directory, generation, visual, original, mode, output, context):
    filename, download = names(original, mode)
    payloads = verified_payloads(pdf, directory, mode, generation, visual, context)
    # Only the ZIP entry name changes. Document bytes, fragments and local asset
    # references remain untouched and are checked again under the final name.
    renamed = {filename: payloads.pop(generation["filename"]), **payloads}
    validate_payloads(renamed, mode, filename, context)
    expected = {n: {"sha256": digest(data), "bytes": len(data)} for n, data in renamed.items()}
    output.mkdir(mode=0o700, exist_ok=False)
    archive = output / "result.zip"
    _write_archive(archive, renamed, PackagingPolicy(), context)
    data = read_bounded(archive, 128 * 1024 * 1024)
    audit_bytes(data, mode, filename, expected, context)
    return CurrentPackage(
        mode=mode,
        original_filename=original,
        download_filename=download,
        document_filename=filename,
        sha256=digest(data),
        bytes=len(data),
        files=tuple(Member(filename=n, **record) for n, record in expected.items()),
        generation_sha256=object_hash(generation),
        visual_sha256=object_hash(visual),
        source_pdf_sha256=generation["source_pdf_sha256"],
    ).model_dump(mode="json")
