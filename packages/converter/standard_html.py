"""Modern HTML5 rendering of a verified shared layout and native SVG paint scopes."""

from __future__ import annotations

import base64
import hashlib
import re
from io import BytesIO

import pymupdf
from lxml import etree, html
from PIL import Image

from converter.context import ProcessingContext
from converter.errors import fail
from converter.layout.models import DocumentLayout
from converter.ooxml import sha256
from converter.pdf_export.validation import PDFValidationPolicy, _open
from converter.sec_validation.validator import read_bounded

SVG = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"
TAGS = {
    "svg",
    "defs",
    "g",
    "path",
    "text",
    "tspan",
    "image",
    "use",
    "clipPath",
    "mask",
    "linearGradient",
    "radialGradient",
    "stop",
    "pattern",
    "symbol",
    "filter",
    "feColorMatrix",
    "feComposite",
}
FONT_ALIASES = {
    "Helvetica": "Arial",
    "Helvetica-Bold": "Arial",
    "Helvetica-Oblique": "Arial",
    "Times-Roman": "Times New Roman",
    "TimesNewRomanPS": "Times New Roman",
    "TimesNewRomanPSMT": "Times New Roman",
    "ArialMT": "Arial",
    "Courier": "Courier New",
}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _text(page):
    return "".join(span.text for block in page.text_blocks for line in block.lines for span in line.spans)


def _restore_spaces(svg, page):
    """Restore only PDF extractor-marked synthetic spaces at their source positions.

    Native SVG omits TJ-gap spaces. Explicit x/y lists keep every real glyph fixed.
    """
    nodes = list(svg.iter(f"{{{SVG}}}tspan"))
    actual = [(node, index, char) for node in nodes for index, char in enumerate(node.text or "")]
    expected = [
        char
        for block in page.text_blocks
        for line in block.lines
        for span in line.spans
        for char in span.characters
    ]
    inserts, cursor = {}, 0
    for char in expected:
        if char.synthetic and char.text.isspace() and len(char.text) == 1 and actual:
            node, index, _ = (
                actual[cursor] if cursor < len(actual) else (actual[-1][0], len(actual[-1][0].text), None)
            )
            inserts.setdefault(node, {}).setdefault(index, []).append(char)
        elif cursor < len(actual) and char.text == actual[cursor][2]:
            cursor += 1
        else:
            return 0
    if cursor != len(actual) or not inserts:
        return 0
    modifications = []
    for node, indices in inserts.items():
        text = node.text or ""
        xs = [float(value) for value in node.get("x", "").replace(",", " ").split()]
        ys = [float(value) for value in node.get("y", "").replace(",", " ").split()]
        if len(xs) != len(text) or len(ys) not in {1, len(text)}:
            return 0
        if len(ys) == 1:
            ys *= len(text)
        matrix = pymupdf.Matrix(1, 0, 0, 1, 0, 0)
        for ancestor in (node, *node.iterancestors()):
            transform = ancestor.get("transform")
            if transform:
                match = re.fullmatch(r"matrix\(([^)]+)\)", transform)
                if not match:
                    return 0
                matrix *= pymupdf.Matrix([float(value) for value in match[1].replace(",", " ").split()])
        if abs(matrix.a * matrix.d - matrix.b * matrix.c) < 1e-12:
            return 0
        out_text, out_x, out_y = [], [], []
        for index in range(len(text) + 1):
            for char in indices.get(index, []):
                position = (
                    pymupdf.Point(char.origin)
                    * pymupdf.Matrix(page.geometry.page_to_display_matrix)
                    * ~matrix
                )
                out_text.append(char.text)
                out_x.append(position.x)
                out_y.append(position.y)
            if index < len(text):
                out_text.append(text[index])
                out_x.append(xs[index])
                out_y.append(ys[index])
        modifications.append((node, "".join(out_text), out_x, out_y))
    for node, text, xs, ys in modifications:
        node.text = text
        node.set("x", " ".join(format(value, ".12g") for value in xs))
        node.set("y", " ".join(format(value, ".12g") for value in ys))
    return sum(len(chars) for indices in inserts.values() for chars in indices.values())


