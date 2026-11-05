from __future__ import annotations

import hashlib
import re
from pathlib import Path

from lxml import html

from converter.assets.normalize import publish
from converter.context import ProcessingContext
from converter.errors import fail
from converter.packaging.models import PackageNames
from converter.sec_validation.profile import valid_filename
from converter.sec_validation.validator import read_bounded


def package_names(original_filename):
    if (
        not isinstance(original_filename, str)
        or not original_filename.lower().endswith(".docx")
        or len(original_filename) <= 5
        or len(original_filename.encode("utf-8")) > 240
        or original_filename.startswith(".")
        or any(ord(c) < 32 or ord(c) == 127 or c in '/\\:<>"|?*' for c in original_filename)
    ):
        raise fail(
            "PACKAGE_SOURCE_NAME_INVALID",
            "packaging_zip",
            "Source name must be a safe DOCX basename",
            "Use the original admitted upload filename",
        )
    stem = original_filename[:-5]
    proposed = stem.lower() + ".htm"
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *[f"com{i}" for i in range(1, 10)],
        *[f"lpt{i}" for i in range(1, 10)],
    }
    if not valid_filename(proposed, (".htm",)) or stem.split(".")[0].lower() in reserved:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "document"
        if not slug[0].isalnum() or slug.split(".")[0].lower() in reserved:
            slug = "document_" + slug
        suffix = hashlib.sha256(original_filename.encode("utf-8")).hexdigest()[:12]
        proposed = slug[:15].lower() + "-" + suffix + ".htm"
    return PackageNames(
        original_filename=original_filename, download_filename=stem + ".zip", htm_filename=proposed
    )


def prepare_filing_name(
    htm: Path, original_filename, context: ProcessingContext | None = None, max_bytes=25 * 1024 * 1024
):
    """Finalize naming before compliance/visual gates. Never rename qualified bytes afterward."""
    context = context or ProcessingContext()
    context.check()
    names = package_names(original_filename)
    raw = read_bounded(htm, max_bytes)
    target = htm.with_name(names.htm_filename)
    if target == htm:
        return target, names
    if target.exists() or target.is_symlink():
        raise fail(
            "PACKAGE_NAME_COLLISION",
            "generating_htm",
            "Prepared HTM target already exists",
            "Use a new attempt-local filing directory",
        )
    tree = html.document_fromstring(raw)
    before = "".join(tree.find("body").itertext())
    pattern = rb'(<a\b[^>]*\bhref=")' + re.escape(htm.name.encode("ascii")) + rb'(?=[#"])'
    updated = re.sub(pattern, lambda match: match[1] + names.htm_filename.encode("ascii"), raw)
    after = html.document_fromstring(updated)
    if "".join(after.find("body").itertext()) != before or any(
        (a.get("href") or "").split("#")[0] == htm.name for a in after.findall(".//a")
    ):
        raise fail(
            "PACKAGE_RENAME_REFERENCE_UNSUPPORTED",
            "generating_htm",
            "HTM naming could not preserve self-reference semantics",
            "Resolve reference syntax before validation; do not change disclosure",
        )
    context.check()
    publish(target, updated)
    htm.unlink()
    return target, names
