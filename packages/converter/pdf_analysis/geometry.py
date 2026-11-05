from __future__ import annotations

import math

import pymupdf


def box(value) -> tuple[float, float, float, float]:
    result = tuple(float(v) for v in value)
    if (
        len(result) != 4
        or not all(math.isfinite(v) for v in result)
        or result[0] > result[2]
        or result[1] > result[3]
    ):
        raise ValueError("Invalid PDF rectangle")
    return result


def point(value) -> tuple[float, float]:
    result = tuple(float(v) for v in value)
    if len(result) != 2 or not all(math.isfinite(v) for v in result):
        raise ValueError("Invalid PDF point")
    return result


def union(boxes):
    if not boxes:
        return None
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def center(bbox):
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def contains(bbox, xy, tolerance=0.0):
    return (
        bbox[0] - tolerance <= xy[0] <= bbox[2] + tolerance
        and bbox[1] - tolerance <= xy[1] <= bbox[3] + tolerance
    )


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def visibility(bbox, bounds):
    if all(contains(bounds, xy) for xy in ((bbox[0], bbox[1]), (bbox[2], bbox[3]))):
        return "inside"
    return "partial" if overlaps(bbox, bounds) else "outside"


def quad_points(value):
    quad = pymupdf.Quad(value)
    return tuple(point(p) for p in (quad.ul, quad.ur, quad.ll, quad.lr))
