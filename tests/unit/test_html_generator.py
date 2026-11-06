import hashlib
import json
from types import SimpleNamespace

import pymupdf
import pytest
from conftest import ROOT
from converter.context import ProcessingContext
from converter.errors import ConversionFailure
from converter.html_generator.generator import generate_htm, zero_width_ligature_backstep
from converter.html_generator.models import GenerationPolicy
from converter.pdf_analysis.extract import analyze_pdf, inspect_pdf
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_export.validation import validate_pdf
from layout_fixtures import merged_table_pdf, simple_pdf
from lxml import html
from PIL import Image


@pytest.mark.parametrize(
    "change,expected",
    [
        ({}, True),
        ({"glyph_ids": [15]}, False),
        ({"synthetic": True}, False),
        ({"bbox": (190.317, 100, 191, 112)}, False),
        ({"origin": (191, 110)}, False),
        ({"origin": (190.317, 111)}, False),
        ({"origin": (190.295, 110)}, False),
    ],
)
def test_ligature_exception_requires_native_zero_width_tiny_backstep(change, expected):
    # Actual LibreOffice Calibri-Italic f/i continuation coordinates from Stage9.
    span = SimpleNamespace(id="italic-run")
    char = SimpleNamespace(
        **{
            "synthetic": False,
            "glyph_ids": [],
            "bbox": (190.317, 100, 190.317, 112),
            "origin": (190.317, 110),
            **change,
        }
    )
    following = SimpleNamespace(origin=(190.295, 110))
    assert zero_width_ligature_backstep(span, char, span, following) is expected
    assert not zero_width_ligature_backstep(span, char, SimpleNamespace(id="other-run"), following)


def generate(path, output=None, policy=None):
    # A real test PDF compared to itself tests generator mechanics, not Word equivalence.
    proof = validate_pdf(path, path)
    layout = analyze_pdf(path, proof, AnalysisPolicy(detect_borderless_candidates=False))
    output = output or path.parent / "candidate.htm"
    result = generate_htm(layout, path, proof, output, policy)
    tree = html.parse(str(output)) if result.generated else None
    return result, tree, layout, proof


def disclosure(tree):
    return "".join(tree.find("body").itertext())


def test_real_selectable_text_typography_and_deterministic_bytes(tmp_path):
    path = simple_pdf(tmp_path / "source.pdf", text='Hello  <world> & "filing"')
    before = path.read_bytes()
    result, tree, layout, proof = generate(path)
    assert disclosure(tree) == 'Hello  <world> & "filing"'
    assert result.content_integrity_passed and not result.strict_validation_passed
    assert not result.sec_compliance_passed and not result.visual_fidelity_passed
    assert result.candidate_sha256 == hashlib.sha256((tmp_path / "candidate.htm").read_bytes()).hexdigest()
    assert all(
        "font-size:12pt" in e.get("style") and "color:#ff0000" in e.get("style")
        for e in tree.findall(".//font")
    )
    assert all(
        c.text in disclosure(tree)
        for p in layout.pages
        for b in p.text_blocks
        for line in b.lines
        for s in line.spans
        for c in s.characters
    )
    second = tmp_path / "second"
    second.mkdir()
    generate_htm(layout, path, proof, second / "candidate.htm")
    assert (second / "candidate.htm").read_bytes() == (tmp_path / "candidate.htm").read_bytes()
    assert path.read_bytes() == before
    assert not tree.findall(".//img")


def test_permitted_tag_construction_without_positioned_or_active_content(tmp_path):
    result, tree, _, _ = generate(simple_pdf(tmp_path / "source.pdf"))
    assert result.generated
    assert {e.tag for e in tree.iter()} <= {
        "html",
        "head",
        "title",
        "body",
        "div",
        "p",
        "font",
        "a",
        "b",
        "i",
        "u",
        "sup",
        "sub",
        "table",
        "tr",
        "td",
        "img",
    }
    assert b"<!DOCTYPE" not in (tmp_path / "candidate.htm").read_bytes()
    assert not tree.xpath("//table//table")
    for e in tree.iter():
        assert not any(name.startswith("on") for name in e.attrib)
        assert not any(
            token in e.get("style", "") for token in ("position:", "transform:", "url(", "overflow:hidden")
        )
    assert {d.code for d in result.diagnostics} >= {
        "HTM_STYLE_PROFILE_PENDING",
        "HTM_FONT_METRICS_UNVERIFIED",
    }
    registry = json.loads((ROOT / "docs/compliance/efm-v78.rules.json").read_text(encoding="utf-8"))
    permitted = {
        tag
        for rule in registry["rules"]
        if rule["id"] in {"EFM78-DOCUMENT-TAGS", "EFM78-BODY-TAGS"}
        for tag in rule["tags"]
    }
    assert {e.tag for e in tree.iter()} <= permitted


