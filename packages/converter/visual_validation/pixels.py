from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def compare_pixels(reference, actual, text_boxes=(), scale=1.0, structure_equal=False):
    if reference.size != actual.size:
        return (
            {
                "size_equal": False,
                "raw_difference_pixels": None,
                "antialias_candidate_pixels": 0,
                "explained_antialias_pixels": 0,
                "unexplained_difference_pixels": None,
                "mean_absolute_channel_error": None,
            },
            None,
            None,
        )
    a, b = np.asarray(reference.convert("RGB")), np.asarray(actual.convert("RGB"))
    delta = np.abs(a.astype(np.int16) - b.astype(np.int16))
    different = np.any(delta != 0, axis=2)
    neutral = (np.ptp(a, axis=2) <= 1) & (np.ptp(b, axis=2) <= 1)
    ga = a[:, :, 0]
    gb = b[:, :, 0]
    # No translation, blur, resizing, thresholding of disclosure or color normalization.
    core_equal = np.array_equal(ga < 16, gb < 16)
    la = Image.fromarray(ga)
    lb = Image.fromarray(gb)
    edge = (
        (np.asarray(la.filter(ImageFilter.MinFilter(3))) < 16)
        & (np.asarray(la.filter(ImageFilter.MaxFilter(3))) > 250)
        & (np.asarray(lb.filter(ImageFilter.MinFilter(3))) < 16)
        & (np.asarray(lb.filter(ImageFilter.MaxFilter(3))) > 250)
    )
    text = np.zeros(different.shape, dtype=bool)
    for x0, y0, x1, y1 in text_boxes:
        text[
            max(0, int(y0 * scale)) : min(text.shape[0], int(np.ceil(y1 * scale))),
            max(0, int(x0 * scale)) : min(text.shape[1], int(np.ceil(x1 * scale))),
        ] = True
    intermediate = ((ga > 0) & (ga < 255)) | ((gb > 0) & (gb < 255))
    candidates = different & neutral & edge & text & intermediate
    explained = candidates if structure_equal and core_equal else np.zeros_like(candidates)
    unresolved = different & ~explained
    heat = np.full(a.shape, 255, dtype=np.uint8)
    heat[explained] = (255, 180, 0)
    heat[unresolved] = (255, 0, 0)
    overlay = (a.astype(np.uint16) + b.astype(np.uint16)) // 2
    overlay[unresolved] = (255, 0, 0)
    return (
        {
            "size_equal": True,
            "raw_difference_pixels": int(different.sum()),
            "difference_fraction": float(different.mean()),
            "antialias_candidate_pixels": int(candidates.sum()),
            "explained_antialias_pixels": int(explained.sum()),
            "unexplained_difference_pixels": int(unresolved.sum()),
            "mean_absolute_channel_error": float(delta.mean()),
        },
        Image.fromarray(heat),
        Image.fromarray(overlay.astype(np.uint8)),
    )
