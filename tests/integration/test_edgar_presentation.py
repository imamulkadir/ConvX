import pymupdf
import pytest
from converter.html_presentation import disclosure_text
from converter.input_pipeline import process_input
from lxml import html

from tools.verify_download import verify_archive


@pytest.mark.parametrize("layered", [False, True])
def test_actual_two_page_separator_indentation_print_and_zip(tmp_path, layered):
    source = tmp_path / "pages.pdf"
    with pymupdf.open() as document:
        for index in range(2):
            page = document.new_page(width=400, height=600)
            page.insert_text((40, 60), f"Independent page {index + 1}: price 123.45", fontsize=10)
            if layered:
                stream = page.get_contents()[-1]
                document.update_stream(
                    stream, b"q\n30 500 340 80 re W n\n" + document.xref_stream(stream) + b"\nQ\n"
                )
        document.save(source)
    report = process_input(source, tmp_path / "attempt", "pages.pdf", mode="edgar")
    assert report["status"] == "packaged", report["diagnostics"]
    filename = report["html_generation"]["filename"]
    payload = (tmp_path / "attempt/edgar" / filename).read_bytes()
    assert b"<html>\n  <head>" in payload
    tree = html.document_fromstring(payload)
    frames = tree.xpath("/html/body/div")
    assert len(frames) == 2
    assert len(tree.xpath('//a[@name="pagebreak1"]')) == 1
    assert not tree.xpath('//a[@name="pagebreak2"]')
    assert len(tree.xpath('//div[contains(@style,"background-color:#808080")]')) == 1
    assert disclosure_text(frames[0]) == "Independent page 1: price 123.45"
    with pymupdf.open(tmp_path / "attempt/edgar-visual/rendered.pdf") as printed:
        assert len(printed) == 2
        assert tuple(printed[0].rect) == pytest.approx((0, 0, 400, 600), abs=0.1)
        assert printed[0].get_pixmap().pixel(200, 588) == (128, 128, 128)
    summary = verify_archive(
        tmp_path / "attempt/package/result.zip",
        tmp_path / "attempt" / report["generated_pdf_artifact"],
        report,
    )
    assert summary["source_text_verified"] and summary["crc_verified"]
