"""Four actual bounded runtime paths with independently verified saved ZIPs."""

import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pymupdf
import pytest
from converter.context import ProcessingContext
from converter.html_generator.generator import Builder
from converter.html_generator.models import GenerationPolicy
from converter.layout.models import DocumentLayout
from converter.ooxml import sha256
from lxml import etree
from PIL import Image

from tools.verify_download import verify_saved_download

ROOT = Path(__file__).resolve().parents[2]


def independent_docx(path):
    document = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Independent quarterly statement</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Final price: </w:t></w:r><w:del w:id="1" w:author="Regression"><w:r><w:delText>999.99</w:delText></w:r></w:del><w:ins w:id="2" w:author="Regression"><w:r><w:t>123.45</w:t></w:r></w:ins></w:p>
<w:p><w:r><w:rPr><w:i/></w:rPr><w:t>Preserved disclosure and financial figures.</w:t></w:r></w:p>
<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>
</w:body></w:document>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr("word/document.xml", document)


def independent_pdf(path):
    image = BytesIO()
    Image.new("RGB", (12, 9), (30, 120, 220)).save(image, format="JPEG", quality=95)
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=600)
        page.insert_text((40, 45), "Independent assets report", fontsize=12)
        for y in (80, 120, 160):
            page.draw_line((40, y), (240, y))
        for x in (40, 140, 240):
            page.draw_line((x, 80), (x, 160))
        for x, y, text in [(50, 105, "Asset"), (150, 105, "Price"), (50, 145, "Bond"), (150, 145, "123.45")]:
            page.insert_text((x, y), text, fontsize=10)
        page.insert_image(pymupdf.Rect(40, 200, 120, 260), stream=image.getvalue())
        doc.save(path)


@pytest.mark.parametrize("kind", ["docx", "pdf"])
@pytest.mark.parametrize("mode", ["standard", "edgar"])
def test_bounded_runtime_four_path_source_zip_matrix(tmp_path, kind, mode):
    source = tmp_path / ("source." + kind)
    (independent_docx if kind == "docx" else independent_pdf)(source)
    before = sha256(source)
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps({"original_filename": "independent quarterly report." + kind, "mode": mode}),
        encoding="utf-8",
    )
    result = subprocess.run(  # noqa: S603 - fixed trusted runtime, private test files
        [sys.executable, "-m", "converter.runtime", str(request)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "packages")},
        timeout=350,
        capture_output=True,
    )
    report = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert result.returncode == 0, report["diagnostics"]
    assert report["status"] == "packaged" and report["mode"] == mode
    assert sha256(source) == before and report["source_unchanged"]
    summary = verify_saved_download(tmp_path / "attempt001/package/result.zip", tmp_path)
    assert summary["source_text_verified"] and summary["crc_verified"]
    assert summary["download_filename"] == "independent quarterly report.zip"
    assert not summary["sec_acceptance_confirmed"]
    if kind == "docx":
        revisions = report["revision_acceptance"]
        assert revisions["before"]["total"] == 2 and revisions["after"]["total"] == 0
        with ZipFile(tmp_path / "attempt001/accepted.docx") as accepted:
            xml = etree.fromstring(accepted.read("word/document.xml"))
            text = "".join(xml.itertext())
            assert "123.45" in text and "999.99" not in text
        assert len(summary["members"]) == 1
        if mode == "edgar":
            layout = DocumentLayout.model_validate_json(
                (tmp_path / "attempt001/layout.json").read_text(encoding="utf-8")
            )
            legacy = Builder(layout, GenerationPolicy(), ProcessingContext())
            legacy.prepare()
            assert any(d.code == "HTM_TEXT_ADVANCE_UNSUPPORTED" for d in legacy.diagnostics)
            assert any(d["code"] == "HTM_ZERO_WIDTH_LIGATURE" for d in report["diagnostics"])
        else:
            corrupted = tmp_path / "corrupted.zip"
            corrupted.write_bytes((tmp_path / "attempt001/package/result.zip").read_bytes()[:-1])
            with pytest.raises(AssertionError):
                verify_saved_download(corrupted, tmp_path)
    else:
        assert report["revision_acceptance"] is None and report["provider"] is None
        assert report["layout_analysis"]["tables"] > 0
        assert len(summary["members"]) == 2
    (tmp_path / "matrix-evidence.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
