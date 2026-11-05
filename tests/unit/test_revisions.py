from zipfile import ZipFile

import pytest
from conftest import ROOT, docx_bytes
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.ooxml import parse_xml, read_package, sha256
from converter.revisions.accept import accept_revisions, compare_accepted_content
from converter.revisions.inventory import inventory
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def document(body):
    return f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'.encode()


def accept(tmp_path, body, extra=None):
    source, target = tmp_path / "source.docx", tmp_path / "accepted.docx"
    source.write_bytes(docx_bytes({"word/document.xml": document(body), **(extra or {})}))
    before = source.read_bytes()
    result = accept_revisions(source, target)
    assert source.read_bytes() == before
    parts = read_package(target)
    assert inventory(parts)["total"] == 0
    return parse_xml(parts["word/document.xml"], "word/document.xml"), result, parts


def test_accept_real_fixture_all_stories_and_media(tmp_path):
    source = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated.docx"
    expected = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated (1).docx"
    target = tmp_path / "accepted.docx"
    original = sha256(source)
    result = accept_revisions(source, target)
    comparison = compare_accepted_content(target, expected)
    assert result["before"]["total"] == 31
    assert result["after"]["total"] == 0
    assert result["media_preserved"] and result["source_unchanged"] and sha256(source) == original
    assert comparison["passed"] and len(comparison["stories"]) == 18
    with ZipFile(source) as a, ZipFile(target) as b:
        for name in a.namelist():
            if name not in result["changed_parts"] and not name.endswith("/"):
                assert a.read(name) == b.read(name)


def test_insert_delete_replace_and_formatting(tmp_path):
    root, _, _ = accept(
        tmp_path,
        '<w:p><w:del w:id="1"><w:r><w:delText>deleted</w:delText></w:r></w:del>'
        '<w:ins w:id="2"><w:r><w:rPr><w:b/><w:rPrChange w:id="3"><w:rPr><w:i/></w:rPr></w:rPrChange></w:rPr><w:t>accepted</w:t></w:r></w:ins></w:p>',
    )
    assert root.xpath('//*[local-name()="t"]/text()') == ["accepted"]
    assert root.xpath('//*[local-name()="b"]')
    assert not root.xpath('//*[local-name()="i"]')
    assert "deleted" not in etree.tostring(root).decode()


def test_paragraph_mark_deletion_joins_without_losing_text(tmp_path):
    root, _, _ = accept(
        tmp_path,
        '<w:p><w:pPr><w:rPr><w:del w:id="1"/></w:rPr></w:pPr><w:r><w:t>one</w:t></w:r></w:p>'
        '<w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:t>two</w:t></w:r></w:p>',
    )
    assert len(root.xpath('//*[local-name()="p"]')) == 1
    assert root.xpath('//*[local-name()="t"]/text()') == ["one", "two"]
    assert root.xpath('//*[local-name()="jc"]/@w:val', namespaces={"w": W}) == ["right"]


def test_paragraph_inserted_mark_preserves_break(tmp_path):
    root, _, _ = accept(
        tmp_path,
        '<w:p><w:pPr><w:rPr><w:ins w:id="1"/></w:rPr></w:pPr><w:r><w:t>one</w:t></w:r></w:p><w:p><w:r><w:t>two</w:t></w:r></w:p>',
    )
    assert len(root.xpath('//*[local-name()="p"]')) == 2


def test_rows_and_property_changes(tmp_path):
    body = '<w:tbl><w:tblPr><w:tblW w:w="5000"/><w:tblPrChange w:id="1"><w:tblPr/></w:tblPrChange></w:tblPr>'
    body += '<w:tr><w:trPr><w:del w:id="2"/></w:trPr><w:tc><w:p><w:r><w:t>remove row</w:t></w:r></w:p></w:tc></w:tr>'
    body += '<w:tr><w:trPr><w:ins w:id="3"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="5000"/><w:tcPrChange w:id="4"><w:tcPr/></w:tcPrChange></w:tcPr><w:p><w:r><w:t>keep row</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
    root, _, _ = accept(tmp_path, body)
    assert len(root.xpath('//*[local-name()="tr"]')) == 1
    assert root.xpath('//*[local-name()="t"]/text()') == ["keep row"]
    assert root.xpath('//*[local-name()="tblW"]') and root.xpath('//*[local-name()="tcW"]')


