import pytest
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.sec_validation.models import SubmissionContext, ValidationPolicy
from converter.sec_validation.validator import validate_files
from PIL import Image


def check(tmp_path, markup, assets=(), submission=None, policy=None, name="filing.htm"):
    path = tmp_path / name
    path.write_bytes(markup if isinstance(markup, bytes) else markup.encode("ascii"))
    return validate_files(path, tuple(assets), submission, policy)


def codes(result):
    return {d.code for d in result.diagnostics}


def test_confirmed_subset_passes_and_submission_is_separate(tmp_path):
    result = check(
        tmp_path,
        '<html><head><title>Filing</title></head><body><p align="center"><b>Disclosure</b> &pound; &#233;</p><table border="1"><tr><td>Value</td></tr></table><a name="note"></a><a href="#note">Note</a><page></body></html>',
    )
    assert result.passed and not result.strict_passed and result.checks_complete
    assert not result.sec_acceptance_confirmed and not result.visual_fidelity_passed
    assert codes(result) == {"SUBMISSION_CONTEXT_REQUIRED"}
    result = validate_files(
        tmp_path / "filing.htm", submission=SubmissionContext(form_type="S-1", encoded_submission_bytes=1000)
    )
    assert result.strict_passed and result.submission_limits_checked
    assert result.registry_version == "efm-volume-ii-v78.2-local"


@pytest.mark.parametrize(
    "markup,code",
    [
        ("<script>alert(1)</script>", "HTML_TAG_PROHIBITED"),
        ('<p onclick="x()">Text</p>', "HTML_ATTRIBUTE_PROHIBITED"),
        ('<p onload="x()">Text</p>', "HTML_ATTRIBUTE_PROHIBITED"),
        ('<body background="x.jpg">Text</body>', "HTML_ATTRIBUTE_PROHIBITED"),
        ('<meta http-equiv="refresh" content="0;url=https://evil.example">', "HTML_ATTRIBUTE_PROHIBITED"),
        ('<a href="#x" target="_blank">Text</a>', "HTML_ATTRIBUTE_PROHIBITED"),
        ("<table><tr><td><table><tr><td>x</td></tr></table></td></tr></table>", "HTML_NESTED_TABLE"),
        ("<table><tbody><tr><td>x</td></tr></tbody></table>", "HTML_TAG_PROHIBITED"),
        ("<svg></svg>", "HTML_TAG_PROHIBITED"),
        ('<iframe src="x"></iframe>', "HTML_TAG_PROHIBITED"),
        ("<!DOCTYPE html><p>x</p>", "HTML_DECLARATION_UNSUPPORTED"),
        ('<p id="a" ID="b">x</p>', "HTML_DUPLICATE_ATTRIBUTE"),
        ('<font face="Arial">x</font>', "HTML_ATTRIBUTE_UNLISTED"),
        ('<p class="x">Text</p>', "ATTRIBUTE_SCOPE_UNVERIFIED"),
        ('<p style="margin:0">Text</p>', "CSS_PERMISSION_UNVERIFIED"),
        ('<p style="background:url(https://evil.example/x)">Text</p>', "CSS_ACTIVE_OR_COMPLEX"),
        ('<p style="width:expression(alert(1))">Text</p>', "CSS_ACTIVE_OR_COMPLEX"),
        ('<p style="display:none">Text</p>', "CSS_VALUE_OUTSIDE_PROFILE"),
        ('<p style="position:absolute">Text</p>', "CSS_PROPERTY_OUTSIDE_PROFILE"),
        ('<p style="color:red;color:blue">Text</p>', "CSS_DUPLICATE_PROPERTY"),
        ('<img src="data:image/jpeg;base64,YQ==">', "IMAGE_REFERENCE_INVALID"),
        ('<img src="https://example.com/image.jpg">', "IMAGE_REFERENCE_INVALID"),
        ('<img src="../image.jpg">', "IMAGE_REFERENCE_INVALID"),
        ('<img src="image.jpg">', "IMAGE_MISSING"),
        ("<img>", "IMAGE_SOURCE_REQUIRED"),
        ('<a href="javascript:alert(1)">Text</a>', "HYPERLINK_EXTERNAL_PROHIBITED"),
        (
            '<a href="https://www.sec.gov.evil/Archives/edgar/data/1/x.htm">Text</a>',
            "HYPERLINK_EXTERNAL_PROHIBITED",
        ),
        ('<a href="//evil.example/x">Text</a>', "HYPERLINK_EXTERNAL_PROHIBITED"),
        (
            '<a href="https://www.sec.gov/Archives/edgar/data/../x.htm">Text</a>',
            "HYPERLINK_EXTERNAL_PROHIBITED",
        ),
        ('<a href="https://www.sec.gov/%41rchives/edgar/data/1/x.htm">Text</a>', "HYPERLINK_INVALID"),
        ('<a href="#absent">Text</a>', "HYPERLINK_FRAGMENT_MISSING"),
        ('<a name="note"></a><a name="note"></a>', "BOOKMARK_DUPLICATE"),
        ('<a href="other.htm">Text</a>', "HYPERLINK_OUTSIDE_PACKAGE_PROFILE"),
        ("<r>Redlined</r>", "REDLINE_CONTEXT_REQUIRED"),
        ("<xmp>Text</xmp>", "HTML_TAG_OUTSIDE_PRODUCT_PROFILE"),
        (b"<p>caf\xe9</p>", "HTML_RAW_EXTENDED_BYTES"),
        ("<p>&#149;</p>", "ENTITY_LEGACY_REMAP"),
        ("<p>&#0;</p>", "ENTITY_MAPPING_UNVERIFIED"),
        ("<p>&#8364;</p>", "ENTITY_MAPPING_UNVERIFIED"),
        ("<p>&unknown;</p>", "ENTITY_UNKNOWN"),
        ("<p>&pound</p>", "ENTITY_TERMINATOR_REQUIRED"),
        ("", "HTML_PARSE_FAILED"),
        ("<html><body>A</body></html><html><body>B</body></html>", "HTML_MULTIPLE_DOCUMENTS"),
        ("<p><font>A</font><font>B</font><font>C</font><font>D</font></p>", "HTML_REDUNDANT_WORD_FORMATTING"),
    ],
)
def test_invalid_or_uncertain_actual_bytes_fail(tmp_path, markup, code):
    result = check(tmp_path, markup)
    assert not result.passed and not result.strict_passed
    assert code in codes(result)
    assert all(d.description and d.file and d.section and d.remediation for d in result.diagnostics)


