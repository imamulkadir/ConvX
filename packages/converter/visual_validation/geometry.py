from __future__ import annotations

import hashlib
import re

import pymupdf

from converter.pdf_analysis.graphics import json_value


def page_geometry(page, policy):
    chars = []
    line_count = 0
    raw = page.get_text(
        "rawdict",
        flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES,
        clip=pymupdf.INFINITE_RECT(),
        sort=False,
    )
    for block in raw["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            line_count += 1
            for span in line["spans"]:
                font = re.sub(r"^[A-Z]{6}\+", "", span["font"])
                for c in span["chars"]:
                    chars.append(
                        {
                            "text": c["c"],
                            "origin": tuple(c["origin"]),
                            "bbox": tuple(c["bbox"]),
                            "font": font,
                            "size": span["size"],
                            "flags": span["flags"],
                            "color": span["color"],
                            "alpha": span.get("alpha", 255),
                            "direction": tuple(line["dir"]),
                        }
                    )
    image_metadata = page.get_image_info(hashes=False, xrefs=False)
    if sum(i["width"] * i["height"] for i in image_metadata) > policy.max_page_pixels:
        raise ValueError("PDF decoded image budget")
    images = page.get_image_info(hashes=True, xrefs=True)
    image_signatures = [
        (tuple(i["bbox"]), tuple(i["transform"]), i["width"], i["height"], i.get("digest", b"").hex())
        for i in images
    ]
    vectors = []
    for path in page.get_drawings(extended=True):
        vectors.append({k: json_value(v) for k, v in sorted(path.items()) if k not in {"seqno", "layer"}})
    fonts = []
    for font in page.get_fonts(full=True):
        if font[0]:
            data = page.parent.extract_font(font[0])[3]
            if data:
                fonts.append((re.sub(r"^[A-Z]{6}\+", "", font[3]), hashlib.sha256(data).hexdigest()))
    paints = [
        (
            s["type"],
            tuple(s["bbox"]),
            s["opacity"],
            tuple(s["color"]) if isinstance(s["color"], (list, tuple)) else s["color"],
        )
        for s in page.get_texttrace()
    ]
    return {
        "chars": chars,
        "text": "".join(c["text"] for c in chars),
        "lines": line_count,
        "images": image_signatures,
        "vectors": vectors,
        "font_programs": sorted(set(fonts)),
        "paints": paints,
        "width_pt": page.rect.width,
        "height_pt": page.rect.height,
        "rotation": page.rotation,
    }


def compare_geometry(source, actual, tolerance, limit):
    content = source["text"] == actual["text"]
    segmentation = [c["text"] for c in source["chars"]] == [c["text"] for c in actual["chars"]]
    counts = {
        "origin_mismatches": 0,
        "bbox_mismatches": 0,
        "font_substitutions": 0,
        "font_size_mismatches": 0,
        "emphasis_mismatches": 0,
        "color_mismatches": 0,
    }
    boxes = []
    mismatching = 0
    maximum_origin = 0.0
    maximum_box = 0.0
    if content and segmentation:
        for index, (a, b) in enumerate(zip(source["chars"], actual["chars"], strict=True)):
            od = max(abs(x - y) for x, y in zip(a["origin"], b["origin"], strict=True))
            bd = max(abs(x - y) for x, y in zip(a["bbox"], b["bbox"], strict=True))
            maximum_origin = max(maximum_origin, od)
            maximum_box = max(maximum_box, bd)
            checks = {
                "origin_mismatches": od > tolerance,
                "bbox_mismatches": bd > tolerance,
                "font_substitutions": a["font"] != b["font"],
                "font_size_mismatches": abs(a["size"] - b["size"]) > tolerance,
                "emphasis_mismatches": (a["flags"] & 18) != (b["flags"] & 18),
                "color_mismatches": a["color"] != b["color"]
                or a["alpha"] != b["alpha"]
                or a["direction"] != b["direction"],
            }
            for key, value in checks.items():
                counts[key] += int(value)
            if any(checks.values()) and len(boxes) < limit:
                boxes.append({"character_index": index, "source_bbox": a["bbox"], "rendered_bbox": b["bbox"]})
            mismatching += int(any(checks.values()))
    image_equal = source["images"] == actual["images"]
    vector_equal = source["vectors"] == actual["vectors"]
    paint_equal = source["paints"] == actual["paints"]
    dimensions = (
        abs(source["width_pt"] - actual["width_pt"]) <= tolerance
        and abs(source["height_pt"] - actual["height_pt"]) <= tolerance
        and source["rotation"] == actual["rotation"]
    )
    return {
        "content_equal": content,
        "glyph_segmentation_equal": segmentation,
        "text_alignment_available": content and segmentation,
        "geometry_difference_records_truncated": mismatching > len(boxes),
        "font_resource_sets_equal": {c["font"] for c in source["chars"]}
        == {c["font"] for c in actual["chars"]},
        "font_size_sets_equal": {round(c["size"], 3) for c in source["chars"]}
        == {round(c["size"], 3) for c in actual["chars"]},
        "source_characters": len(source["chars"]),
        "rendered_characters": len(actual["chars"]),
        "source_text_sha256": hashlib.sha256(source["text"].encode()).hexdigest(),
        "rendered_text_sha256": hashlib.sha256(actual["text"].encode()).hexdigest(),
        "dimensions_equal": dimensions,
        "source_lines": source["lines"],
        "rendered_lines": actual["lines"],
        "max_origin_error_pt": maximum_origin,
        "max_bbox_error_pt": maximum_box,
        **counts,
        "image_geometry_pixels_equal": image_equal,
        "vector_geometry_paint_equal": vector_equal,
        "text_paint_equal": paint_equal,
        "embedded_font_programs_equal": source["font_programs"] == actual["font_programs"],
        "geometry_equal": content
        and segmentation
        and dimensions
        and not any(counts.values())
        and image_equal
        and vector_equal
        and paint_equal,
        "differences": boxes,
    }
