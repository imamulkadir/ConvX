import io

import pymupdf
import pytest
from converter.assets.normalize import normalize_assets
from converter.errors import ConversionFailure
from converter.html_generator.generator import generate_htm
from converter.pdf_analysis.extract import analyze_pdf
from converter.pdf_analysis.policy import AnalysisPolicy
from converter.pdf_export.validation import validate_pdf
from converter.sec_validation.validator import validate_files
from lxml import html
from PIL import Image


def fixture(tmp_path, kind):
    if kind == "jpeg":
        im = Image.new("RGB", (8, 6), (20, 80, 150))
        format = "JPEG"
    elif kind == "alpha":
        im = Image.new("RGBA", (8, 6), (20, 80, 150, 128))
        format = "PNG"
    else:
        im = Image.new("RGB", (32, 32))
        im.putdata([(x * 8, y * 8, (x + y) * 4) for y in range(32) for x in range(32)])
        format = "PNG"
    stream = io.BytesIO()
    im.save(stream, format=format)
    path = tmp_path / "source.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((40, 60), "Selectable disclosure")
        xref = page.insert_image(pymupdf.Rect(40, 100, 140, 200), stream=stream.getvalue())
        page.insert_image(pymupdf.Rect(40, 250, 140, 350), xref=xref)
        document.save(path)
    proof = validate_pdf(path, path)
    layout = analyze_pdf(path, proof, AnalysisPolicy(detect_borderless_candidates=False))
    candidate = tmp_path / "candidate.htm"
    generation = generate_htm(layout, path, proof, candidate)
    assert generation.generated, generation.diagnostics
    return path, candidate, generation, stream.getvalue()


@pytest.mark.parametrize("kind", ["jpeg", "alpha", "gradient"])
def test_real_graphics_normalize_without_disclosure_rasterization(tmp_path, kind):
    path, candidate, generation, original = fixture(tmp_path, kind)
    before = candidate.read_bytes()
    report = normalize_assets(path, candidate, generation, tmp_path / "filing")
    root = tmp_path / "filing"
    image = report["images"][0]
    assert len(report["images"]) == 1 and not report["strict_fidelity_passed"]
    with Image.open(root / image["filename"]) as decoded:
        assert decoded.size == ((8, 6) if kind != "gradient" else (32, 32))
    parsed = html.parse(str(root / "candidate.htm"))
    assert "".join(parsed.find("body").itertext()) == "Selectable disclosure"
    assert [e.get("src") for e in parsed.findall(".//img")] == [image["filename"]] * 2
    assert set(p.name for p in root.iterdir()) == {"candidate.htm", image["filename"]}
    assert candidate.read_bytes() == before
    validation = validate_files(root / "candidate.htm", (root / image["filename"],))
    assert not validation.passed  # unresolved STYLE/MANY is reported, not waived by normalization
    assert not any(d.code.startswith("IMAGE_") for d in validation.diagnostics)
    if kind == "jpeg":
        assert image["original_jpeg_preserved"]
        assert (root / image["filename"]).read_bytes() == original
    elif kind == "alpha":
        assert (
            image["format"] == "GIF" and image["decoded_pixels_exact"] and image["alpha_composited_on_white"]
        )
    else:
        assert image["format"] == "JPEG" and not image["original_jpeg_preserved"]


@pytest.mark.parametrize("mutation", ["candidate", "pdf", "request", "mask"])
def test_stale_or_corrupt_graphic_requests_fail(tmp_path, mutation):
    path, candidate, generation, _ = fixture(tmp_path, "alpha")
    if mutation == "candidate":
        candidate.write_bytes(b"<p>Changed</p>")
    elif mutation == "pdf":
        path.write_bytes(b"changed")
    elif mutation == "request":
        generation = generation.model_copy(update={"asset_requests": ()})
    else:
        request = generation.asset_requests[0].model_copy(update={"soft_mask_xref": None})
        generation = generation.model_copy(update={"asset_requests": (request,)})
    with pytest.raises(ConversionFailure):
        normalize_assets(path, candidate, generation, tmp_path / "filing")
    assert not (tmp_path / "filing/candidate.htm").exists()


def test_decode_budget_is_checked_before_graphic_output(tmp_path):
    path, candidate, generation, _ = fixture(tmp_path, "jpeg")
    with pytest.raises(ConversionFailure, match="ASSET_PIXEL_LIMIT"):
        normalize_assets(path, candidate, generation, tmp_path / "filing", max_pixels=1)
    assert not list((tmp_path / "filing").glob("image*"))
