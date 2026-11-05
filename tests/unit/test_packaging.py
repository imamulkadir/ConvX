import io
import struct
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.packaging.archive import STAMP, _members, _write_archive, audit_archive_bytes
from converter.packaging.engine import completion_ready
from converter.packaging.models import PackagingPolicy
from converter.packaging.naming import package_names, prepare_filing_name
from converter.sec_validation.models import SubmissionContext
from converter.sec_validation.validator import validate_files
from PIL import Image


@pytest.fixture
def filing(tmp_path):
    root = tmp_path / "filing"
    root.mkdir()
    htm = root / "filing.htm"
    htm.write_bytes(b'<html><body><p>Selectable disclosure &pound;</p><img src="image001.jpg"></body></html>')
    image = root / "image001.jpg"
    Image.new("RGB", (8, 6), (20, 80, 150)).save(image, format="JPEG")
    submission = SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
    return htm, (image,), submission


def write_zip(tmp_path, payloads):
    path = tmp_path / "mechanics.zip"
    _write_archive(path, payloads, PackagingPolicy(), ProcessingContext())
    return path.read_bytes()


def test_real_archive_mechanics_deterministic_and_independently_validated(filing, tmp_path):
    htm, assets, submission = filing
    context = ProcessingContext()
    policy = PackagingPolicy()
    payloads = _members(htm, assets, policy, context)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    _write_archive(first, payloads, policy, context)
    _write_archive(second, payloads, policy, context)
    assert first.read_bytes() == second.read_bytes()
    sec = validate_files(htm, assets, submission)
    result = audit_archive_bytes(first.read_bytes(), sec.files, submission)
    assert result.passed and not result.conversion_eligible  # archive mechanics, not a DOCX qualification
    with ZipFile(first) as archive:
        assert archive.namelist() == ["filing.htm", "image001.jpg"]
        assert all(
            i.date_time == STAMP and i.compress_type == ZIP_STORED and not i.extra for i in archive.infolist()
        )
        assert archive.testzip() is None and archive.read("filing.htm") == htm.read_bytes()


@pytest.mark.parametrize(
    "name",
    [
        "Report.docx",
        "a" * 60 + ".docx",
        "Report with spaces.docx",
        "\u03a3\u03bf\u03c5.docx",
        "CON.docx",
        "-leading.docx",
        "06749LWD4_prelim_prospectus_automated.docx",
    ],
)
def test_original_zip_name_and_compliant_deterministic_htm(name):
    plan = package_names(name)
    assert plan.download_filename == name[:-5] + ".zip"
    assert len(plan.htm_filename) <= 32 and plan.htm_filename.isascii() and plan.htm_filename[0].isalnum()
    assert plan == package_names(name) and plan.htm_filename == plan.htm_filename.lower()
    assert package_names("Report.docx").htm_filename == "report.htm"


@pytest.mark.parametrize(
    "name", ["../file.docx", "a\\b.docx", "file.docx\n", "file.pdf", ".hidden.docx", "a:stream.docx", ""]
)
def test_rejected_source_names(name):
    with pytest.raises(ConversionFailure):
        package_names(name)


def test_prepare_name_and_self_link_before_validation(tmp_path):
    path = tmp_path / "candidate.htm"
    path.write_bytes(
        b'<html><body><a name="note"></a><a href="candidate.htm#note">candidate.htm</a></body></html>'
    )
    prepared, names = prepare_filing_name(path, "Report.docx")
    assert prepared.name == names.htm_filename == "report.htm" and not path.exists()
    assert (
        b'href="report.htm#note"' in prepared.read_bytes() and b">candidate.htm</a>" in prepared.read_bytes()
    )
    sec = validate_files(
        prepared, submission=SubmissionContext(form_type="S-1", encoded_submission_bytes=1000)
    )
    assert sec.strict_passed


def test_existing_outputs_are_never_overwritten(filing, tmp_path):
    htm, _, _ = filing
    candidate = htm.parent / "candidate.htm"
    candidate.write_bytes(b"<p>Keep source</p>")
    with pytest.raises(ConversionFailure):
        prepare_filing_name(candidate, "filing.docx")
    assert candidate.read_bytes() == b"<p>Keep source</p>"
    path = tmp_path / "existing.zip"
    path.write_bytes(b"keep existing")
    with pytest.raises(FileExistsError):
        _write_archive(path, {"filing.htm": b"x"}, PackagingPolicy(), ProcessingContext())
    assert path.read_bytes() == b"keep existing"


@pytest.mark.parametrize(
    "extra",
    ["diagnostic.json", "original.pdf", "accepted.docx", "style.css", "script.js", "unused.jpg", "nested"],
)
def test_filing_root_must_be_exact(filing, extra):
    htm, assets, _ = filing
    if extra == "nested":
        (htm.parent / extra).mkdir()
    else:
        (htm.parent / extra).write_bytes(b"not included")
    with pytest.raises(ConversionFailure, match="PACKAGE_INPUT_NOT_CLEAN"):
        _members(htm, assets, PackagingPolicy(), ProcessingContext())