def test_inspection_cannot_be_promoted_to_html(tmp_path):
    path = simple_pdf(tmp_path / "source.pdf")
    with pytest.raises(ConversionFailure, match="HTM_LAYOUT_GATE_REQUIRED"):
        generate_htm(inspect_pdf(path), path, validate_pdf(path, path), tmp_path / "candidate.htm")
    assert not (tmp_path / "candidate.htm").exists()


@pytest.mark.parametrize("change", ["failed", "stale", "layout_proof"])
def test_failed_or_stale_proof_never_generates(tmp_path, change):
    path = simple_pdf(tmp_path / "source.pdf")
    proof = validate_pdf(path, path)
    layout = analyze_pdf(path, proof)
    if change == "failed":
        proof["passed"] = False
    elif change == "stale":
        path.write_bytes(simple_pdf(tmp_path / "other.pdf", text="Changed").read_bytes())
    else:
        layout = layout.model_copy(update={"validation_report_sha256": "0" * 64})
    with pytest.raises(ConversionFailure):
        generate_htm(layout, path, proof, tmp_path / "candidate.htm")
    assert not (tmp_path / "candidate.htm").exists()


@pytest.mark.parametrize("kind", ["columns", "scripts", "merged_table", "rules", "pages"])
def test_native_layout_features_keep_every_character(tmp_path, kind):
    path = tmp_path / "source.pdf"
    if kind == "merged_table":
        merged_table_pdf(path)
    elif kind == "pages":
        simple_pdf(path, pages=3)
    else:
        with pymupdf.open() as document:
            page = document.new_page(width=400, height=600)
            if kind == "columns":
                for x, y, text in [
                    (240, 60, "Right first"),
                    (40, 60, "Left first"),
                    (240, 120, "Right next"),
                    (40, 120, "Left next"),
                ]:
                    page.insert_text((x, y), text)
            elif kind == "scripts":
                page.insert_text((40, 160), "Bold ", fontname="hebo", fontsize=12)
                page.insert_text((70, 160), "Italic ", fontname="heit", fontsize=12)
                page.insert_text((40, 80), "x", fontsize=12)
                page.insert_text((46, 76), "2", fontsize=8)
                page.insert_text((51, 80), "H", fontsize=12)
                page.insert_text((60, 83), "2", fontsize=8)
                page.insert_text((64, 80), "O", fontsize=12)
            else:
                page.insert_text((40, 60), "Underlined")
                page.draw_line((40, 62), (95, 62), width=0.5)
                page.draw_line((40, 140), (200, 140), color=(1, 0, 0), width=2)
            document.save(path)
    result, tree, layout, _ = generate(path)
    assert result.generated, result.diagnostics
    text = "".join(
        s.text for p in layout.pages for b in p.text_blocks for line in b.lines for s in line.spans
    )
    assert sorted(disclosure(tree)) == sorted(text)
    assert result.character_count == len(text) and result.content_integrity_passed
    assert not tree.xpath("//table//table")
    if kind == "merged_table":
        assert len(tree.findall(".//table")) == 1
        assert any(c.get("colspan") == "2" for c in tree.findall(".//td"))
        assert any("border-top" in c.get("style", "") for c in tree.findall(".//td"))
    elif kind == "scripts":
        assert (
            tree.findall(".//sup")
            and tree.findall(".//sub")
            and tree.findall(".//b")
            and tree.findall(".//i")
        )
    elif kind == "pages":
        assert len(tree.xpath("//a[starts-with(@name,'page')]")) == 3
    elif kind == "columns":
        assert "inline-block" in (tmp_path / "candidate.htm").read_text()


