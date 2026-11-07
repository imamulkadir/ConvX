import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pymupdf
import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.input_pipeline import process_input
from converter.ooxml import sha256
from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.standard_visual import verify_standard
from layout_fixtures import merged_table_pdf, simple_pdf
from lxml import etree, html
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("factory", [simple_pdf, merged_table_pdf])
def test_actual_edgar_browser_dom_print_and_raw_pixels(tmp_path, factory):
    source = factory(tmp_path / "source.pdf")
    report = process_input(source, tmp_path / "attempt", "financial report.pdf", mode="edgar")
    assert report["status"] == "packaged", report["diagnostics"]
    assert report["packaging"]["validated"]
    assert report["sec_validation"]["passed"] and not report["sec_validation"]["strict_passed"]
    visual = report["edgar_visual_validation"]
    assert visual["checks_complete"] and visual["text_verified"] and visual["page_geometry_verified"]
    assert visual["method"] == "chromium-edgar-flow-screen-print-v1"
    assert visual["network_requests_denied"] == 0
    assert report["source_unchanged"] and report["final_conversion_complete"]
    for page in visual["pages"]:
        assert page["word_geometry"]["missing_words"] == 0
        assert page["word_geometry"]["max_origin_error_pt"] < 6
        assert page["screen"]["dimensions_match"] and page["print"]["dimensions_match"]
    for name, digest in visual["artifact_sha256"].items():
        assert sha256(tmp_path / "attempt/edgar-visual" / name) == digest


@pytest.mark.parametrize("format", ["JPEG", "PNG"])
def test_actual_graphics_normalized_to_local_jpg_or_gif(tmp_path, format):
    image = BytesIO()
    Image.new("RGB", (8, 6), (20, 150, 240)).save(image, format=format)
    source = tmp_path / "image.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=600)
        page.insert_text((40, 50), "Independent image report")
        page.insert_image(pymupdf.Rect(40, 100, 120, 160), stream=image.getvalue())
        page.insert_image(pymupdf.Rect(200, 200, 280, 260), stream=image.getvalue())
        doc.save(source)
    report = process_input(source, tmp_path / "attempt", "image.pdf", mode="edgar")
    assert report["packaging"]["validated"], report["diagnostics"]
    generation = report["html_generation"]
    assert len(generation["assets"]) == 1
    assert {p.name for p in (tmp_path / "attempt/edgar").iterdir()} == {
        generation["filename"],
        *generation["assets"],
    }
    asset = next(iter(generation["assets"].values()))
    assert asset["format"] == ("JPEG" if format == "JPEG" else "GIF")
    if format == "JPEG":
        assert asset["original_jpeg_preserved"]
        assert (tmp_path / "attempt/edgar" / asset["filename"]).read_bytes() == image.getvalue()


def test_actual_browser_detects_major_flow_displacement(tmp_path):
    source = simple_pdf(tmp_path / "source.pdf")
    report = process_input(source, tmp_path / "attempt", "source.pdf", mode="edgar")
    generation = report["html_generation"]
    directory = tmp_path / "attempt/edgar"
    path = directory / generation["filename"]
    parsed = html.fromstring(path.read_bytes())
    font = parsed.xpath("//font")[0]
    font.set("style", font.get("style").replace("margin-left:0pt", "margin-left:20pt"))
    path.write_bytes(etree.tostring(parsed, method="html", encoding="ascii"))
    generation["sha256"] = sha256(path)
    with pytest.raises(ConversionFailure, match="EDGAR_LAYOUT_INCOMPATIBLE"):
        verify_standard(source, directory, generation, tmp_path / "displaced-check", ProcessingContext())


def test_mixed_edgar_print_dimensions_fail_explicitly(tmp_path):
    source = tmp_path / "mixed.pdf"
    with pymupdf.open() as doc:
        for width, height in [(400, 600), (600, 400)]:
            page = doc.new_page(width=width, height=height)
            page.insert_text((40, 100), "Mixed EDGAR print dimensions")
        doc.save(source)
    report = process_input(source, tmp_path / "attempt", "mixed.pdf", mode="edgar")
    assert report["status"] == "failed"
    assert report["diagnostics"][-1]["code"] == "EDGAR_MIXED_PRINT_GEOMETRY_UNSUPPORTED"


def test_real_docx_acceptance_export_and_edgar_flow(tmp_path):
    source = tmp_path / "source.docx"
    with ZipFile(source, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Independent accepted disclosure 123.45</w:t></w:r></w:p></w:body></w:document>',
        )
    provider = LibreOfficeProvider(ROOT / ".tools/libreoffice/program/soffice.com")
    report = process_input(source, tmp_path / "attempt", "source.docx", provider, mode="edgar")
    assert report["packaging"]["validated"], report["diagnostics"]
    assert report["revision_acceptance"]["after"]["total"] == 0 and report["source_unchanged"]
    assert report["visual_reference"]["method"] == "accepted_docx_local_export"


