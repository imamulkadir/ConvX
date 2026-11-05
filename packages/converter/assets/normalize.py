from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pymupdf
from lxml import html
from PIL import Image

from converter.context import ProcessingContext
from converter.errors import fail
from converter.html_generator.models import GenerationResult
from converter.ooxml import sha256
from converter.sec_validation.profile import valid_filename
from converter.sec_validation.validator import digest, read_bounded


def publish(path, data):
    temporary = path.with_name(path.name + ".part")
    try:
        with temporary.open("xb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def normalize_assets(
    source_pdf: Path,
    candidate: Path,
    generation: GenerationResult,
    output_root: Path,
    context: ProcessingContext | None = None,
    max_pixels=16_000_000,
    max_bytes=20 * 1024 * 1024,
    max_html_bytes=25 * 1024 * 1024,
    max_total_bytes=100 * 1024 * 1024,
    max_total_pixels=64_000_000,
    max_assets=1000,
):
    context = context or ProcessingContext()
    context.check()
    generation = GenerationResult.model_validate(generation.model_dump())
    raw = read_bounded(candidate, max_html_bytes)
    if (
        not generation.generated
        or not generation.content_integrity_passed
        or digest(raw) != generation.candidate_sha256
        or sha256(source_pdf) != generation.source_pdf_sha256
    ):
        raise fail(
            "ASSET_SOURCE_GATE_REQUIRED",
            "preparing_assets",
            "Graphics require unchanged generated HTM and its source PDF",
            "Revalidate the current attempt's immutable artifacts",
        )
    if (
        candidate.name != generation.candidate_filename
        or not valid_filename(candidate.name, (".htm",))
        or candidate.is_symlink()
        or output_root.exists()
        or output_root.is_symlink()
    ):
        raise fail(
            "ASSET_OUTPUT_INVALID",
            "preparing_assets",
            "Asset output must be a new owned directory",
            "Use a new attempt-local filing directory",
        )
    tree = html.document_fromstring(raw)
    before = "".join(tree.find("body").itertext())
    references = [e.get("src") for e in tree.findall(".//img")]
    requests = {r.filename: r for r in generation.asset_requests}
    if len(requests) > max_assets or len(raw) > max_total_bytes:
        raise fail(
            "ASSET_MANIFEST_LIMIT",
            "preparing_assets",
            "Asset count or total byte budget exceeded",
            "Review bounded filing artifact limits",
        )
    if len(requests) != len(generation.asset_requests) or set(references) != set(requests):
        raise fail(
            "ASSET_REQUEST_MISMATCH",
            "preparing_assets",
            "Actual IMG references differ from the source-bound request manifest",
            "Regenerate the HTM and asset requests together",
        )
    output_root.mkdir(mode=0o700, parents=False)
    evidence = []
    replacements = {}
    total_pixels = 0
    total_bytes = len(raw)
    with pymupdf.open(source_pdf) as document:
        for name, request in requests.items():
            context.check()
            if (
                not valid_filename(name, (".jpg", ".gif"))
                or request.source_pdf_sha256 != generation.source_pdf_sha256
                or request.source_xref <= 0
            ):
                raise fail(
                    "ASSET_REQUEST_INVALID",
                    "preparing_assets",
                    "Graphic request has an unsafe filename or stale source",
                    "Resolve the original request",
                )
            if document.xref_get_key(request.source_xref, "Subtype") != ("name", "/Image"):
                raise fail(
                    "ASSET_XREF_INVALID",
                    "preparing_assets",
                    "Requested source object is not an image",
                    "Resolve source image identity",
                )
            dimensions = [
                int(document.xref_get_key(request.source_xref, key)[1]) for key in ("Width", "Height")
            ]
            pixels = dimensions[0] * dimensions[1]
            total_pixels += pixels
            if min(dimensions) <= 0 or pixels > max_pixels or total_pixels > max_total_pixels:
                raise fail(
                    "ASSET_PIXEL_LIMIT",
                    "preparing_assets",
                    "Graphic exceeds the decoded-pixel budget",
                    "Review bounded image complexity",
                )
            extracted = document.extract_image(request.source_xref)
            native_mask = document.xref_get_key(request.source_xref, "SMask")
            native_mask_xref = int(native_mask[1].split()[0]) if native_mask[0] == "xref" else None
            if native_mask_xref != request.soft_mask_xref:
                raise fail(
                    "ASSET_MASK_MISMATCH",
                    "preparing_assets",
                    "Request disagrees with the source image soft mask",
                    "Resolve the source-bound alpha metadata",
                )
            pix = pymupdf.Pixmap(document, request.source_xref)
            if pix.colorspace is None:
                raise fail(
                    "ASSET_COLORSPACE_UNSUPPORTED",
                    "preparing_assets",
                    "Image colorspace cannot be normalized safely",
                    "Resolve the source graphic",
                )
            if pix.colorspace.n != 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if request.soft_mask_xref:
                mask_dimensions = [
                    int(document.xref_get_key(request.soft_mask_xref, key)[1]) for key in ("Width", "Height")
                ]
                if mask_dimensions != dimensions:
                    raise fail(
                        "ASSET_MASK_MISMATCH",
                        "preparing_assets",
                        "Source soft mask dimensions disagree before decoding",
                        "Resolve bounded source alpha geometry",
                    )
                if pix.alpha:
                    pix = pymupdf.Pixmap(pix, 0)
                mask = pymupdf.Pixmap(document, request.soft_mask_xref)
                if (mask.width, mask.height) != (pix.width, pix.height):
                    raise fail(
                        "ASSET_MASK_MISMATCH",
                        "preparing_assets",
                        "Image soft mask dimensions disagree",
                        "Resolve source alpha geometry",
                    )
                pix = pymupdf.Pixmap(pix, mask)
            mode = "RGBA" if pix.alpha else "RGB"
            source = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if mode == "RGBA":
                white = Image.new("RGBA", source.size, "white")
                white.alpha_composite(source)
                source = white.convert("RGB")
            converted = io.BytesIO()
            output_name = name
            passthrough = False
            if extracted["ext"] in {"jpeg", "jpg"} and not request.soft_mask_xref and not pix.alpha:
                payload = extracted["image"]
                format = "JPEG"
                passthrough = True
            elif source.getcolors(256) is not None:
                source.convert("P", palette=Image.Palette.ADAPTIVE, colors=256).save(
                    converted, format="GIF", optimize=False
                )
                payload = converted.getvalue()
                output_name = Path(name).stem + ".gif"
                format = "GIF"
            else:
                source.save(
                    converted, format="JPEG", quality=100, subsampling=0, optimize=False, progressive=False
                )
                payload = converted.getvalue()
                format = "JPEG"
            total_bytes += len(payload)
            if len(payload) > max_bytes or total_bytes > max_total_bytes:
                raise fail(
                    "ASSET_BYTE_LIMIT",
                    "preparing_assets",
                    "Normalized graphic exceeds its byte budget",
                    "Review bounded asset size",
                )
            with Image.open(io.BytesIO(payload)) as decoded:
                decoded.load()
                roundtrip = decoded.convert("RGB").tobytes()
            exact = roundtrip == source.tobytes()
            if format == "GIF" and not exact:
                raise fail(
                    "ASSET_PALETTE_LOSS",
                    "preparing_assets",
                    "Palette conversion changed source pixels",
                    "Use a verified graphic-only normalization strategy",
                )
            publish(output_root / output_name, payload)
            replacements[name] = output_name
            evidence.append(
                {
                    "filename": output_name,
                    "sha256": digest(payload),
                    "bytes": len(payload),
                    "format": format,
                    "width": source.width,
                    "height": source.height,
                    "source_xref": request.source_xref,
                    "soft_mask_xref": request.soft_mask_xref,
                    "original_jpeg_preserved": passthrough,
                    "decoded_pixels_exact": exact,
                    "alpha_composited_on_white": mode == "RGBA",
                }
            )
    # Only generator-produced literal IMG src values are changed; never reserialize disclosure.
    normalized = re.sub(
        rb'(<img\b[^>]*\bsrc=")([^"]+)(")',
        lambda match: match[1] + replacements[match[2].decode("ascii")].encode("ascii") + match[3],
        raw,
    )
    parsed = html.document_fromstring(normalized)
    if "".join(parsed.find("body").itertext()) != before or sorted(
        e.get("src") for e in parsed.findall(".//img")
    ) != sorted(replacements[n] for n in references):
        raise fail(
            "ASSET_CONTENT_INTEGRITY_FAILED",
            "preparing_assets",
            "Asset reference normalization changed disclosure or references",
            "Regenerate source-bound artifacts",
        )
    context.check()
    if sha256(source_pdf) != generation.source_pdf_sha256 or sha256(candidate) != generation.candidate_sha256:
        raise fail(
            "ASSET_SOURCE_CHANGED",
            "preparing_assets",
            "Source PDF or candidate changed during normalization",
            "Repeat from immutable current-attempt artifacts",
        )
    publish(output_root / candidate.name, normalized)
    return {
        "schema_version": 1,
        "source_pdf_sha256": generation.source_pdf_sha256,
        "original_candidate_sha256": generation.candidate_sha256,
        "normalized_htm_sha256": digest(normalized),
        "content_integrity_passed": True,
        "images": evidence,
        "strict_fidelity_passed": False,
    }
