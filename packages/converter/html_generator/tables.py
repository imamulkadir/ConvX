from __future__ import annotations

from lxml import etree

from converter.html_generator.flow import pt
from converter.html_generator.typography import render_line


def rgb(value):
    if value is None or len(value) != 3:
        return None
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02x}" for c in value)


def path_edges(path):
    result = []
    for item in path.items:
        if item.command == "l":
            result.append(item.points)
        elif item.command == "re":
            x0, y0, x1, y1 = item.rect
            result += [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return result


def border_styles(cell, paths):
    x0, y0, x1, y1 = cell.bbox
    styles = []
    for side, axis, coordinate, lo, hi in (
        ("top", 1, y0, x0, x1),
        ("bottom", 1, y1, x0, x1),
        ("left", 0, x0, y0, y1),
        ("right", 0, x1, y0, y1),
    ):
        matches = []
        for path in paths:
            for a, b in path_edges(path):
                if (
                    abs(a[axis] - coordinate) <= 0.01
                    and abs(b[axis] - coordinate) <= 0.01
                    and min(a[1 - axis], b[1 - axis]) <= lo + 0.01
                    and max(a[1 - axis], b[1 - axis]) >= hi - 0.01
                ):
                    matches.append(path)
        if matches:
            path = matches[-1]
            styles.append(f"border-{side}:{pt(path.stroke_width_pt or 0)} solid {rgb(path.stroke_color)}")
    return styles


def render_table(table, page, parent, emitted, hrefs, anchors):
    element = etree.SubElement(
        parent,
        "table",
        border="0",
        cellpadding="0",
        cellspacing="0",
        style=f"border-collapse:collapse;table-layout:fixed;width:{pt(table.bbox[2] - table.bbox[0])};margin:0;padding:0",
    )
    paths = {p.id: p for p in page.vectors}
    lines = [line for block in page.text_blocks for line in block.lines]
    edges = sorted({v for c in table.cells for v in (c.bbox[1], c.bbox[3])})
    for row in range(table.rows):
        tr = etree.SubElement(element, "tr", style=f"height:{pt(edges[row + 1] - edges[row])}")
        for cell in sorted((c for c in table.cells if c.row == row), key=lambda c: c.column):
            style = [
                "padding:0",
                "vertical-align:top",
                "box-sizing:border-box",
                f"width:{pt(cell.bbox[2] - cell.bbox[0])}",
                f"height:{pt(cell.bbox[3] - cell.bbox[1])}",
            ]
            style += border_styles(cell, [paths[i] for i in cell.border_path_ids])
            td = etree.SubElement(
                tr,
                "td",
                rowspan=str(cell.row_span),
                colspan=str(cell.column_span),
                valign="top",
                style=";".join(style),
            )
            selected = set(cell.character_ids)
            selected_lines = [
                (line, [c for s in line.spans for c in s.characters if c.id in selected]) for line in lines
            ]
            cursor = cell.bbox[1]
            for line, chars in sorted(
                (pair for pair in selected_lines if pair[1]),
                key=lambda pair: (
                    min(c.bbox[1] for c in pair[1]),
                    min(c.origin[0] for c in pair[1]),
                    pair[0].id,
                ),
            ):
                render_line(line, td, emitted, hrefs, anchors, selected, offset=(cell.bbox[0], cursor))
                cursor = max(c.bbox[3] for c in chars)