@pytest.mark.parametrize(
    "name",
    [
        "06749LWD4_prelim_prospectus_automated.pdf",
        "06749LWD4_prelim_prospectus_automated.docx",
        "06749LWD4_prelim_prospectus_automated (1).docx",
    ],
)
def test_reference_inputs_preserve_source_through_layered_edgar_and_zip(tmp_path, name):
    source = ROOT / "tests/fixtures" / name
    before = sha256(source)
    provider = LibreOfficeProvider(ROOT / ".tools/libreoffice/program/soffice.com")
    report = process_input(source, tmp_path / "attempt", name, provider, mode="edgar")
    assert report["input_preparation_complete"] and report["source_unchanged"]
    assert report["status"] == "packaged" and report["final_conversion_complete"], report["diagnostics"]
    assert report["html_generation"]["method"] == "efm78-layered-css2-v1"
    assert report["sec_validation"]["html_profile"] == "edgar_layers_v1"
    assert not report["sec_validation"]["strict_passed"]
    from tools.verify_download import verify_archive

    summary = verify_archive(
        tmp_path / "attempt/package/result.zip",
        tmp_path / "attempt" / report["generated_pdf_artifact"],
        report,
    )
    assert summary["source_text_verified"] and summary["crc_verified"] and summary["pages"] == 23
    tree = html.parse(str(next((tmp_path / "attempt/edgar").glob("*.htm"))))
    assert tree.findall(".//table") and not tree.xpath("//table//table")
    assert any(d["code"] == "EDGAR_VERTICAL_TEXT_REFLOWED" for d in report["diagnostics"])
    import copy

    from converter.packaging.current import verified_payloads

    changed = copy.deepcopy(report["html_generation"])
    changed["reflow_targets"]["1"][0]["target_origin"][0] += 50
    with pytest.raises(ConversionFailure, match="PACKAGE_VALIDATION_FAILED"):
        verified_payloads(
            tmp_path / "attempt" / report["generated_pdf_artifact"],
            tmp_path / "attempt/edgar",
            "edgar",
            changed,
            report["edgar_visual_validation"],
            ProcessingContext(),
        )
    assert before == sha256(source)
    assert len(list((tmp_path / "attempt").rglob("*.zip"))) == 1
    (tmp_path / "observed.json").write_text(
        json.dumps({"input": name, "diagnostics": report["diagnostics"]}, indent=2)
    )


@pytest.mark.parametrize("crop_image", [False, True])
def test_independent_rectangular_clip_image_and_vertical_text(tmp_path, crop_image):
    source = tmp_path / "source.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=600)
        page.insert_text((35, 55), "Independent disclosure 123.45", fontsize=10)
        stream = page.get_contents()[-1]
        doc.update_stream(stream, b"q\n30 520 340 60 re W n\n" + doc.xref_stream(stream) + b"\nQ\n")
        page.insert_text(
            (15, 450), "Independent marginal disclosure remains selectable.", fontsize=8, rotate=90
        )
        image = BytesIO()
        Image.new("RGB", (30, 20), (30, 100, 210)).save(image, format="JPEG")
        page.insert_image(pymupdf.Rect(35, 150, 95, 190), stream=image.getvalue())
        if crop_image:
            stream = page.get_contents()[-1]
            doc.update_stream(stream, b"q\n35 410 30 40 re W n\n" + doc.xref_stream(stream) + b"\nQ\n")
        doc.save(source)
    report = process_input(source, tmp_path / "attempt", source.name, mode="edgar")
    assert report["status"] == "packaged", report["diagnostics"]
    assert report["edgar_visual_validation"]["checks_complete"]
    assert report["edgar_visual_validation"]["pages"][0]["word_geometry"]["missing_words"] == 0
    assert report["html_generation"]["clip_association"][0]["associations"] > 0
    assert any(d["code"] == "EDGAR_VERTICAL_TEXT_REFLOWED" for d in report["diagnostics"])
    if not crop_image:
        import copy

        from converter.packaging.current import verified_payloads

        captured = tmp_path / "attempt/edgar-visual/rendered.pdf"
        original = captured.read_bytes()
        changed = tmp_path / "changed-print.pdf"
        with pymupdf.open(captured) as printed:
            matches = printed[0].search_for("123.45")
            assert matches
            for rect in matches:
                printed[0].add_redact_annot(rect)
            printed[0].apply_redactions()
            printed.save(changed)
        try:
            captured.write_bytes(changed.read_bytes())
            forged = copy.deepcopy(report["edgar_visual_validation"])
            forged["artifact_sha256"]["rendered.pdf"] = sha256(captured)
            with pytest.raises(ConversionFailure, match="PACKAGE_VALIDATION_FAILED"):
                verified_payloads(
                    tmp_path / "attempt" / report["generated_pdf_artifact"],
                    tmp_path / "attempt/edgar",
                    "edgar",
                    report["html_generation"],
                    forged,
                    ProcessingContext(),
                )
        finally:
            captured.write_bytes(original)


def test_nonrectangular_clip_still_fails_with_meaningful_diagnostic(tmp_path):
    source = tmp_path / "source.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=600)
        page.insert_text((40, 100), "Unsupported curved clipping", fontsize=10)
        stream = page.get_contents()[-1]
        doc.update_stream(
            stream,
            b"q\n30 450 m 30 550 350 550 350 450 c 350 400 30 400 30 450 c W n\n"
            + doc.xref_stream(stream)
            + b"\nQ\n",
        )
        doc.save(source)
    report = process_input(source, tmp_path / "attempt", source.name, mode="edgar")
    assert report["status"] == "failed"
    assert report["diagnostics"][-1]["code"] == "EDGAR_CLIPPING_UNSUPPORTED"
    assert not list((tmp_path / "attempt").rglob("*.zip"))
