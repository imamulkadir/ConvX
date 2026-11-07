"""Associate native SVG paint scopes with shared PDF characters and images.

SVG is inspection-only here. No SVG enters EDGAR output. Rectangular clipping is
associated with its actual paint and retained in literal CSS2 overflow boxes.
"""

import re

import pymupdf
from lxml import etree

from converter.standard_html import SVG, _restore_spaces


def matrix(node):
    value = node.get("transform")
    if not value:
        return pymupdf.Matrix(1, 0, 0, 1, 0, 0)
    match = re.fullmatch(r"matrix\(([^)]+)\)", value)
    if not match:
        raise ValueError("Unsupported native transform")
    values = [float(x) for x in match[1].replace(",", " ").split()]
    if len(values) != 6:
        raise ValueError("Invalid native transform")
    return pymupdf.Matrix(values)


def rectangle(node):
    """Strict native rectangular path; no curve/compound approximation."""
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[Ee][-+]?\d+)?", node.get("d", ""))
    points, i, x, y = [], 0, 0.0, 0.0
    while i < len(tokens):
        command = tokens[i]
        i += 1
        if command in {"M", "L"}:
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
        elif command == "H":
            x = float(tokens[i])
            i += 1
        elif command == "V":
            y = float(tokens[i])
            i += 1
        elif command == "Z" and i == len(tokens):
            break
        else:
            raise ValueError("Nonrectangular native clipping")
        points.append((x, y))
    if len(points) != 4 or tokens[-1] != "Z":
        raise ValueError("Compound or open native clipping")
    xs, ys = sorted({p[0] for p in points}), sorted({p[1] for p in points})
    if len(xs) != 2 or len(ys) != 2 or set(points) != {(a, b) for a in xs for b in ys}:
        raise ValueError("Nonrectangular native clipping")
    if any(a[0] != b[0] and a[1] != b[1] for a, b in zip(points, points[1:] + points[:1], strict=True)):
        raise ValueError("Crossed native clipping")
    transform = matrix(node)
    if transform.b or transform.c:
        raise ValueError("Rotated clipping is unsupported")
    return tuple(pymupdf.Rect(xs[0], ys[0], xs[1], ys[1]) * transform)


def inside(rect, bounds, tolerance=0.05):
    return (
        bounds[0] >= rect[0] - tolerance
        and bounds[1] >= rect[1] - tolerance
        and bounds[2] <= rect[2] + tolerance
        and bounds[3] <= rect[3] + tolerance
    )


def inspect_clips(native_page, page, context):
    """Return source-bound proof or fail for clipped text/images requiring loss."""
    tree = etree.fromstring(
        native_page.get_svg_image(text_as_path=False).encode(),
        parser=etree.XMLParser(resolve_entities=False, no_network=True),
    )
    if sum(1 for _ in tree.iter()) > 200000:
        raise ValueError("Native paint complexity exceeds budget")
    _restore_spaces(tree, page)
    clips = {}
    for node in tree.iter(f"{{{SVG}}}clipPath"):
        if len(node) != 1 or node[0].tag != f"{{{SVG}}}path":
            raise ValueError("Unsupported native clipping definition")
        clips[node.get("id")] = rectangle(node[0])

    scope_cache = {}

    def scopes(node):
        if node in scope_cache:
            return scope_cache[node]
        result = []
        for ancestor in (node, *node.iterancestors()):
            value = ancestor.get("clip-path")
            if value:
                match = re.fullmatch(r"url\(#([^)]*)\)", value)
                if not match or match[1] not in clips:
                    raise ValueError("Unresolved native clipping scope")
                transform = pymupdf.Matrix(1, 0, 0, 1, 0, 0)
                for parent in (ancestor, *ancestor.iterancestors()):
                    transform *= matrix(parent)
                result.append(tuple(pymupdf.Rect(clips[match[1]]) * transform))
        scope_cache[node] = result
        return result

    expected = [c for b in page.text_blocks for line in b.lines for s in line.spans for c in s.characters]
    actual = [(node, i, ch) for node in tree.iter(f"{{{SVG}}}tspan") for i, ch in enumerate(node.text or "")]
    if "".join(c.text for c in expected) != "".join(c for _, _, c in actual):
        raise ValueError("Native clipping text ledger mismatch")
    associations = {}
    position_cache = {}
    for index, ((node, i, _), char) in enumerate(zip(actual, expected, strict=True)):
        if index % 256 == 0:
            context.check()
        if node not in position_cache:
            xs = [float(v) for v in node.get("x", "").replace(",", " ").split()]
            ys = [float(v) for v in node.get("y", "").replace(",", " ").split()]
            if len(xs) != len(node.text or "") or len(ys) not in {1, len(xs)}:
                raise ValueError("Unresolved native glyph positions")
            if len(ys) == 1:
                ys *= len(xs)
            transform = pymupdf.Matrix(1, 0, 0, 1, 0, 0)
            for ancestor in (node, *node.iterancestors()):
                transform *= matrix(ancestor)
            position_cache[node] = [pymupdf.Point(x, y) * transform for x, y in zip(xs, ys, strict=True)]
        native_origin = position_cache[node][i]
        if abs(native_origin.x - char.origin[0]) > 0.05 or abs(native_origin.y - char.origin[1]) > 0.05:
            raise ValueError("Native clip glyph origin differs from shared source")
        bounds = pymupdf.Rect(page.geometry.unrotated_bounds)
        for rect in scopes(node):
            bounds &= pymupdf.Rect(rect)
        associations[char.id] = tuple(bounds)
    images = [
        n
        for n in tree.iter(f"{{{SVG}}}image")
        if not any(a.tag in {f"{{{SVG}}}mask", f"{{{SVG}}}defs"} for a in n.iterancestors())
    ]
    if len(images) != len(page.images):
        raise ValueError("Native clipping image count mismatch")
    for node, image in zip(images, page.images, strict=True):
        transform = pymupdf.Matrix(1, 0, 0, 1, 0, 0)
        for ancestor in (node, *node.iterancestors()):
            transform *= matrix(ancestor)
        bounds = tuple(pymupdf.Rect(0, 0, float(node.get("width")), float(node.get("height"))) * transform)
        if any(abs(a - b) > 0.05 for a, b in zip(bounds, image.bbox, strict=True)):
            raise ValueError("Native clipping image association mismatch")
        bounds = pymupdf.Rect(page.geometry.unrotated_bounds)
        for rect in scopes(node):
            bounds &= pymupdf.Rect(rect)
        associations[image.id] = tuple(bounds)
    # Native paint order associates drawing nodes with the already verified paths.
    painted = [
        n
        for n in tree.iter(f"{{{SVG}}}path")
        if not any(a.tag in {f"{{{SVG}}}clipPath", f"{{{SVG}}}defs"} for a in n.iterancestors())
    ]
    vectors = [v for v in page.vectors if v.kind not in {"clip", "group"}]
    if len(painted) != len(vectors):
        raise ValueError("Native vector clipping association mismatch")
    for node, vector in zip(painted, vectors, strict=True):
        bounds = pymupdf.Rect(page.geometry.unrotated_bounds)
        for rect in scopes(node):
            bounds &= pymupdf.Rect(rect)
        associations[vector.id] = tuple(bounds)
    return associations
