from __future__ import annotations

import hashlib
import io
import json
import math
import os
import platform
from importlib.metadata import version
from pathlib import Path

from PIL import Image

from converter.context import ProcessingContext
from converter.errors import fail
from converter.ooxml import sha256
from converter.pdf_analysis.extract import _gate
from converter.pdf_export.libreoffice import font_fingerprint
from converter.pdf_export.validation import PDFValidationPolicy, _open, _render
from converter.sec_validation.models import ComplianceResult, ValidationPolicy
from converter.sec_validation.validator import read_bounded, validate_files
from converter.visual_validation.browser import render_browser
from converter.visual_validation.geometry import compare_geometry, page_geometry
from converter.visual_validation.models import VisualDiagnostic, VisualPolicy, VisualResult
from converter.visual_validation.pixels import compare_pixels


def object_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    ).hexdigest()


def fonts():
    if os.name == "nt":
        directories = [
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
            / "Microsoft/Windows/Fonts",
        ]
    elif platform.system() == "Darwin":
        directories = [Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path.home() / "Library/Fonts"]
    else:
        directories = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local/share/fonts",
        ]
    return font_fingerprint(directories)


class Evidence:
    def __init__(self, root, limit):
        self.root, self.limit = root, limit
        self.bytes = 0
        self.truncated = False
        self.names = []

    def image(self, name, image):
        data = io.BytesIO()
        image.save(data, format="PNG")
        payload = data.getvalue()
        if self.bytes + len(payload) > self.limit:
            self.truncated = True
            return
        with (self.root / name).open("xb") as stream:
            os.chmod(self.root / name, 0o600)
            stream.write(payload)
        self.bytes += len(payload)
        self.names.append(name)


