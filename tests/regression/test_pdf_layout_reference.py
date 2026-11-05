"""Inspect the real Word-saved reference without authorizing reconstruction."""

import hashlib

import pymupdf
from conftest import ROOT
from converter.ooxml import sha256
from converter.pdf_analysis.extract import inspect_pdf


def test_all_23_reference_pages_retain_native_character_ledger():
    path = ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf"
    before = sha256(path)
    layout = inspect_pdf(path)
    assert len(layout.pages) == 23
    assert not layout.reconstruction_eligible and layout.validation_report_sha256 is None
    assert len(layout.fonts) == 13 and len(layout.assets) == 4
    assert sum(p.character_count for p in layout.pages) == 85798
    assert sum(len(p.images) for p in layout.pages) == 5
    with pymupdf.open(path) as document:
        for native, extracted in zip(document, layout.pages, strict=True):
            raw = native.get_text(
                "rawdict",
                flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES,
                clip=pymupdf.INFINITE_RECT(),
                sort=False,
            )
            text = "".join(
                c["c"]
                for b in raw["blocks"]
                if b["type"] == 0
                for line in b["lines"]
                for span in line["spans"]
                for c in span["chars"]
            )
            assert extracted.character_count == len(text)
            assert extracted.character_sha256 == hashlib.sha256(text.encode()).hexdigest()
            assert len(extracted.vectors) == len(native.get_drawings(extended=True))
            assert len(extracted.images) == len(native.get_image_info(xrefs=True))
    assert sha256(path) == before == layout.source_pdf_sha256
