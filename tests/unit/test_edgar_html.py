import hashlib

import pytest
from converter.edgar_html import document_name, render_edgar
from converter.errors import ConversionFailure
from converter.sec_validation.flow_profile import flow_style_problems
from converter.sec_validation.models import ValidationPolicy
from converter.sec_validation.validator import validate_files
from layout_fixtures import complex_pdf, merged_table_pdf, simple_pdf
from lxml import html
from test_standard_html import prepare


@pytest.mark.parametrize(
    "name", ["report.pdf", "hello world.docx", "_data.pdf", "x" * 150 + ".pdf", "বাংলা.docx"]
)
def test_portable_deterministic_filename(name):
    output = document_name(name)
    assert output == document_name(name) and len(output) <= 32
    assert output.isascii() and output[0].isalnum() and output.endswith(".htm")
    assert document_name("report.pdf") == "report.htm"


@pytest.mark.parametrize("factory", [simple_pdf, merged_table_pdf])
def test_real_flow_text_tables_and_source_authority(tmp_path, factory):
    source = factory(tmp_path / "source.pdf")
    layout, context = prepare(source, tmp_path)
    result = render_edgar(source, layout, tmp_path / "edgar", "financial report.pdf", context)
    tree = html.fromstring((tmp_path / "edgar" / result["filename"]).read_bytes())
    assert result["sec_validation"]["passed"] and not result["sec_validation"]["strict_passed"]
    assert not result["sec_validation"]["sec_acceptance_confirmed"]
    assert not tree.xpath("//svg|//script|//style|//link|//span|//table//table")
    assert result["characters"] == sum(p.character_count for p in layout.pages)
    assert not layout.reconstruction_eligible and layout.validation_report_sha256 is None
    if factory == merged_table_pdf:
        assert tree.xpath('//td[@colspan="2"]')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == result["source_pdf_sha256"]
    assert not validate_files(tmp_path / "edgar" / result["filename"]).passed, (
        "Legacy strict CSS uncertainty remains"
    )


def test_stale_and_inspection_models_cannot_authorize_edgar(tmp_path):
    source = simple_pdf(tmp_path / "source.pdf")
    layout, context = prepare(source, tmp_path)
    for changed in [
        layout.model_copy(update={"mode": "inspection_only"}),
        layout.model_copy(update={"verification": None}),
    ]:
        with pytest.raises(ConversionFailure, match="EDGAR_AUTHORITY_REQUIRED"):
            render_edgar(source, changed, tmp_path / "edgar", "source.pdf", context)
    source.write_bytes(source.read_bytes() + b"\nchanged")
    with pytest.raises(ConversionFailure, match="EDGAR_AUTHORITY_REQUIRED"):
        render_edgar(source, layout, tmp_path / "edgar", "source.pdf", context)


def test_unsupported_complex_geometry_fails_instead_of_rasterizing_text(tmp_path):
    source = complex_pdf(tmp_path / "source.pdf")
    layout, context = prepare(source, tmp_path)
    with pytest.raises(ConversionFailure, match="HTM_TEXT_ROTATION_UNSUPPORTED"):
        render_edgar(source, layout, tmp_path / "edgar", "source.pdf", context)
    assert not (tmp_path / "edgar").exists()


@pytest.mark.parametrize(
    "markup",
    [
        "<script>x()</script>",
        "<svg></svg>",
        "<span>x</span>",
        '<p onclick="x()">x</p>',
        '<p style="position:absolute">x</p>',
        '<p style="box-sizing:border-box">x</p>',
        '<p style="display:none">x</p>',
        '<p style="width:expression(x)">x</p>',
        '<p style="color:transparent">x</p>',
        '<p style="background:url(https://example.org)">x</p>',
        '<a href="https://example.org">x</a>',
        '<a href="mailto:x@example.org">x</a>',
        '<img src="data:image/gif;base64,AAAA">',
        '<img src="../x.jpg">',
        '<img src="image.png">',
        "<table><tr><td><table></table></td></tr></table>",
        '<meta http-equiv="refresh">',
        "<!DOCTYPE html><p>x</p>",
        "<p>&#149;</p>",
        "<p>&#0;</p>",
    ],
)
def test_actual_edgar_profile_rejects_unsafe_or_unsupported_bytes(tmp_path, markup):
    path = tmp_path / "document.htm"
    path.write_text(markup, encoding="ascii")
    assert not validate_files(path, policy=ValidationPolicy(html_profile="edgar_flow_v1")).passed


def test_documented_html4_reference_mapping_and_style_scope(tmp_path):
    path = tmp_path / "document.htm"
    path.write_bytes(
        b'<html><body><p style="margin:0;font-size:12pt">&#163; &#8364; &#8212; &#8220; &trade;</p></body></html>'
    )
    result = validate_files(path, policy=ValidationPolicy(html_profile="edgar_flow_v1"))
    assert result.passed and result.html_profile == "edgar_flow_v1"
    assert not result.sec_acceptance_confirmed and not result.strict_passed
    assert not validate_files(path).passed
    assert flow_style_problems("position:absolute")


def test_css_looking_disclosure_is_never_rewritten(tmp_path):
    text = "box-sizing:border-box; 123.45 < & >"
    source = simple_pdf(tmp_path / "source.pdf", text=text)
    layout, context = prepare(source, tmp_path)
    result = render_edgar(source, layout, tmp_path / "edgar", "source.pdf", context)
    parsed = html.fromstring((tmp_path / "edgar" / result["filename"]).read_bytes())
    assert "".join(parsed.find("body").itertext()) == text
    assert result["characters"] == len(text)
    assert all("box-sizing" not in v for v in parsed.xpath("//@style"))
