import pymupdf
import pytest
from converter.html_presentation import disclosure_text
from converter.input_pipeline import process_input
from converter.sec_validation.flow_profile import flow_style_problems
from converter.sec_validation.layer_profile import layer_style_problems
from lxml import html


def source_document(path, unsafe=False):
    with pymupdf.open() as doc:
        page = doc.new_page(width=500, height=650)
        # Deliberately insert body/fields before the visual title.
        page.insert_textbox(
            (40, 220, 460, 270),
            "A complete independent paragraph keeps financial text 123.45 and its "
            "continuation together rather than separate paragraphs for every PDF line.",
            fontsize=10,
        )
        for y, label, value in [
            (110, "Issuer:", "Independent Corporation"),
            (130, "Amount:", "$123.45"),
            (150, "Maturity:", "December 31, 2032"),
        ]:
            page.insert_text((40, y), label, fontsize=10)
            page.insert_text((170, y), value, fontsize=10)
        page.insert_text((40, 65), "Independent report heading", fontsize=12)
        stream = page.get_contents()[-1]
        doc.update_stream(stream, b"q\n30 560 440 50 re W n\n" + doc.xref_stream(stream) + b"\nQ\n")
        page.insert_text((15, 450), "Independent marginal notice retained first.", fontsize=8, rotate=90)
        url = "http://www.sec.gov/Archives/edgar/data/1234/report.htm"
        if unsafe:
            url = "http://www.sec.gov.evil.test/Archives/edgar/data/1234/report.htm"
        page.insert_text((40, 310), "Source document reference", fontsize=10)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(40, 298, 180, 313), "uri": url})
        doc.save(path)
    return path


@pytest.mark.parametrize("unsafe", [False, True])
def test_actual_source_paragraphs_reading_order_fields_and_sec_links(tmp_path, unsafe):
    source = source_document(tmp_path / "independent.pdf", unsafe)
    report = process_input(source, tmp_path / "attempt", source.name, mode="edgar")
    assert report["status"] == "packaged", report["diagnostics"]
    path = tmp_path / "attempt/edgar" / report["html_generation"]["filename"]
    tree = html.fromstring(path.read_bytes())
    text = disclosure_text(tree.find("body"))
    assert text.startswith("Independent marginal notice retained first.")
    assert (
        text.index("Independent report heading")
        < text.index("Issuer:")
        < text.index("A complete independent")
    )
    paragraphs = ["".join(p.itertext()) for p in tree.xpath("//p")]
    assert any("A complete independent" in p and "every PDF line." in p for p in paragraphs)
    table = tree.xpath("//table")
    assert len(table) == 1 and len(table[0].xpath("./tr")) == 3
    assert not tree.xpath("//table//table | //p//div | //p//p")
    assert "margin:0 auto" in tree.xpath("//body/div/@style")[0]
    hrefs = tree.xpath("//a/@href")
    if unsafe:
        assert not hrefs
        assert any(d["code"] == "EDGAR_EXTERNAL_LINK_INERT" for d in report["diagnostics"])
    else:
        assert hrefs == ["https://www.sec.gov/Archives/edgar/data/1234/report.htm"]
    visual = report["edgar_visual_validation"]["pages"][0]
    assert visual["word_geometry"]["missing_words"] == 0
    assert visual["word_geometry"]["max_origin_error_pt"] < 6
    with pymupdf.open(tmp_path / "attempt/edgar-visual/rendered.pdf") as printed:
        assert len(printed) == 1
        assert printed[0].search_for("123.45")


def test_centering_is_narrowly_scoped_to_layer_profile():
    assert not layer_style_problems("margin:0 auto;background-color:#ffffff")
    assert flow_style_problems("margin:0 auto")
    for invalid in ("margin:0 auto;margin:2pt", "margin:auto auto", "margin:calc(2pt) auto"):
        assert layer_style_problems(invalid)


def test_actual_column_order_is_not_interleaved_by_pdf_paint_order(tmp_path):
    source = tmp_path / "columns.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=500, height=650)
        for point, text in [
            ((280, 110), "Right first"),
            ((40, 130), "Left second"),
            ((280, 130), "Right second"),
            ((40, 110), "Left first"),
        ]:
            page.insert_text(point, text, fontsize=10)
        page.insert_text((40, 60), "Independent two-column report with a full-width heading", fontsize=12)
        stream = page.get_contents()[-1]
        doc.update_stream(stream, b"q\n30 560 440 50 re W n\n" + doc.xref_stream(stream) + b"\nQ\n")
        doc.save(source)
    report = process_input(source, tmp_path / "attempt", source.name, mode="edgar")
    assert report["status"] == "packaged", report["diagnostics"]
    tree = html.parse(str(tmp_path / "attempt/edgar" / report["html_generation"]["filename"]))
    text = "".join(tree.xpath("//body//text()"))
    assert (
        text.index("Left first")
        < text.index("Left second")
        < text.index("Right first")
        < text.index("Right second")
    )


def test_ambiguous_fields_remain_paragraphs_without_losing_intervening_text(tmp_path):
    source = source_document(tmp_path / "ambiguous.pdf")
    with pymupdf.open(source) as doc:
        doc[0].insert_text((110, 120), "Unrelated caption", fontsize=8)
        changed = tmp_path / "changed.pdf"
        doc.save(changed)
    report = process_input(changed, tmp_path / "attempt", "ambiguous.pdf", mode="edgar")
    assert report["status"] == "packaged", report["diagnostics"]
    tree = html.parse(str(tmp_path / "attempt/edgar" / report["html_generation"]["filename"]))
    assert not tree.xpath("//table")
    assert "Unrelated caption" in "".join(tree.xpath("//body//text()"))
