from __future__ import annotations

from converter.errors import fail
from converter.layout.models import ImageAsset, ImagePlacement, VectorPath, VectorPrimitive
from converter.pdf_analysis.geometry import box, point, quad_points


def json_value(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        return list(point(value))
    if hasattr(value, "x0"):
        return list(box(value))
    raise ValueError("Unsupported native drawing property")


def vectors(raw_paths, prefix, policy, guard):
    if len(raw_paths) > policy.max_vectors_per_page:
        raise fail(
            "PDF_ANALYSIS_LIMIT",
            "analyzing_pdf",
            "Vector path limit exceeded",
            "Review PDF complexity and analysis policy",
        )
    results, count = [], 0
    for index, path in enumerate(raw_paths):
        guard.check()
        primitives = []
        for item in path.get("items", []):
            count += 1
            if count > policy.max_primitives_per_page:
                raise fail(
                    "PDF_ANALYSIS_LIMIT",
                    "analyzing_pdf",
                    "Vector primitive limit exceeded",
                    "Review PDF complexity and analysis policy",
                )
            command = item[0]
            if command in {"l", "c"}:
                primitives.append(VectorPrimitive(command=command, points=tuple(point(p) for p in item[1:])))
            elif command == "re":
                primitives.append(
                    VectorPrimitive(command=command, rect=box(item[1]), orientation=int(item[2]))
                )
            elif command == "qu":
                primitives.append(VectorPrimitive(command=command, points=quad_points(item[1])))
            else:
                raise fail(
                    "PDF_VECTOR_UNSUPPORTED",
                    "analyzing_pdf",
                    "Unknown native vector operation",
                    "Preserve diagnostics and add supported extraction before reconstruction",
                )
        excluded = {"items", "type", "rect", "scissor", "seqno", "level", "color", "fill", "width"}
        results.append(
            VectorPath(
                id=f"{prefix}-v{index:05d}",
                kind=path["type"],
                bbox=box(path["rect"]) if path.get("rect") is not None else None,
                scissor=box(path["scissor"]) if path.get("scissor") is not None else None,
                level=int(path.get("level", 0)),
                paint_sequence=path.get("seqno"),
                items=tuple(primitives),
                stroke_color=path.get("color"),
                fill_color=path.get("fill"),
                stroke_width_pt=path.get("width"),
                properties={k: json_value(v) for k, v in sorted(path.items()) if k not in excluded},
            )
        )
    return tuple(results)


def images(page, document, prefix, policy, guard, assets, paint_order, has_nontrivial_clip):
    resources = page.get_images(full=True)
    infos = page.get_image_info(hashes=False, xrefs=False)
    if len(infos) > policy.max_images_per_page or len(resources) > policy.max_images_per_page:
        raise fail(
            "PDF_ANALYSIS_LIMIT",
            "analyzing_pdf",
            "Image count limit exceeded",
            "Review PDF image resources and analysis policy",
        )
    total = 0
    for width, height in [(r[2], r[3]) for r in resources] + [(i["width"], i["height"]) for i in infos]:
        pixels = width * height
        total += pixels
        if pixels > policy.max_image_pixels or total > policy.max_page_image_pixels:
            raise fail(
                "PDF_IMAGE_LIMIT",
                "analyzing_pdf",
                "Decoded image resource budget exceeded",
                "Use a bounded PDF image profile before extraction",
            )
    guard.check()
    # Metadata limits are checked before requesting native decoded-pixel identity hashes.
    infos = page.get_image_info(hashes=True, xrefs=True) if infos else []
    resource_map = {r[0]: r for r in resources}
    result = []
    for index, info in enumerate(infos):
        guard.check()
        xref = int(info.get("xref", 0))
        resource = resource_map.get(xref)
        asset_id = f"image-x{xref:08d}" if xref else f"{prefix}-inline{index:05d}"
        assets.setdefault(
            asset_id,
            ImageAsset(
                id=asset_id,
                xref=xref,
                soft_mask_xref=int(resource[1]) if resource and resource[1] else None,
                width_px=int(info["width"]),
                height_px=int(info["height"]),
                bits_per_component=int(info["bpc"]),
                color_space=str(info.get("cs-name", "unknown")),
                decoded_pixel_digest=info["digest"].hex() if info.get("digest") else None,
                digest_algorithm="mupdf-md5-nonsecurity-identity" if info.get("digest") else "not_available",
                inline=xref == 0,
            ),
        )
        matrix = tuple(float(v) for v in info["transform"])
        a, b, c, d, e, f = matrix
        bbox = box(info["bbox"])
        sequences = tuple(
            p.sequence
            for p in paint_order
            if p.kind == "fill-image" and all(abs(x - y) <= 0.01 for x, y in zip(p.bbox, bbox, strict=True))
        )
        result.append(
            ImagePlacement(
                id=f"{prefix}-i{index:05d}",
                asset_id=asset_id,
                native_number=info["number"],
                bbox=bbox,
                transform=matrix,
                quad=((e, f), (a + e, b + f), (c + e, d + f), (a + c + e, b + d + f)),
                paint_sequences=sequences,
                clipping="association_unresolved" if has_nontrivial_clip else "page_bounds_only",
            )
        )
    return tuple(result)