def test_native_image_requests_do_not_rasterize_disclosure(tmp_path):
    image = tmp_path / "graphic.png"
    Image.new("RGB", (20, 10), (20, 80, 150)).save(image)
    path = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text((40, 60), "Searchable disclosure")
        xref = page.insert_image(pymupdf.Rect(40, 100, 140, 150), filename=str(image))
        page.insert_image(pymupdf.Rect(40, 200, 140, 250), xref=xref)
        document.save(path)
    result, tree, _, _ = generate(path)
    assert result.generated and disclosure(tree) == "Searchable disclosure"
    assert len(result.asset_requests) == 1 and len(result.asset_requests[0].placement_ids) == 2
    assert [e.get("src") for e in tree.findall(".//img")] == ["image001.jpg", "image001.jpg"]
    assert not (tmp_path / "image001.jpg").exists()
    assert any(d.code == "HTM_ASSETS_PENDING" for d in result.diagnostics)


@pytest.mark.parametrize(
    "uri,allowed",
    [
        ("https://www.sec.gov/Archives/edgar/data/1/test.htm", True),
        ("javascript:alert(1)", False),
        ("https://example.com/test", False),
        ("https://www.sec.gov.evil/Archives/edgar/data/1/test.htm", False),
        ("https://www.sec.gov/Archives/edgar/data/../x.htm", False),
    ],
)
def test_hyperlinks_preserved_or_explicitly_blocked(tmp_path, uri, allowed):
    path = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((40, 60), "Filing link")
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(39, 45, 100, 65), "uri": uri})
        document.save(path)
    result, tree, _, _ = generate(path)
    assert result.generated is allowed
    if allowed:
        assert {a.get("href") for a in tree.findall(".//a") if a.get("href")} == {uri}
    else:
        assert any(d.code == "HTM_LINK_UNSUPPORTED" for d in result.diagnostics)


@pytest.mark.parametrize(
    "feature,code",
    [
        ("vertical", "HTM_TEXT_ROTATION_UNSUPPORTED"),
        ("page_rotation", "HTM_PAGE_ROTATION_UNSUPPORTED"),
        ("curve", "HTM_VECTOR_UNSUPPORTED"),
        ("overlap", "HTM_FLOW_OVERLAP_UNSUPPORTED"),
        ("transparency", "HTM_TEXT_PAINT_UNSUPPORTED"),
    ],
)
def test_unsupported_features_fail_without_partial_htm(tmp_path, feature, code):
    path = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=600)
        page.insert_text(
            (40, 100),
            "Disclosure",
            rotate=90 if feature == "vertical" else 0,
            fill_opacity=0.5 if feature == "transparency" else 1,
        )
        if feature == "page_rotation":
            page.set_rotation(90)
        elif feature == "overlap":
            page.insert_text((41, 100), "Collision")
        elif feature == "curve":
            page.draw_bezier((40, 200), (60, 180), (100, 220), (130, 200))
        document.save(path)
    result, tree, _, _ = generate(path)
    assert not result.generated and tree is None and not result.content_integrity_passed
    assert code in {d.code for d in result.diagnostics}
    assert not (tmp_path / "candidate.htm").exists()


@pytest.mark.parametrize(
    "policy",
    [
        GenerationPolicy(max_characters=1),
        GenerationPolicy(max_items_per_page=1),
        GenerationPolicy(max_partition_work=1),
        GenerationPolicy(max_html_bytes=10),
        GenerationPolicy(max_nodes=1),
    ],
)
def test_generation_budgets_fail_without_publishing(tmp_path, policy):
    path = simple_pdf(tmp_path / "source.pdf", pages=1)
    if policy.max_items_per_page == 1 or policy.max_partition_work == 1:
        with pymupdf.open(path) as document:
            document[0].insert_text((50, 200), "Second line")
            document.save(tmp_path / "two.pdf")
        path = tmp_path / "two.pdf"
    with pytest.raises(ConversionFailure):
        generate(path, policy=policy)
    assert not (tmp_path / "candidate.htm").exists()


