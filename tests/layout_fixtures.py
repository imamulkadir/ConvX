"""Small genuine PDFs with known geometry; no converter output is simulated."""

from io import BytesIO

import pymupdf
from PIL import Image


def simple_pdf(path, text="Hello  world", pages=1):
    with pymupdf.open() as document:
        for _index in range(pages):
            page = document.new_page(width=400, height=600)
            page.insert_text((50, 100), text, fontsize=12, color=(1, 0, 0))
        document.save(path)
    return path


def complex_pdf(path):
    image = BytesIO()
    Image.new("RGBA", (8, 6), (20, 150, 240, 128)).save(image, format="PNG")
    with pymupdf.open() as document:
        for number in range(1, 4):
            page = document.new_page(width=400, height=600)
            page.insert_text((40, 30), "Repeated report header", fontsize=10)
            page.insert_text((190, 580), f"S-{number}", fontsize=9)
            page.insert_text((40, 70), "Bold", fontname="hebo", fontsize=12)
            page.insert_text((110, 70), "Italic", fontname="heit", fontsize=9.5)
            width = pymupdf.get_text_length("Underlined", fontname="helv", fontsize=12)
            page.insert_text((40, 100), "Underlined", fontsize=12)
            page.draw_line((40, 101.5), (40 + width, 101.5), width=0.5)
            page.insert_text((360, 200), "Vertical disclosure", fontsize=10, rotate=90)
            for x in (40, 140, 240):
                page.draw_line((x, 160), (x, 240), color=(0, 0, 1), width=0.8)
            for y in (160, 200, 240):
                page.draw_line((40, y), (240, y), color=(0, 0, 1), width=0.8)
            for _i, (x, y, text) in enumerate(
                ((50, 185, "Asset"), (150, 185, "Price"), (50, 225, "Bond"), (150, 225, "100"))
            ):
                page.insert_text((x, y), text, fontsize=10)
            xref = page.insert_image(pymupdf.Rect(40, 270, 120, 330), stream=image.getvalue())
            page.insert_image(pymupdf.Rect(150, 270, 210, 350), xref=xref, rotate=90)
            shape = page.new_shape()
            shape.draw_bezier((50, 390), (100, 350), (130, 430), (200, 390))
            shape.finish(color=(0.2, 0.3, 0.4), fill=(0.8, 0.8, 0.8), width=1.25, fill_opacity=0.6)
            shape.commit()
            page.insert_link(
                {
                    "kind": pymupdf.LINK_URI,
                    "from": pymupdf.Rect(40, 60, 90, 74),
                    "uri": "https://www.sec.gov/Archives/edgar/data/1/test.htm",
                }
            )
        document.save(path)
    return path


def merged_table_pdf(path):
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=400)
        for y in (60, 100, 140):
            page.draw_line((40, y), (240, y))
        for x in (40, 240):
            page.draw_line((x, 60), (x, 140))
        page.draw_line((140, 100), (140, 140))
        page.insert_text((60, 85), "Merged heading", fontsize=10)
        page.insert_text((60, 125), "Left", fontsize=10)
        page.insert_text((160, 125), "Right", fontsize=10)
        document.save(path)
    return path
