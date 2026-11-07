"""Optional non-overlapping CSS2 page separators in vacant bottom margins."""

import pymupdf
from lxml import etree

from converter.edgar_reflow import axis, vertical_plan
from converter.html_generator.flow import pt
from converter.html_generator.models import GenerationDiagnostic


def add_dividers(root, source, layered, context):
    warnings = []
    frames = root.xpath("/html/body/div")
    with pymupdf.open(source) as document:
        for index, (page, frame) in enumerate(zip(document, frames, strict=True)):
            context.check()
            if index == len(frames) - 1:
                continue
            plan = vertical_plan(page) if layered else {"chunks": []}
            divider = divider_geometry(page, plan)
            if divider is None:
                warnings.append(
                    GenerationDiagnostic(
                        code="EDGAR_PAGE_DIVIDER_NO_SPACE",
                        severity="warning",
                        page=index + 1,
                        description="This page has no vacant bottom margin for a separator without covering source content",
                        remediation="Review the source page margin; disclosure and graphics take priority",
                    )
                )
                continue
            width = page.rect.width
            # Flow-v1 children consume height; layered children reserve none.
            # A transparent zero-height wrapper gives both an unchanged origin
            # and leaves the divider anchored to the page rather than the last
            # paragraph's flow position. Actual print checks verify this.
            content = etree.Element("div", style="height:0;margin:0;padding:0;font-size:0;line-height:0")
            content.text, frame.text = frame.text, None
            for child in list(frame):
                content.append(child)
            frame.append(content)
            etree.SubElement(frame, "a", name=f"pagebreak{index + 1}")
            outer = etree.SubElement(
                frame, "div", style="height:0;margin:0;padding:0;font-size:0;line-height:0"
            )
            band = etree.SubElement(
                outer,
                "div",
                style=f"display:inline-block;vertical-align:top;margin:{pt(divider['top'])} 0 0 0;padding:0;width:{pt(width)};height:{pt(divider['height'])};font-size:0;line-height:0",
            )
            etree.SubElement(
                band,
                "div",
                style=f"margin:0;padding:0;width:{pt(width - 2 * divider['border'])};height:{pt(divider['dark'])};border:{pt(divider['border'])} solid #d3d3d3;background-color:#808080",
            )
    return warnings


def divider_geometry(page, reflow):
    raw = page.get_text("dict", flags=0)
    shift = reflow.get("content_offset_y", 0)
    bottoms = [
        line["bbox"][3] + shift
        for block in raw["blocks"]
        if block["type"] == 0
        for line in block["lines"]
        if axis(line["dir"]) == "horizontal"
    ]
    bottoms.extend(c["top"] + c["height"] for c in reflow["chunks"])
    bottoms.extend(image["bbox"][3] + shift for image in page.get_image_info())
    for drawing in page.get_drawings():
        fill, stroke = drawing.get("fill"), drawing.get("color")
        if (fill is not None and fill != (1, 1, 1)) or (stroke is not None and stroke != (1, 1, 1)):
            bottoms.append(drawing["rect"].y1 + (drawing.get("width") or 0) / 2 + shift)
    # Match 13px gray borders / 6px dark center where space permits. Shorter
    # margins get a thinner frame, never a moved footer or obscured image/text.
    available = page.rect.height - max(bottoms, default=0) - 1
    height = min(24, available)
    if height < 2:
        return None
    dark = min(4.5, height / 2)
    border = (height - dark) / 2
    return {"top": page.rect.height - height, "height": height, "dark": dark, "border": border}
