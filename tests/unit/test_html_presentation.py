import pymupdf
from converter.edgar_dividers import divider_geometry
from converter.html_presentation import disclosure_text, readable_html
from lxml import html


def test_indentation_preserves_inline_spaces_nbsp_and_literal_text_newlines():
    tree = html.document_fromstring(
        "<html><head><title>Report</title></head><body><div><p><font>Price: </font>"
        "<font> 123.45\n  </font><b> USD&#160;</b><font>\n  </font></p></div></body></html>"
    )
    expected = "".join(tree.find("body").itertext())
    payload = readable_html(tree)
    assert b"<html>\n  <head>" in payload
    assert b"\n    <div>\n      <p>" in payload
    parsed = html.document_fromstring(payload)
    assert disclosure_text(parsed.find("body")) == expected
    parsed.xpath("//font")[1].text = "999.99"
    assert disclosure_text(parsed.find("body")) != expected


def test_unmarked_old_html_keeps_all_structural_whitespace():
    tree = html.document_fromstring("<html><body><div>\n  <p>Disclosure</p>\n</div></body></html>")
    assert disclosure_text(tree.find("body")) == "\n  Disclosure\n"


def test_divider_will_not_cover_a_full_bleed_graphic():
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=600)
        page.draw_rect(page.rect, fill=(0, 0, 1), color=None)
        assert divider_geometry(page, {"chunks": []}) is None