def malformed_zip(payloads, change=None):
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        for name, data in payloads:
            info = ZipInfo(name, STAMP)
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            if change == "symlink":
                info.external_attr = 0o120777 << 16
            if change == "extra":
                info.extra = b"\x00\x00\x00\x00"
            archive.writestr(info, data)
    return stream.getvalue()


@pytest.mark.parametrize(
    "names",
    [
        ["../filing.htm"],
        ["nested/filing.htm"],
        ["filing.htm", "other.htm"],
        ["filing.htm", "report.json"],
        ["filing.htm", "source.pdf"],
        ["filing.htm", "script.js"],
        ["filing.htm", "bad.svg"],
        ["filing.htm", "image.JPG", "IMAGE.jpg"],
    ],
)
def test_unacceptable_archive_members_never_extract(tmp_path, names):
    data = malformed_zip([(name, b"<p>Disclosure</p>") for name in names])
    with pytest.raises(ConversionFailure):
        audit_archive_bytes(
            data, submission=SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "change", ["symlink", "extra", "prefix", "suffix", "crc", "local_flags", "local_name", "encrypted"]
)
def test_corrupt_or_noncanonical_zip_rejected(change):
    data = malformed_zip([("filing.htm", b"<p>Disclosure</p>")], change)
    if change == "prefix":
        data = b"junk" + data
    elif change == "suffix":
        data += b"junk"
    elif change == "crc":
        offset = 30 + len("filing.htm")
        data = data[:offset] + b"X" + data[offset + 1 :]
    elif change == "local_flags":
        value = bytearray(data)
        struct.pack_into("<H", value, 6, 8)
        data = bytes(value)
    elif change == "local_name":
        data = data[:30] + b"F" + data[31:]
    elif change == "encrypted":
        value = bytearray(data)
        cd = value.find(b"PK\x01\x02")
        struct.pack_into("<H", value, cd + 8, 1)
        data = bytes(value)
    with pytest.raises(ConversionFailure):
        audit_archive_bytes(
            data, submission=SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
        )


def test_actual_archived_content_revalidated_not_just_crc(tmp_path):
    data = write_zip(tmp_path, {"filing.htm": b"<html><body><script>alert(1)</script></body></html>"})
    with pytest.raises(ConversionFailure, match="PACKAGE_SEC_VALIDATION_FAILED"):
        audit_archive_bytes(
            data, submission=SubmissionContext(form_type="S-1", encoded_submission_bytes=10000)
        )


def test_changed_payload_and_unused_asset_rejected(filing, tmp_path):
    htm, assets, submission = filing
    sec = validate_files(htm, assets, submission)
    payloads = _members(htm, assets, PackagingPolicy(), ProcessingContext())
    payloads[htm.name] = b"<p>Different disclosure</p>"
    data = write_zip(tmp_path, payloads)
    with pytest.raises(ConversionFailure, match="PACKAGE_PAYLOAD_CHANGED"):
        audit_archive_bytes(data, sec.files, submission)
    with pytest.raises(ConversionFailure, match="PACKAGE_SEC_VALIDATION_FAILED"):
        audit_archive_bytes(data, submission=submission)


@pytest.mark.parametrize(
    "policy",
    [
        PackagingPolicy(max_archive_bytes=1),
        PackagingPolicy(max_member_bytes=1),
        PackagingPolicy(max_uncompressed_bytes=1),
        PackagingPolicy(max_members=1),
    ],
)
def test_archive_resource_limits_fail(filing, tmp_path, policy):
    htm, assets, submission = filing
    data = write_zip(tmp_path, _members(htm, assets, PackagingPolicy(), ProcessingContext()))
    with pytest.raises(ConversionFailure):
        audit_archive_bytes(data, submission=submission, policy=policy)


def test_incomplete_conversion_never_becomes_complete():
    assert not completion_ready(
        {"status": "packaged", "final_conversion_complete": True, "source_unchanged": True, "diagnostics": []}
    )


def test_exclusive_archive_write_never_removes_existing_file(tmp_path):
    path = tmp_path / "existing.zip"
    path.write_bytes(b"preserve existing artifact")
    with pytest.raises(FileExistsError):
        _write_archive(path, {"filing.htm": b"<p>Disclosure</p>"}, PackagingPolicy(), ProcessingContext())
    assert path.read_bytes() == b"preserve existing artifact"


def test_cancelled_archive_write_removes_only_its_partial_file(tmp_path):
    path = tmp_path / "result.part"
    with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
        _write_archive(
            path,
            {"filing.htm": b"<p>Disclosure</p>"},
            PackagingPolicy(),
            ProcessingContext(cancelled=lambda: True),
        )
    assert not path.exists()


def test_oversized_archive_write_removes_partial_file(tmp_path):
    path = tmp_path / "result.part"
    with pytest.raises(ConversionFailure, match="PACKAGE_ARCHIVE_BYTE_LIMIT"):
        _write_archive(
            path,
            {"filing.htm": b"<p>Disclosure</p>"},
            PackagingPolicy(max_archive_bytes=1),
            ProcessingContext(),
        )
    assert not path.exists()