def render_standard(
    source_pdf,
    layout,
    resources,
    directory,
    original_filename,
    context=None,
    max_html_bytes=32 * 1024 * 1024,
    max_asset_bytes=32 * 1024 * 1024,
    max_total_bytes=128 * 1024 * 1024,
):
    context = context or ProcessingContext()
    layout = DocumentLayout.model_validate(layout.model_dump())
    context.check()
    if (
        layout.mode != "authoritative_pdf"
        or not layout.verification
        or sha256(source_pdf) != layout.source_pdf_sha256
    ):
        raise fail(
            "STANDARD_SOURCE_REQUIRED",
            "generating_htm",
            "Standard HTML requires the current verified authoritative PDF model",
            "Re-analyze the unchanged input",
        )
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    # Recheck captured private image bytes; never trust mutable filenames or manifests alone.
    captured = {}
    for asset in layout.assets:
        for item in (asset.original, asset.mask):
            if item:
                path = resources / item.filename
                if path.is_symlink():
                    raise fail(
                        "STANDARD_ASSET_CHANGED",
                        "generating_htm",
                        "Private image resource is linked",
                        "Regenerate the analysis",
                    )
                data = read_bounded(path, max_asset_bytes)
                if len(data) != item.bytes or _digest(data) != item.sha256:
                    raise fail(
                        "STANDARD_ASSET_CHANGED",
                        "generating_htm",
                        "Private image resource changed",
                        "Regenerate the analysis",
                    )
                captured[item.sha256] = data
    root = etree.Element("html", lang="en")
    head = etree.SubElement(root, "head")
    etree.SubElement(head, "meta", charset="utf-8")
    etree.SubElement(head, "meta", name="viewport", content="width=device-width, initial-scale=1")
    etree.SubElement(
        head,
        "meta",
        attrib={
            "http-equiv": "Content-Security-Policy",
            "content": "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; font-src 'none'; script-src 'none'; base-uri 'none'; form-action 'none'",
        },
    )
    etree.SubElement(head, "title").text = original_filename
    style = etree.SubElement(head, "style")
    css = [
        "html,body{margin:0;padding:0}body{background:#e5e7eb}main{width:max-content;margin:auto}.page{position:relative;overflow:hidden;background:white;break-after:page}.page>svg{display:block;width:100%;height:100%}text,tspan{white-space:pre;font-kerning:none;font-variant-ligatures:none} @media screen{.page{margin:16px auto;box-shadow:0 1px 8px #0002}} @media print{body{background:white}main{width:auto;margin:0}.page{margin:0;box-shadow:none}.page:last-child{break-after:auto}}"
    ]
    body = etree.SubElement(root, "body")
    main = etree.SubElement(body, "main", attrib={"aria-label": "Converted document"})
    assets, payloads, fonts, page_reports = {}, {}, set(), []
    total = 0
    with _open(source_pdf, PDFValidationPolicy(require_reference=False)) as document:
        if document.page_count != len(layout.pages):
            raise fail(
                "STANDARD_SOURCE_CHANGED",
                "generating_htm",
                "Source page count changed",
                "Re-analyze the input",
            )
        for native, page in zip(document, layout.pages, strict=True):
            context.check()
            if page.annotations:
                raise fail(
                    "STANDARD_ANNOTATION_UNSUPPORTED",
                    "generating_htm",
                    "Annotation appearances are not verified for HTML rendering",
                    "Export a static PDF with authorized annotations flattened",
                    page=page.page_number,
                )
            raw = native.get_svg_image(text_as_path=False).encode("utf-8")
            if len(raw) > max_html_bytes or b"<!DOCTYPE" in raw:
                raise fail(
                    "STANDARD_SVG_LIMIT",
                    "generating_htm",
                    "Native page SVG exceeds safe limits",
                    "Review page complexity",
                )
            svg = etree.fromstring(
                raw, etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
            )
            if etree.QName(svg).namespace != SVG or svg.tag != f"{{{SVG}}}svg":
                raise fail(
                    "STANDARD_SVG_INVALID",
                    "generating_htm",
                    "Native SVG root is invalid",
                    "Review the document",
                )
            text = "".join("".join(node.itertext()) for node in svg.iter(f"{{{SVG}}}text"))
            expected = _text(page)
            restored = _restore_spaces(svg, page) if text != expected else 0
            if restored:
                text = "".join("".join(node.itertext()) for node in svg.iter(f"{{{SVG}}}text"))
            if text != expected:
                raise fail(
                    "STANDARD_TEXT_MISMATCH",
                    "generating_htm",
                    "SVG text differs from the verified character ledger",
                    "Resolve source text mapping before rendering",
                    page=page.page_number,
                )
            width = page.geometry.display_bounds[2] - page.geometry.display_bounds[0]
            height = page.geometry.display_bounds[3] - page.geometry.display_bounds[1]
            viewbox = tuple(float(value) for value in svg.get("viewBox", "").split())
            if len(viewbox) != 4 or any(
                abs(a - b) > 0.01 for a, b in zip(viewbox, (0, 0, width, height), strict=True)
            ):
                raise fail(
                    "STANDARD_GEOMETRY_MISMATCH",
                    "generating_htm",
                    "Native SVG page geometry differs from the model",
                    "Re-analyze page geometry",
                )
            prefix = f"p{page.page_number:04d}_"
            identifiers = {node.get("id") for node in svg.iter() if node.get("id")}
            for node in svg.iter():
                if etree.QName(node).namespace != SVG or etree.QName(node).localname not in TAGS:
                    raise fail(
                        "STANDARD_SVG_UNSUPPORTED",
                        "generating_htm",
                        "Unsupported native SVG element",
                        "Add verified support before conversion",
                    )
                for name, value in list(node.attrib.items()):
                    local = etree.QName(name).localname.lower()
                    if local.startswith("on") or any(
                        token in value.lower()
                        for token in ("javascript:", "@import", "expression(", "-moz-binding")
                    ):
                        raise fail(
                            "STANDARD_SVG_UNSAFE",
                            "generating_htm",
                            "Unsafe SVG attribute",
                            "Use a static document",
                        )
                    if local == "id":
                        node.set(name, prefix + value)
                    elif local == "href":
                        if value.startswith("#"):
                            if value[1:] not in identifiers:
                                raise fail(
                                    "STANDARD_REFERENCE_INVALID",
                                    "generating_htm",
                                    "SVG fragment is unresolved",
                                    "Review native paint references",
                                )
                            node.set(name, "#" + prefix + value[1:])
                        elif node.tag == f"{{{SVG}}}image" and value.startswith("data:image/"):
                            header, encoded = value.split(",", 1)
                            if not header.lower().endswith(";base64"):
                                raise ValueError("Unsupported image encoding")
                            data = base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
                            if not data or len(data) > max_asset_bytes:
                                raise fail(
                                    "STANDARD_ASSET_LIMIT",
                                    "generating_htm",
                                    "SVG image exceeds safe size",
                                    "Review embedded images",
                                )
                            digest = _digest(data)
                            # Preserve exact native JPEG/PNG bytes when already captured.
                            data = captured.get(digest, data)
                            with Image.open(BytesIO(data)) as image:
                                if image.width * image.height > 16_000_000:
                                    raise ValueError("Image pixel limit")
                                extension = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}.get(
                                    image.format
                                )
                                image.verify()
                            if not extension:
                                raise fail(
                                    "STANDARD_ASSET_FORMAT",
                                    "generating_htm",
                                    "Native SVG image format is not supported by this renderer",
                                    "Normalize the source graphic",
                                )
                            if digest not in payloads:
                                filename = f"image{len(payloads) + 1:04d}.{extension}"
                                total += len(data)
                                if total > max_total_bytes:
                                    raise fail(
                                        "STANDARD_ASSET_LIMIT",
                                        "generating_htm",
                                        "Total image bytes exceed safe limits",
                                        "Review document graphics",
                                    )
                                (directory / filename).write_bytes(data)
                                payloads[digest] = filename
                                assets[filename] = {"sha256": digest, "bytes": len(data)}
                            node.set(name, payloads[digest])
                        else:
                            raise fail(
                                "STANDARD_REFERENCE_UNSAFE",
                                "generating_htm",
                                "Nonlocal SVG reference is not allowed",
                                "Use local static assets",
                            )
                    else:
                        if "url(" in value.lower():
                            for target in re.findall(r"url\(([^)]+)\)", value, re.I):
                                if not target.startswith("#") or target[1:] not in identifiers:
                                    raise fail(
                                        "STANDARD_REFERENCE_UNSAFE",
                                        "generating_htm",
                                        "Nonlocal or unresolved SVG paint reference",
                                        "Review native paint references",
                                    )
                            node.set(
                                name,
                                re.sub(
                                    r"url\(#([^)]+)\)",
                                    lambda m, prefix=prefix: "url(#" + prefix + m[1] + ")",
                                    value,
                                ),
                            )
                        if local == "font-family":
                            family = re.sub(r"^[A-Z]{6}\+", "", value)
                            family = FONT_ALIASES.get(family, family)
                            family = re.sub(r"[^A-Za-z0-9 _-]", "", family) or "serif"
                            node.set(name, family)
                            fonts.add(family)
            svg.set("aria-label", f"Page {page.page_number}")
            css.append(
                f".page-{page.page_number}{{width:{width:g}pt;height:{height:g}pt;page:sheet{page.page_number}}}@page sheet{page.page_number}{{size:{width:g}pt {height:g}pt;margin:0}}"
            )
            section = etree.SubElement(
                main,
                "section",
                attrib={"class": f"page page-{page.page_number}", "data-page": str(page.page_number)},
            )
            section.append(svg)
            page_reports.append(
                {
                    "page": page.page_number,
                    "width_pt": width,
                    "height_pt": height,
                    "characters": len(text),
                    "text_sha256": _digest(text.encode()),
                    "synthetic_spaces_restored": restored,
                }
            )
    context.check()
    style.text = "\n".join(css)
    data = etree.tostring(root, method="html", encoding="utf-8", doctype="<!DOCTYPE html>")
    if len(data) > max_html_bytes or sha256(source_pdf) != layout.source_pdf_sha256:
        raise fail(
            "STANDARD_OUTPUT_INVALID",
            "generating_htm",
            "HTML exceeds limits or source changed",
            "Review the document",
        )
    parsed = html.fromstring(data)
    if parsed.xpath("//script|//iframe|//object|//link|//base"):
        raise ValueError("Unexpected active HTML")
    references = {
        value
        for node in parsed.iter()
        for key, value in node.attrib.items()
        if key in {"href", "xlink:href"} and not value.startswith("#")
    }
    if references != set(assets):
        raise fail(
            "STANDARD_ASSET_MANIFEST",
            "generating_htm",
            "Generated local asset references are inconsistent",
            "Regenerate output",
        )
    filename = "document.html"
    (directory / filename).write_bytes(data)
    return {
        "method": "verified-layout-native-svg-html5-v1",
        "generated": True,
        "filename": filename,
        "sha256": _digest(data),
        "bytes": len(data),
        "source_pdf_sha256": layout.source_pdf_sha256,
        "assets": assets,
        "pages": page_reports,
        "characters": sum(page["characters"] for page in page_reports),
        "fonts": sorted(fonts),
        "font_embedding": False,
        "pixel_equivalence_verified": False,
        "diagnostics": [
            {
                "code": "STANDARD_LOCAL_FONTS",
                "severity": "warning",
                "stage": "generating_htm",
                "description": "Text uses local fonts with aliases; embedded PDF fonts are not redistributed. Browser substitutions may change appearance.",
            }
        ],
    }