def test_moves_and_range_markers(tmp_path):
    root, _, _ = accept(
        tmp_path,
        '<w:p><w:moveFromRangeStart w:id="1"/><w:moveFrom w:id="2"><w:r><w:t>moved</w:t></w:r></w:moveFrom><w:moveFromRangeEnd w:id="1"/>'
        '<w:moveToRangeStart w:id="3"/><w:moveTo w:id="4"><w:r><w:t>moved</w:t></w:r></w:moveTo><w:moveToRangeEnd w:id="3"/></w:p>',
    )
    assert root.xpath('//*[local-name()="t"]/text()') == ["moved"]


def test_revisions_in_headers_notes_and_textboxes(tmp_path):
    extra = {
        f"word/{name}.xml": f'<w:{root} xmlns:w="{W}"><w:p><w:ins w:id="1"><w:r><w:t>new</w:t></w:r></w:ins></w:p></w:{root}>'.encode()
        for name, root in [
            ("header1", "hdr"),
            ("footer1", "ftr"),
            ("footnotes", "footnotes"),
            ("endnotes", "endnotes"),
        ]
    }
    _, result, parts = accept(
        tmp_path,
        '<w:p><w:r><w:pict><w:txbxContent><w:p><w:del w:id="2"><w:r><w:delText>gone</w:delText></w:r></w:del><w:r><w:t>box</w:t></w:r></w:p></w:txbxContent></w:pict></w:r></w:p>',
        extra,
    )
    assert result["before"]["total"] == 5
    assert all(b"new" in parts[name] for name in extra)
    assert b"gone" not in parts["word/document.xml"]


@pytest.mark.parametrize(
    "revision", ["cellIns", "cellDel", "cellMerge", "customXmlInsRangeStart", "conflictIns", "futurePrChange"]
)
def test_unsupported_revision_fails_before_output(tmp_path, revision):
    source, target = tmp_path / "source.docx", tmp_path / "accepted.docx"
    source.write_bytes(
        docx_bytes(
            {"word/document.xml": document(f'<w:p><w:{revision} w:id="1"/><w:r><w:t>keep</w:t></w:r></w:p>')}
        )
    )
    before = source.read_bytes()
    with pytest.raises(ConversionFailure, match="UNSUPPORTED_REVISION"):
        accept_revisions(source, target)
    assert source.read_bytes() == before and not target.exists()


@pytest.mark.parametrize(
    "body",
    [
        '<w:p><w:pPr><w:rPr><w:del w:id="1"/></w:rPr><w:sectPr/></w:pPr></w:p><w:p/>',
        '<w:p><w:moveFrom w:id="1"><w:r><w:t>orphan</w:t></w:r></w:moveFrom></w:p>',
        '<w:p><w:moveFromRangeStart w:id="1"/><w:r><w:t>ambiguous</w:t></w:r></w:p>',
        "<w:p><w:r><w:delText>orphan</w:delText></w:r></w:p>",
    ],
)
def test_ambiguous_revisions_fail_safely(tmp_path, body):
    with pytest.raises(ConversionFailure, match="UNSUPPORTED_REVISION"):
        accept(tmp_path, body)


def test_deterministic_acceptance_and_tracking_disabled(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(
        docx_bytes(
            {"word/settings.xml": f'<w:settings xmlns:w="{W}"><w:trackRevisions/></w:settings>'.encode()}
        )
    )
    first, second = tmp_path / "one.docx", tmp_path / "two.docx"
    accept_revisions(source, first)
    accept_revisions(source, second)
    assert first.read_bytes() == second.read_bytes()
    assert b"trackRevisions" not in read_package(first)["word/settings.xml"]
    with pytest.raises(ConversionFailure, match="UNSAFE_OUTPUT_PATH"):
        accept_revisions(source, first)


def test_cancel_before_acceptance_leaves_no_output(tmp_path):
    source, target = tmp_path / "source.docx", tmp_path / "accepted.docx"
    source.write_bytes(docx_bytes())
    with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
        accept_revisions(source, target, ProcessingContext(cancelled=lambda: True))
    assert not target.exists()


def test_property_change_in_wrong_container_is_rejected(tmp_path):
    with pytest.raises(ConversionFailure, match="UNSUPPORTED_REVISION"):
        accept(tmp_path, '<w:p><w:rPrChange w:id="1"><w:rPr/></w:rPrChange></w:p>')
