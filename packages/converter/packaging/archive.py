from __future__ import annotations

import io
import os
import stat
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_STORED, BadZipFile, ZipFile, ZipInfo

from converter.context import ProcessingContext
from converter.errors import fail
from converter.packaging.models import ArchiveAudit, PackagingPolicy
from converter.sec_validation.models import FileEvidence
from converter.sec_validation.profile import valid_filename
from converter.sec_validation.validator import digest, read_bounded, validate_files
from converter.visual_validation.engine import object_hash

STAMP = (1980, 1, 1, 0, 0, 0)


def _reject(code, description):
    raise fail(
        code,
        "packaging_zip",
        description,
        "Regenerate the clean archive from current validated HTM and its exact referenced images",
    )


def _members(htm, assets, policy, context):
    paths = (Path(htm), *sorted(map(Path, assets), key=lambda p: p.name))
    if len(paths) > policy.max_members:
        _reject("PACKAGE_MEMBER_LIMIT", "Archive member-count budget exceeded")
    names = [p.name for p in paths]
    if len(set(n.casefold() for n in names)) != len(names):
        _reject("PACKAGE_NAME_COLLISION", "Archive names collide under case-insensitive resolution")
    if not valid_filename(paths[0].name, (".htm",)) or any(
        not valid_filename(p.name, (".jpg", ".gif")) for p in paths[1:]
    ):
        _reject("PACKAGE_MEMBER_NAME_INVALID", "Members must be one compliant HTM and root JPG/GIF names")
    root = paths[0].parent.resolve()
    if paths[0].parent.is_symlink() or any(p.is_symlink() or p.parent.resolve() != root for p in paths):
        _reject("PACKAGE_PATH_INVALID", "All members must be regular files in the same owned root")
    if set(p.name for p in root.iterdir()) != set(names):
        _reject("PACKAGE_INPUT_NOT_CLEAN", "Filing root contains an undeclared file or directory")
    payloads = {}
    total = 0
    for path in paths:
        context.check()
        try:
            data = read_bounded(path, policy.max_member_bytes)
        except (OSError, ValueError) as exc:
            raise fail(
                "PACKAGE_MEMBER_UNAVAILABLE",
                "packaging_zip",
                "A member is linked, unreadable or exceeds its budget",
                "Revalidate a bounded immutable filing root",
            ) from exc
        total += len(data)
        if total > policy.max_uncompressed_bytes:
            _reject("PACKAGE_TOTAL_BYTE_LIMIT", "Uncompressed artifact budget exceeded")
        payloads[path.name] = data
    return payloads


def _write_archive(path, payloads, policy, context):
    """Pure archive mechanics; this helper cannot make an application job downloadable."""
    created = False
    try:
        with path.open("xb") as stream:
            created = True
            os.chmod(path, 0o600)
            with ZipFile(stream, "w", compression=ZIP_STORED, allowZip64=False) as archive:
                for name, data in payloads.items():
                    context.check()
                    entry = ZipInfo(name, date_time=STAMP)
                    entry.create_system = 3
                    entry.external_attr = 0o100600 << 16
                    entry.compress_type = ZIP_STORED
                    archive.writestr(entry, data)
                    if stream.tell() > policy.max_archive_bytes:
                        _reject("PACKAGE_ARCHIVE_BYTE_LIMIT", "Archive byte budget exceeded")
            stream.flush()
            os.fsync(stream.fileno())
        if path.stat().st_size > policy.max_archive_bytes:
            _reject("PACKAGE_ARCHIVE_BYTE_LIMIT", "Archive including its directory exceeds the byte budget")
    except BaseException:
        if created:
            path.unlink(missing_ok=True)
        raise


