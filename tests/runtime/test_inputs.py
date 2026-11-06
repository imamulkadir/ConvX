import json
from io import BytesIO

import pymupdf
import pytest
from conftest import ROOT
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.input_pipeline import process_input
from converter.ooxml import sha256
from converter.pdf_admission import admit_pdf
from converter.pdf_export.libreoffice import LibreOfficeProvider
from converter.revisions.accept import compare_accepted_content
from PIL import Image


def pdf_bytes(*, encrypted=False, scanned=False, active=False, attachment=False):
    with pymupdf.open() as document:
        page = document.new_page(width=500, height=300)
        if scanned:
            image = BytesIO()
            Image.new("RGB", (60, 40), "navy").save(image, format="PNG")
            page.insert_image(pymupdf.Rect(10, 10, 100, 100), stream=image.getvalue())
        else:
            page.insert_text((30, 60), "Independent PDF input: 123.45", fontsize=14)
            page = document.new_page(width=300, height=500)
            page.insert_text((30, 60), "Second page")
            page.set_rotation(90)
            document.set_toc([[1, "First independent page", 1], [1, "Second independent page", 2]])
        if active:
            xref = document.get_new_xref()
            document.update_object(xref, r"<< /S /JavaScript /JS (app.alert\(1\)) >>")
            document.xref_set_key(document.pdf_catalog(), "OpenAction", f"{xref} 0 R")
        if attachment:
            document.embfile_add("attachment.txt", b"not allowed")
        return document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256 if encrypted else pymupdf.PDF_ENCRYPT_NONE,
            owner_pw="owner" if encrypted else None,
            user_pw="secret" if encrypted else None,
        )


class NoRenderer:
    def render(self, *_):
        pytest.fail("Uploaded PDFs must never invoke the DOCX renderer")


def test_pdf_uses_unchanged_bytes_and_shared_analysis_without_docx(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(pdf_bytes())
    digest = sha256(source)
    result = process_input(source, tmp_path / "attempt", "Independent.PDF", NoRenderer())
    assert result["input_preparation_complete"], result
    assert result["source_unchanged"] and sha256(source) == digest
    assert result["pdf_input"]["candidate_sha256"] == digest
    assert result["visual_reference"]["method"] == "direct_uploaded_pdf"
    assert result["revision_acceptance"] is None and result["provider"] is None
    assert not list((tmp_path / "attempt").rglob("*.docx"))
    layout = json.loads((tmp_path / "attempt/layout.json").read_text())
    assert layout["mode"] == "authoritative_pdf" and not layout["reconstruction_eligible"]
    assert layout["validation_report_sha256"] is None
    assert len(layout["pages"]) == 2 and layout["fonts"]
    assert result["pdf_input"]["pages"][1]["rotation"] == 90
    assert not result["final_conversion_complete"] and result["status"] == "blocked"
    assert result["diagnostics"][-1]["code"] == "PACKAGING_ENGINE_PENDING"


@pytest.mark.parametrize("options", [{"encrypted": True}, {"active": True}, {"attachment": True}])
def test_unsafe_uploaded_pdfs_are_rejected(tmp_path, options):
    source = tmp_path / "source.pdf"
    source.write_bytes(pdf_bytes(**options))
    with pytest.raises(ConversionFailure, match="PDF_INVALID"):
        admit_pdf(source, ProcessingContext())


def test_mislabeled_pdf_and_invalid_dimensions_fail_without_output(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"PK\x03\x04 not a PDF")
    result = process_input(source, tmp_path / "invalid", "fake.pdf")
    assert result["status"] == "failed" and result["source_unchanged"]
    assert result["diagnostics"][0]["code"] == "PDF_SIGNATURE_INVALID"
    assert not (tmp_path / "invalid/layout.json").exists()
    with pymupdf.open() as document:
        document.new_page(width=3000, height=100)
        document.save(source)
    with pytest.raises(ConversionFailure, match="PDF_PAGE_LIMIT"):
        admit_pdf(source, ProcessingContext())


def test_image_only_pdf_reports_ocr_limit_without_inventing_text(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(pdf_bytes(scanned=True))
    result = process_input(source, tmp_path / "scan", "scan.pdf")
    assert result["input_preparation_complete"], result
    assert result["layout_analysis"]["characters"] == 0
    warning = next(item for item in result["diagnostics"] if item["code"] == "OCR_NOT_AVAILABLE")
    assert warning["pages"] == [1]
    layout = json.loads((tmp_path / "scan/layout.json").read_text())
    assert layout["assets"] and layout["pages"][0]["images"]


def test_pdf_launch_action_and_repaired_structure_are_rejected(tmp_path):
    source = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_link(
            {"kind": pymupdf.LINK_LAUNCH, "from": pymupdf.Rect(20, 20, 100, 60), "file": "unsafe.exe"}
        )
        document.save(source)
    with pytest.raises(ConversionFailure, match="PDF_ACTIVE_CONTENT"):
        admit_pdf(source, ProcessingContext())
    source.write_bytes(pdf_bytes().split(b"xref\n")[0] + b"%%EOF\n")
    with pytest.raises(ConversionFailure, match="PDF_(INVALID|REPAIR_REQUIRED)"):
        admit_pdf(source, ProcessingContext())


@pytest.mark.parametrize(
    "name",
    [
        "06749LWD4_prelim_prospectus_automated.docx",
        "06749LWD4_prelim_prospectus_automated (1).docx",
        "06749LWD4_prelim_prospectus_automated.pdf",
    ],
)
def test_real_reference_inputs_reach_shared_analysis_without_word_gate(tmp_path, name):
    source = ROOT / "tests/fixtures" / name
    local = ROOT / ".tools/libreoffice/program/soffice.com"
    if name.endswith(".docx") and not local.is_file():
        pytest.skip("Local free LibreOffice is not installed")
    result = process_input(source, tmp_path / "real", name, LibreOfficeProvider(local))
    assert result["input_preparation_complete"], result
    assert result["source_unchanged"] and result["pdf_input"]["page_count"] == 23
    assert result["layout_analysis"]["pages"] == 23 and result["layout_analysis"]["characters"] > 10000
    assert not result["pdf_input"]["word_equivalence_verified"]
    assert result["diagnostics"][-1]["code"] == "PACKAGING_ENGINE_PENDING"
    if name.endswith(".docx"):
        assert result["revision_acceptance"]["after"]["total"] == 0
        accepted = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated (1).docx"
        assert compare_accepted_content(tmp_path / "real/accepted.docx", accepted)["passed"]
