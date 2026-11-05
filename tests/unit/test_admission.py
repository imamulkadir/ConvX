import stat
from io import BytesIO
from zipfile import ZipFile, ZipInfo

import pytest
from app.core.errors import Problem
from app.services.admission import validate_docx
from app.services.storage import Storage, safe_filename
from conftest import docx_bytes


def check(settings, tmp_path, data):
    path = tmp_path / "document.docx"
    path.write_bytes(data)
    validate_docx(path, settings)


def test_real_original_and_accepted_fixtures(settings):
    from conftest import ROOT

    for path in (ROOT / "tests/fixtures").glob("*.docx"):
        validate_docx(path, settings)


@pytest.mark.parametrize(
    "name",
    [
        "../file.docx",
        "C:\\file.docx",
        "a/b.docx",
        ".hidden.docx",
        "evil\n.docx",
        "name.docm",
        "file.docx ",
        "a:stream.docx",
        "a" * 250 + ".docx",
    ],
)
def test_reject_unsafe_names(name):
    with pytest.raises(Problem):
        safe_filename(name)


def test_storage_containment(settings, tmp_path):
    storage = Storage(settings)
    outside = tmp_path / "keep.txt"
    outside.write_text("keep")
    for name in ("../keep.txt", str(tmp_path), "not-a-uuid"):
        with pytest.raises(ValueError):
            storage.remove(name)
    assert outside.read_text() == "keep"


@pytest.mark.parametrize(
    "extra,code",
    [
        ({"../escape.xml": b"<x/>"}, "UNSAFE_ZIP_PATH"),
        ({"word/vbaProject.bin": b"macro"}, "ACTIVE_CONTENT"),
        ({"word/embeddings/ole.bin": b"object"}, "ACTIVE_CONTENT"),
        (
            {"word/document.xml": b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///secret">]><x>&e;</x>'},
            "UNSAFE_XML",
        ),
        ({"word/document.xml": b"<broken>"}, "INVALID_DOCX"),
        ({"word/document.xml": b"<wrong/>"}, "INVALID_DOCX"),
        ({"word/extra.xml": b"<x>" * 130 + b"</x>" * 130}, "XML_LIMIT_EXCEEDED"),
        ({"word/extra.xml": b"<x><instrText>DDEAUTO cmd</instrText></x>"}, "ACTIVE_FIELD"),
        ({"word/extra.xml": b"<x><altChunk/></x>"}, "UNSUPPORTED_EMBEDDED_CONTENT"),
    ],
)
def test_reject_hostile_packages(settings, tmp_path, extra, code):
    with pytest.raises(Problem) as exc:
        check(settings, tmp_path, docx_bytes(extra))
    assert exc.value.code == code


def test_reject_zip_bomb(settings, tmp_path):
    with pytest.raises(Problem, match="ZIP_LIMIT_EXCEEDED"):
        check(settings, tmp_path, docx_bytes({"word/bomb.bin": b"0" * 500000}))


def test_reject_duplicate_entries(settings, tmp_path):
    data = BytesIO(docx_bytes())
    with ZipFile(data, "a") as archive:
        archive.writestr("WORD/DOCUMENT.XML", "<x/>")
    with pytest.raises(Problem, match="UNSAFE_ZIP_PATH"):
        check(settings, tmp_path, data.getvalue())


def test_reject_symlink_entry(settings, tmp_path):
    data = BytesIO(docx_bytes())
    with ZipFile(data, "a") as archive:
        entry = ZipInfo("word/link")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(entry, "/etc/passwd")
    with pytest.raises(Problem, match="UNSAFE_ZIP_PATH"):
        check(settings, tmp_path, data.getvalue())


@pytest.mark.parametrize(
    "kind,target,expected",
    [
        ("image", "https://example.com/x.jpg", "EXTERNAL_RELATIONSHIP"),
        ("attachedTemplate", "https://example.com/t.dotm", "EXTERNAL_RELATIONSHIP"),
        ("hyperlink", "file:///secret", "EXTERNAL_RELATIONSHIP"),
        ("hyperlink", "https://www.sec.gov/Archives/edgar/data/1/a.htm", None),
    ],
)
def test_external_relationship_policy(settings, tmp_path, kind, target, expected):
    payload = docx_bytes(
        {
            "word/_rels/document.xml.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{kind}" Target="{target}" TargetMode="External"/></Relationships>'.encode()
        }
    )
    if expected:
        with pytest.raises(Problem, match=expected):
            check(settings, tmp_path, payload)
    else:
        check(settings, tmp_path, payload)


def test_reject_truncated_zip(settings, tmp_path):
    with pytest.raises(Problem):
        check(settings, tmp_path, docx_bytes()[:-40])