def test_valid_sec_link_and_optional_table_end_tags_are_not_blanket_rejected(tmp_path):
    result = check(
        tmp_path,
        '<p><a href="https://www.sec.gov/Archives/edgar/data/1/x.htm">SEC</a></p><table><tr><td>A<td>B<tr><td>C<td>D</table>',
    )
    assert result.passed


@pytest.mark.parametrize("kind", ["JPEG", "GIF"])
def test_real_images_are_decoded_and_references_exact(tmp_path, kind):
    path = tmp_path / ("image.jpg" if kind == "JPEG" else "image.gif")
    Image.new("RGB", (8, 6), (10, 80, 150)).save(path, format=kind)
    result = check(tmp_path, f'<p>Disclosure</p><img src="{path.name}">', assets=[path])
    assert result.passed and result.files[1].format == kind
    assert result.files[1].width == 8 and result.files[1].height == 6
    result = check(tmp_path, "<p>Disclosure</p>", assets=[path])
    assert not result.passed and "ASSET_UNUSED" in codes(result)


@pytest.mark.parametrize("kind", ["corrupt", "png", "case", "outside"])
def test_bad_or_unresolved_asset_manifest(tmp_path, kind):
    path = tmp_path / "image.jpg"
    if kind == "corrupt":
        path.write_bytes(b"not an image")
    elif kind == "png":
        Image.new("RGB", (4, 4)).save(path, format="PNG")
    else:
        Image.new("RGB", (4, 4)).save(path, format="JPEG")
    if kind == "outside":
        outside = tmp_path / "other"
        outside.mkdir()
        path.rename(outside / path.name)
        path = outside / path.name
    result = check(
        tmp_path, '<img src="Image.jpg">' if kind == "case" else '<img src="image.jpg">', assets=[path]
    )
    assert not result.passed
    assert codes(result) & {
        "IMAGE_CORRUPT_OR_LIMIT",
        "IMAGE_FORMAT_INVALID",
        "IMAGE_MISSING",
        "ASSET_PATH_INVALID",
    }


@pytest.mark.parametrize("name", ["a" * 29 + ".htm", "bad name.htm", "_bad.htm", "filing.html"])
def test_filename_rules(tmp_path, name):
    assert "FILENAME_INVALID" in codes(check(tmp_path, "<p>Disclosure</p>", name=name))


@pytest.mark.parametrize(
    "policy",
    [
        ValidationPolicy(max_html_bytes=1),
        ValidationPolicy(max_nodes=1),
        ValidationPolicy(max_depth=1),
        ValidationPolicy(max_attributes=1),
        ValidationPolicy(max_diagnostics=2),
        ValidationPolicy(max_total_bytes=1),
    ],
)
def test_limits_do_not_return_success(tmp_path, policy):
    result = check(tmp_path, '<p style="position:absolute" onclick="x()"><b>Text</b></p>', policy=policy)
    assert not result.passed


@pytest.mark.parametrize(
    "form,size,passes",
    [
        ("S-1", 200_000_001, False),
        ("NPORT-P", 600_000_000, True),
        ("NPORT-P", 600_000_001, False),
        ("10-D/ABS-EE", 800_000_000, False),
        ("S-1", 1, False),
    ],
)
def test_whole_encoded_submission_context(tmp_path, form, size, passes):
    result = check(
        tmp_path, "<p>Filing</p>", submission=SubmissionContext(form_type=form, encoded_submission_bytes=size)
    )
    assert result.strict_passed is passes


def test_cancellation_is_not_validation_success(tmp_path):
    path = tmp_path / "filing.htm"
    path.write_text("<p>Text</p>")
    with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
        validate_files(path, context=ProcessingContext(cancelled=lambda: True))


@pytest.mark.parametrize(
    "source", ["<!--><script>alert(1)</script>", "<!-- unclosed", "<!-- --!><script>alert(1)</script>"]
)
def test_ambiguous_comments_cannot_hide_source_markup(tmp_path, source):
    result = check(tmp_path, source)
    assert not result.passed and "HTML_COMMENT_AMBIGUOUS" in codes(result)


def test_abs15g_actual_html_size_not_zip_size(tmp_path):
    result = check(
        tmp_path,
        "<p>" + ("a" * 25_000_000) + "</p>",
        submission=SubmissionContext(form_type="ABS-15G", encoded_submission_bytes=30_000_000),
        policy=ValidationPolicy(max_html_bytes=30_000_000),
    )
    assert not result.passed and "HTML_FORM_SIZE_LIMIT" in codes(result)


def test_modification_during_validation_invalidates_hash_evidence(tmp_path, monkeypatch):
    from converter.sec_validation.validator import Checks

    original = Checks.references

    def change(self, *args):
        original(self, *args)
        self.htm.write_bytes(b"<p>Changed after scan</p>")

    monkeypatch.setattr(Checks, "references", change)
    result = check(tmp_path, "<p>Original</p>")
    assert not result.passed and "VALIDATED_FILE_CHANGED" in codes(result)