def audit_archive_bytes(
    data, expected_files=None, submission=None, sec_policy=None, policy=None, context=None
):
    """Reopen, read every CRC and validate actual member bytes without extractall."""
    policy, context = policy or PackagingPolicy(), context or ProcessingContext()
    context.check()
    if len(data) > policy.max_archive_bytes:
        _reject("PACKAGE_ARCHIVE_BYTE_LIMIT", "Archive byte budget exceeded")
    if len(data) < 22 or data[:4] != b"PK\x03\x04" or data[-22:-18] != b"PK\x05\x06":
        _reject("PACKAGE_ENVELOPE_INVALID", "Archive has a leading/trailing payload or invalid envelope")
    try:
        _, disk, cd_disk, disk_count, count, cd_size, cd_offset, comment = struct.unpack(
            "<4s4H2LH", data[-22:]
        )
        if disk or cd_disk or disk_count != count or comment or cd_offset + cd_size != len(data) - 22:
            _reject("PACKAGE_ENVELOPE_INVALID", "Archive has unsupported split/comment/directory metadata")
        with ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > policy.max_members or len(infos) != count:
                _reject("PACKAGE_MEMBER_LIMIT", "Archive member count is invalid")
            names = [i.filename for i in infos]
            if len(set(n.casefold() for n in names)) != len(names):
                _reject("PACKAGE_NAME_COLLISION", "Duplicate or case-colliding archive members")
            htms = [n for n in names if n.lower().endswith(".htm")]
            if (
                len(htms) != 1
                or not valid_filename(htms[0], (".htm",))
                or any(not valid_filename(n, (".htm", ".jpg", ".gif")) for n in names)
            ):
                _reject(
                    "PACKAGE_CONTENTS_INVALID",
                    "ZIP must contain exactly one compliant root HTM and JPG/GIF images",
                )
            if names != [htms[0], *sorted(n for n in names if n != htms[0])]:
                _reject("PACKAGE_ORDER_INVALID", "Archive order is not deterministic HTM-first order")
            payloads = {}
            total = 0
            offset = 0
            for info in infos:
                context.check()
                if (
                    info.is_dir()
                    or info.flag_bits
                    or info.compress_type != ZIP_STORED
                    or info.date_time != STAMP
                    or info.extra
                    or info.comment
                    or stat.S_IFMT(info.external_attr >> 16) not in {0, stat.S_IFREG}
                ):
                    _reject(
                        "PACKAGE_METADATA_INVALID",
                        "Archive contains unsupported encrypted, linked, directory or noncanonical members",
                    )
                if (
                    info.header_offset != offset
                    or info.file_size > policy.max_member_bytes
                    or info.compress_size != info.file_size
                ):
                    _reject(
                        "PACKAGE_MEMBER_SIZE_INVALID",
                        "Member size/offset/compression is outside the bounded profile",
                    )
                # Local header must also be canonical: no hidden local extras, names or payloads.
                fields = struct.unpack("<4s5H3L2H", data[offset : offset + 30])
                if (
                    fields[0] != b"PK\x03\x04"
                    or fields[2] != 0
                    or fields[3] != ZIP_STORED
                    or fields[4] != 0
                    or fields[5] != 33
                    or fields[6] != info.CRC
                    or fields[7] != info.compress_size
                    or fields[8] != info.file_size
                    or fields[-1] != 0
                    or fields[-2] != len(info.filename.encode("ascii"))
                ):
                    _reject(
                        "PACKAGE_LOCAL_HEADER_INVALID",
                        "Local member header differs from the canonical directory",
                    )
                offset += 30 + fields[-2] + info.compress_size
                total += info.file_size
                if total > policy.max_uncompressed_bytes:
                    _reject("PACKAGE_TOTAL_BYTE_LIMIT", "Uncompressed archive budget exceeded")
                payloads[info.filename] = archive.read(
                    info
                )  # verifies local name and CRC, no filesystem extraction
            if offset != cd_offset:
                _reject(
                    "PACKAGE_LOCAL_HEADER_INVALID", "Unaccounted local payload precedes the central directory"
                )
    except (BadZipFile, OSError, ValueError, UnicodeError, struct.error) as exc:
        raise fail(
            "PACKAGE_CORRUPT",
            "packaging_zip",
            "Archive headers or CRC-checked payloads are invalid",
            "Regenerate from immutable validated artifacts",
        ) from exc
    expected = (
        tuple(
            FileEvidence.model_validate(f.model_dump() if isinstance(f, FileEvidence) else f)
            for f in expected_files
        )
        if expected_files is not None
        else None
    )
    if expected is not None and (
        {f.filename: (f.sha256, f.bytes) for f in expected}
        != {n: (digest(v), len(v)) for n, v in payloads.items()}
    ):
        _reject("PACKAGE_PAYLOAD_CHANGED", "Actual ZIP bytes do not match the validated manifest")
    with TemporaryDirectory(prefix="convx-audit-") as directory:
        root = Path(directory)
        os.chmod(root, 0o700)
        for name, payload in payloads.items():
            path = root / name
            with path.open("xb") as stream:
                os.chmod(path, 0o600)
                stream.write(payload)
        result = validate_files(
            root / htms[0], tuple(root / n for n in names if n != htms[0]), submission, sec_policy, context
        )
        if not result.strict_passed:
            _reject(
                "PACKAGE_SEC_VALIDATION_FAILED",
                "Actual archived HTM/assets do not pass strict local validation",
            )
    return ArchiveAudit(
        sha256=digest(data),
        bytes=len(data),
        htm_filename=htms[0],
        files=result.files,
        sec_gate_sha256=object_hash(result.model_dump(mode="json")),
    )
