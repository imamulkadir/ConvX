"""Whitespace partitioning into normal-flow rows/columns, never positioned text."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from converter.errors import fail
from converter.pdf_analysis.geometry import union


def number(value):
    return format(float(value), ".12g")


def pt(value):
    return number(value) + "pt"


@dataclass(frozen=True)
class Flow:
    bbox: tuple
    axis: int | None = None
    children: tuple = ()
    item: object | None = None


class Partitioner:
    def __init__(self, policy, context):
        self.policy, self.context, self.work = policy, context, 0

    def build(self, items, depth=0):
        self.context.check()
        self.work += len(items)
        if self.work > self.policy.max_partition_work:
            raise fail(
                "HTM_WORK_LIMIT",
                "generating_htm",
                "Flow partition budget exceeded",
                "Review bounded generation limits",
            )
        if not items:
            return None
        if len(items) == 1:
            return Flow(items[0].bbox, item=items[0])
        if depth > 64:
            return None
        # Match the extraction graph: independent columns, then page-wide bands.
        for axis in (0, 1):
            ordered = sorted(items, key=lambda i: (i.bbox[axis], i.bbox[axis + 2], i.id))
            groups, current, end = [], [], float("-inf")
            for item in ordered:
                if current and item.bbox[axis] >= end:
                    groups.append(current)
                    current = []
                current.append(item)
                end = max(end, item.bbox[axis + 2]) if len(current) > 1 else item.bbox[axis + 2]
            groups.append(current)
            if len(groups) > 1:
                children = tuple(self.build(g, depth + 1) for g in groups)
                if all(c is not None for c in children):
                    return Flow(union([i.bbox for i in items]), axis, children)
        return None


def emit_flow(tree, parent, render_leaf):
    """Fixed source extents reserve space without clipping disclosure text."""
    if tree.item is not None:
        render_leaf(tree.item, parent)
        return
    cursor = tree.bbox[tree.axis]
    for child in tree.children:
        x0, y0, x1, y1 = child.bbox
        if tree.axis == 1:
            style = f"margin:0;width:{pt(x1 - x0)};height:{pt(y1 - y0)};padding:{pt(y0 - cursor)} 0 0 {pt(x0 - tree.bbox[0])}"
        else:
            style = f"display:inline-block;vertical-align:top;margin:{pt(y0 - tree.bbox[1])} 0 0 {pt(x0 - cursor)};width:{pt(x1 - x0)};height:{pt(y1 - y0)};padding:0"
        container = etree.SubElement(parent, "div", style=style)
        emit_flow(child, container, render_leaf)
        cursor = child.bbox[tree.axis + 2]