def _compare(
    source_pdf,
    htm,
    assets,
    output,
    policy,
    context,
    mode,
    pdf_proof=None,
    sec_proof=None,
    submission=None,
    sec_policy=None,
):
    source_pdf, htm, output = Path(source_pdf), Path(htm), Path(output)
    policy, context = policy or VisualPolicy(), context or ProcessingContext()
    assets = tuple(map(Path, assets))
    context.check()
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise fail(
            "VISUAL_OUTPUT_INVALID",
            "comparing_formatting",
            "Visual evidence directory must be new and private",
            "Use a new current-attempt evidence path",
        )
    fresh = validate_files(htm, assets, submission, sec_policy or ValidationPolicy(), context)
    allowed_inspection = {
        "ATTRIBUTE_SCOPE_UNVERIFIED",
        "CSS_PERMISSION_UNVERIFIED",
        "ENTITY_MAPPING_UNVERIFIED",
    }
    if mode == "validated_pipeline":
        gate_hash = _gate(source_pdf, pdf_proof or {})
        if sec_proof is None:
            raise fail(
                "VISUAL_SEC_GATE_REQUIRED",
                "comparing_formatting",
                "Strict local SEC evidence is required before production visual comparison",
                "Resolve prior checks and provide the complete submission context",
            )
        sec_proof = ComplianceResult.model_validate(
            sec_proof.model_dump() if isinstance(sec_proof, ComplianceResult) else sec_proof
        )
        if (
            not fresh.strict_passed
            or not sec_proof.strict_passed
            or fresh.model_dump() != sec_proof.model_dump()
        ):
            raise fail(
                "VISUAL_SEC_GATE_REQUIRED",
                "comparing_formatting",
                "Actual files or strict SEC evidence do not match the current passing gate",
                "Revalidate immutable files and resolve prior uncertainty",
            )
        sec_hash = object_hash(sec_proof.model_dump(mode="json"))
    else:
        gate_hash = sec_hash = None
        if not fresh.checks_complete or any(
            d.severity == "error" and d.code not in allowed_inspection for d in fresh.diagnostics
        ):
            raise fail(
                "VISUAL_INSPECTION_UNSAFE",
                "comparing_formatting",
                "Diagnostic inspection still requires safe bounded literal HTM/assets",
                "Resolve active, remote, malformed or unsupported resource constructs",
            )
    resources = {}
    for file in fresh.files:
        path = htm if file.filename == htm.name else next(p for p in assets if p.name == file.filename)
        resources[file.filename] = read_bounded(
            path, policy.max_html_bytes if path == htm else policy.max_asset_bytes
        )
        if hashlib.sha256(resources[file.filename]).hexdigest() != file.sha256:
            raise fail(
                "VISUAL_INPUT_CHANGED",
                "comparing_formatting",
                "Artifact changed between validation and capture",
                "Use immutable current-attempt files",
            )
    if sum(len(v) for v in resources.values()) > policy.max_input_bytes:
        raise fail(
            "VISUAL_INPUT_LIMIT",
            "comparing_formatting",
            "Captured input manifest exceeds the byte budget",
            "Review bounded rendering limits",
        )
    source_hash = sha256(source_pdf)
    htm_hash = hashlib.sha256(resources[htm.name]).hexdigest()
    pdf_policy = PDFValidationPolicy(
        max_pages=policy.max_pages,
        max_pdf_bytes=policy.max_pdf_bytes,
        max_render_pixels=policy.max_page_pixels,
    )
    with _open(source_pdf, pdf_policy) as source:
        sizes = [(p.rect.width, p.rect.height) for p in source]
        if any(size != sizes[0] for size in sizes) or any(p.rotation for p in source):
            raise fail(
                "VISUAL_PAGE_GEOMETRY_UNSUPPORTED",
                "comparing_formatting",
                "Mixed or rotated source page geometry is outside the fixed print profile",
                "Implement a separately verified per-page rendering strategy",
            )
        pixels = sum(math.ceil(w * policy.dpi / 72) * math.ceil(h * policy.dpi / 72) for w, h in sizes)
        if pixels > policy.max_total_pixels or any(
            math.ceil(w * policy.dpi / 72) * math.ceil(h * policy.dpi / 72) > policy.max_page_pixels
            for w, h in sizes
        ):
            raise fail(
                "VISUAL_PIXEL_LIMIT",
                "comparing_formatting",
                "Source raster dimensions exceed the visual budget",
                "Review DPI/page limits without normalizing away layout differences",
            )
        output.mkdir(mode=0o700)
        evidence = Evidence(output, policy.max_evidence_bytes)
        font_hash = fonts()
        context.check()
        renderer = render_browser(resources, htm.name, sizes[0], output / "browser", policy, context)
        renderer.update(
            {
                "font_environment_sha256": font_hash,
                "platform": platform.platform(),
                "pymupdf_version": __import__("pymupdf").VersionBind,
                "numpy_version": version("numpy"),
                "pillow_version": version("pillow"),
                "screen_antialias_suppression": False,
                "policy_sha256": object_hash(policy.model_dump(mode="json")),
                "input_manifest_sha256": object_hash(
                    {name: hashlib.sha256(data).hexdigest() for name, data in resources.items()}
                ),
                "submission_context_sha256": object_hash(submission.model_dump(mode="json"))
                if submission
                else None,
            }
        )
        diagnostics = []
        pages = []
        source_chars = rendered_chars = 0
        remaining_geometry_records = policy.max_geometry_differences

        def diagnostic(code, description, page=None, count=1):
            diagnostics.append(
                VisualDiagnostic(
                    code=code,
                    description=description,
                    remediation="Inspect private page/geometry evidence; preserve disclosure and revalidate all affected gates",
                    page=page,
                    count=count,
                )
            )

        with _open(output / "browser/chromium.pdf", pdf_policy) as rendered:
            if source.page_count != rendered.page_count:
                diagnostic("VISUAL_PAGE_COUNT_MISMATCH", "Browser pagination differs from the source PDF")
            if renderer["denied_requests"]:
                diagnostic(
                    "VISUAL_RESOURCE_REQUEST_DENIED",
                    "Browser attempted a resource outside the captured manifest",
                    count=renderer["denied_requests"],
                )
            if any(not image["loaded"] for image in renderer["images"]):
                diagnostic("VISUAL_IMAGE_NOT_LOADED", "Referenced graphic did not decode in Chromium")
            if renderer["hidden_text_characters"]:
                diagnostic(
                    "VISUAL_HIDDEN_DISCLOSURE",
                    "DOM contains hidden or nonrendering text characters",
                    count=renderer["hidden_text_characters"],
                )
            if renderer["screen_page_mapping"] == "unresolved":
                diagnostic(
                    "VISUAL_SCREEN_MAPPING_UNRESOLVED",
                    "Continuous browser layout cannot be unambiguously mapped to source pages",
                )
            if renderer["document_width"] > math.ceil(sizes[0][0] * 96 / 72):
                diagnostic("VISUAL_HORIZONTAL_OVERFLOW", "Browser content extends beyond the page viewport")
            for index in range(max(source.page_count, rendered.page_count)):
                context.check()
                number = index + 1
                if index >= source.page_count or index >= rendered.page_count:
                    diagnostic("VISUAL_PAGE_MISSING", "A source or browser page has no counterpart", number)
                    pages.append({"page": number, "passed": False, "missing_counterpart": True})
                    continue
                expected, actual = source[index], rendered[index]
                a, b = page_geometry(expected, policy), page_geometry(actual, policy)
                source_chars += len(a["chars"])
                rendered_chars += len(b["chars"])
                if max(source_chars, rendered_chars) > policy.max_characters:
                    raise fail(
                        "VISUAL_CHARACTER_LIMIT",
                        "comparing_formatting",
                        "Extracted visual text exceeds the character budget",
                        "Review bounded document complexity",
                    )
                geometry = compare_geometry(a, b, policy.geometry_tolerance_pt, remaining_geometry_records)
                remaining_geometry_records -= len(geometry["differences"])
                for key, code in (
                    ("content_equal", "VISUAL_CONTENT_MISMATCH"),
                    ("geometry_equal", "VISUAL_GEOMETRY_MISMATCH"),
                    ("image_geometry_pixels_equal", "VISUAL_IMAGE_MISMATCH"),
                    ("vector_geometry_paint_equal", "VISUAL_VECTOR_MISMATCH"),
                    ("dimensions_equal", "VISUAL_DIMENSIONS_MISMATCH"),
                ):
                    if not geometry[key]:
                        diagnostic(code, "Source and browser " + key.replace("_", " ") + " differs", number)
                if geometry["font_substitutions"]:
                    diagnostic(
                        "VISUAL_FONT_SUBSTITUTION",
                        "Browser selected different PDF font names",
                        number,
                        geometry["font_substitutions"],
                    )
                if geometry["font_size_mismatches"]:
                    diagnostic(
                        "VISUAL_FONT_SIZE_MISMATCH",
                        "Source and rendered font sizes differ",
                        number,
                        geometry["font_size_mismatches"],
                    )
                if not geometry["font_resource_sets_equal"]:
                    diagnostic(
                        "VISUAL_FONT_RESOURCE_DIFFERENCE",
                        "Font resource sets differ; substitution or removed text needs diagnosis",
                        number,
                    )
                if not geometry["font_size_sets_equal"]:
                    diagnostic(
                        "VISUAL_FONT_SIZE_DIFFERENCE",
                        "Source and browser use different sets of font sizes",
                        number,
                    )
                reference_image = _render(expected, policy.dpi)
                actual_image = _render(actual, policy.dpi)
                boxes = [c["bbox"] for c in a["chars"]]
                structure = (
                    geometry["geometry_equal"]
                    and geometry["embedded_font_programs_equal"]
                    and not a["images"]
                )
                print_metrics, heat, overlay = compare_pixels(
                    reference_image, actual_image, boxes, policy.dpi / 72, structure
                )
                stem = f"page{number:04d}"
                evidence.image(stem + ".pdf.png", reference_image)
                evidence.image(stem + ".print.png", actual_image)
                if heat is not None:
                    evidence.image(stem + ".print-diff.png", heat)
                    evidence.image(stem + ".overlay.png", overlay)
                screen_metrics = None
                screen_path = output / "browser" / f"screen{number:04d}.png"
                if screen_path.is_file() and renderer["screen_page_mapping"] != "unresolved":
                    with Image.open(screen_path) as im:
                        screen = im.convert("RGB")
                    screen_metrics, screen_heat, _ = compare_pixels(
                        reference_image, screen, boxes, policy.dpi / 72, False
                    )
                    evidence.image(stem + ".screen.png", screen)
                    if screen_heat is not None:
                        evidence.image(stem + ".screen-diff.png", screen_heat)
                for kind, metrics in (("print", print_metrics), ("screen", screen_metrics)):
                    if (
                        metrics is None
                        or not metrics["size_equal"]
                        or metrics["unexplained_difference_pixels"]
                    ):
                        diagnostic(
                            "VISUAL_" + kind.upper() + "_PIXEL_MISMATCH",
                            "Unexplained " + kind + " raster differences remain",
                            number,
                        )
                passed = (
                    geometry["geometry_equal"]
                    and print_metrics["size_equal"]
                    and print_metrics["unexplained_difference_pixels"] == 0
                    and screen_metrics is not None
                    and screen_metrics["size_equal"]
                    and screen_metrics["unexplained_difference_pixels"] == 0
                )
                pages.append(
                    {
                        "page": number,
                        "passed": passed,
                        "geometry": geometry,
                        "print_pixels": print_metrics,
                        "screen_pixels": screen_metrics,
                    }
                )
            rendered_count = rendered.page_count
        context.check()
        if sha256(source_pdf) != source_hash or any(
            sha256(htm if name == htm.name else next(p for p in assets if p.name == name))
            != hashlib.sha256(data).hexdigest()
            for name, data in resources.items()
        ):
            raise fail(
                "VISUAL_INPUT_CHANGED",
                "comparing_formatting",
                "An input changed during rendering or comparison",
                "Repeat validation on immutable artifacts",
            )
        if fonts() != font_hash:
            diagnostic("VISUAL_FONT_ENVIRONMENT_CHANGED", "Installed font bytes changed during comparison")
        if evidence.truncated:
            diagnostic(
                "VISUAL_EVIDENCE_LIMIT", "Evidence byte budget was reached; required artifacts are incomplete"
            )
        comparison = not diagnostics and all(p["passed"] for p in pages)
        result = VisualResult(
            mode=mode,
            comparison_passed=comparison,
            strict_passed=comparison and mode == "validated_pipeline",
            checks_complete=True,
            source_pdf_sha256=source_hash,
            htm_sha256=htm_hash,
            asset_sha256={n: hashlib.sha256(v).hexdigest() for n, v in resources.items() if n != htm.name},
            pdf_gate_sha256=gate_hash,
            sec_gate_sha256=sec_hash,
            policy=policy.model_dump(mode="json"),
            renderer=renderer,
            source_pages=len(sizes),
            rendered_pages=rendered_count,
            pages=tuple(pages),
            evidence_bytes=evidence.bytes,
            evidence_truncated=evidence.truncated,
            artifacts=tuple(evidence.names),
            diagnostics=tuple(diagnostics),
        )
        with (output / "visual.json").open("x", encoding="utf-8") as stream:
            os.chmod(output / "visual.json", 0o600)
            stream.write(result.model_dump_json())
        return result


def compare_visuals(
    source_pdf,
    htm,
    assets,
    pdf_validation,
    sec_validation,
    output,
    policy=None,
    context=None,
    submission=None,
    sec_policy=None,
):
    return _compare(
        source_pdf,
        htm,
        assets,
        output,
        policy,
        context,
        "validated_pipeline",
        pdf_validation,
        sec_validation,
        submission,
        sec_policy,
    )


def inspect_visuals(source_pdf, htm, assets, output, policy=None, context=None):
    """Explicit diagnostic comparison; never supplies a successful production gate."""
    return _compare(source_pdf, htm, assets, output, policy, context, "inspection_only")
