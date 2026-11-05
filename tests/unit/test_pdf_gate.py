import pymupdf
import pytest
from conftest import ROOT
from converter.errors import ConversionFailure
from converter.pdf_export.validation import PDFValidationPolicy, validate_pdf


def make_pdf(path, text="Disclosure text", position=(72, 72), pages=1, color=(0, 0, 0)):
    with pymupdf.open() as document:
        for _ in range(pages):
            page = document.new_page(width=612, height=792)
            page.insert_text(position, text, fontsize=11, color=color)
        document.save(path)
    return path


def test_reference_self_comparison_all_23_pages():
    reference = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf"
    result = validate_pdf(reference, reference)
    assert result["passed"] and len(result["pages"]) == 23
    assert all(page["different_pixels"] == 0 for page in result["pages"])


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"text": "Changed disclosure"}, "PDF_CONTENT_MISMATCH"),
        ({"position": (76, 72)}, "PDF_TEXT_POSITION_MISMATCH"),
        ({"color": (1, 0, 0)}, "PDF_FONT_MISMATCH"),
        ({"pages": 2}, "PDF_EXTRA_PAGE"),
    ],
)
def test_strict_gate_detects_content_geometry_font_and_pages(tmp_path, change, expected):
    baseline = make_pdf(tmp_path / "reference.pdf")
    candidate = make_pdf(tmp_path / "actual.pdf", **change)
    result = validate_pdf(candidate, baseline, evidence_directory=tmp_path / "evidence")
    assert not result["passed"]
    assert any(expected in page["codes"] for page in result["pages"])


def test_page_23_change_is_not_missed(tmp_path):
    baseline = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf"
    changed = tmp_path / "changed.pdf"
    with pymupdf.open(baseline) as document:
        document[22].insert_text((20, 20), "Changed page 23", fontsize=8)
        document.save(changed)
    report = validate_pdf(changed, baseline)
    assert not report["passed"] and len(report["pages"]) == 23
    assert all(page["passed"] for page in report["pages"][:22])
    assert "PDF_CONTENT_MISMATCH" in report["pages"][22]["codes"]


def test_missing_reference_is_not_strict_success(tmp_path):
    report = validate_pdf(make_pdf(tmp_path / "actual.pdf"))
    assert not report["passed"] and report["diagnostics"] == [{"code": "PDF_REFERENCE_REQUIRED"}]


def test_invalid_encrypted_and_active_pdfs_rejected(tmp_path):
    invalid = tmp_path / "invalid.pdf"
    invalid.write_bytes(b"not a PDF")
    with pytest.raises(ConversionFailure, match="PDF_INVALID"):
        validate_pdf(invalid)
    original = make_pdf(tmp_path / "original.pdf")
    encrypted = tmp_path / "encrypted.pdf"
    with pymupdf.open(original) as document:
        document.save(encrypted, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="reader")
    with pytest.raises(ConversionFailure, match="PDF_INVALID"):
        validate_pdf(encrypted)
    active = tmp_path / "active.pdf"
    with pymupdf.open(original) as document:
        document.xref_set_key(
            document.pdf_catalog(), "OpenAction", r"<< /S /JavaScript /JS (app.alert\(1\)) >>"
        )
        document.save(active)
    with pytest.raises(ConversionFailure, match="PDF_INVALID"):
        validate_pdf(active)


def test_raster_limits_are_not_bypassed(tmp_path):
    actual = make_pdf(tmp_path / "actual.pdf")
    with pytest.raises(ConversionFailure, match="PDF_PAGE_LIMIT"):
        validate_pdf(actual, policy=PDFValidationPolicy(max_render_pixels=100))


def test_identical_intentionally_blank_page_is_allowed(tmp_path):
    actual = make_pdf(tmp_path / "actual.pdf")
    with pymupdf.open(actual) as document:
        document.new_page(width=612, height=792)
        document.save(tmp_path / "with-blank.pdf")
    report = validate_pdf(tmp_path / "with-blank.pdf", tmp_path / "with-blank.pdf")
    assert report["passed"] and len(report["pages"]) == 2


def test_pdf_file_size_limit_before_parsing(tmp_path):
    actual = make_pdf(tmp_path / "actual.pdf")
    with pytest.raises(ConversionFailure, match="PDF_INVALID"):
        validate_pdf(actual, policy=PDFValidationPolicy(max_pdf_bytes=1))


def test_evidence_quota_does_not_conceal_page_failures(tmp_path):
    reference = make_pdf(tmp_path / "reference.pdf")
    actual = make_pdf(tmp_path / "actual.pdf", text="Different text", pages=2)
    report = validate_pdf(
        actual,
        reference,
        policy=PDFValidationPolicy(max_evidence_bytes=0),
        evidence_directory=tmp_path / "evidence",
    )
    assert not report["passed"] and report["evidence_truncated"]
    assert report["evidence_bytes"] == 0 and len(report["pages"]) == 2