def test_cancellation_output_safety_and_existing_file_preserved(tmp_path):
    path = simple_pdf(tmp_path / "source.pdf")
    proof = validate_pdf(path, path)
    layout = analyze_pdf(path, proof)
    with pytest.raises(ConversionFailure, match="PROCESSING_CANCELLED"):
        generate_htm(
            layout, path, proof, tmp_path / "candidate.htm", context=ProcessingContext(cancelled=lambda: True)
        )
    output = tmp_path / "candidate.htm"
    output.write_bytes(b"existing")
    with pytest.raises(ConversionFailure, match="HTM_OUTPUT_INVALID"):
        generate_htm(layout, path, proof, output)
    assert output.read_bytes() == b"existing"
    assert not list(tmp_path.glob("*.part"))


def test_internal_links_resolve_to_unique_emitted_bookmarks(tmp_path):
    path = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        document.new_page()
        document.new_page()
        document[0].insert_text((40, 60), "Next page")
        document[1].insert_text((40, 60), "Destination")
        document[0].insert_link(
            {
                "kind": pymupdf.LINK_GOTO,
                "from": pymupdf.Rect(39, 45, 110, 65),
                "page": 1,
                "to": pymupdf.Point(40, 60),
            }
        )
        document.save(path)
    result, tree, _, _ = generate(path)
    assert result.generated
    names = [a.get("name") for a in tree.findall(".//a") if a.get("name")]
    assert len(names) == len(set(names))
    assert all(a.get("href")[1:] in names for a in tree.findall(".//a") if a.get("href"))
    assert "HTM_LINK_DESTINATION_APPROXIMATE" in {d.code for d in result.diagnostics}


def test_unicode_is_preserved_in_ascii_references_without_claiming_approval(tmp_path):
    result, tree, _, _ = generate(simple_pdf(tmp_path / "source.pdf", text="Caf\u00e9"))
    assert disclosure(tree) == "Caf\u00e9" and (tmp_path / "candidate.htm").read_bytes().isascii()
    assert "HTM_CHARACTER_MAPPING_PENDING" in {d.code for d in result.diagnostics}


@pytest.mark.parametrize("kind,code", [("links", "HTM_LINK_WORK_LIMIT"), ("table", "HTM_TABLE_WORK_LIMIT")])
def test_association_work_is_bounded(tmp_path, kind, code):
    path = tmp_path / "source.pdf"
    if kind == "table":
        merged_table_pdf(path)
    else:
        simple_pdf(path)
        with pymupdf.open(path) as document:
            document[0].insert_link(
                {
                    "kind": pymupdf.LINK_URI,
                    "from": pymupdf.Rect(49, 85, 125, 105),
                    "uri": "https://www.sec.gov/Archives/edgar/data/1/test.htm",
                }
            )
            document.save(tmp_path / "links.pdf")
        path = tmp_path / "links.pdf"
    with pytest.raises(ConversionFailure, match=code):
        generate(path, policy=GenerationPolicy(max_partition_work=1))
    assert not (tmp_path / "candidate.htm").exists()


def test_memory_budget_stops_before_output(tmp_path, monkeypatch):
    path = simple_pdf(tmp_path / "source.pdf")
    proof = validate_pdf(path, path)
    layout = analyze_pdf(path, proof)
    monkeypatch.setattr(
        "converter.html_generator.generator.psutil.Process",
        lambda: SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=2 * 1024**3)),
    )
    with pytest.raises(ConversionFailure, match="HTM_MEMORY_LIMIT"):
        generate_htm(layout, path, proof, tmp_path / "candidate.htm")
    assert not (tmp_path / "candidate.htm").exists()


def test_exclusive_publication_preserves_concurrent_output(tmp_path, monkeypatch):
    import os

    path = simple_pdf(tmp_path / "source.pdf")
    proof = validate_pdf(path, path)
    layout = analyze_pdf(path, proof)
    link = os.link

    def race(source, destination):
        destination.write_bytes(b"concurrent creator")
        return link(source, destination)

    monkeypatch.setattr("converter.html_generator.generator.os.link", race)
    with pytest.raises(FileExistsError):
        generate_htm(layout, path, proof, tmp_path / "candidate.htm")
    assert (tmp_path / "candidate.htm").read_bytes() == b"concurrent creator"
    assert not list(tmp_path.glob("*.part"))
