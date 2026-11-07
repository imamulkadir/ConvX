from __future__ import annotations

import hashlib
import io
import re
import warnings
from html.entities import name2codepoint
from pathlib import Path
from urllib.parse import urlsplit

from lxml import etree, html
from PIL import Image, UnidentifiedImageError

from converter.context import ProcessingContext
from converter.sec_validation.flow_profile import flow_profile_digest, flow_style_allowed, flow_style_problems
from converter.sec_validation.layer_profile import (
    VERIFIED_REFERENCES,
    layer_profile_digest,
    layer_style_problems,
)
from converter.sec_validation.models import (
    ComplianceDiagnostic,
    ComplianceResult,
    FileEvidence,
    SubmissionContext,
    ValidationPolicy,
)
from converter.sec_validation.profile import registry, style_problems, valid_filename
from converter.sec_validation.scanner import ScanLimit, SourceScanner


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bounded(path, limit):
    if path.is_symlink() or not path.is_file():
        raise OSError("Not a regular owned file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Byte budget exceeded")
    return data


class Checks:
    def __init__(self, htm, policy, context):
        self.htm, self.policy, self.context = htm, policy, context
        self.profile, self.registry_hash = registry()
        self.diagnostics = []
        self.evidence = []
        self.snapshots = {}
        self.complete = True

    def diagnostic(
        self,
        code,
        description,
        remediation,
        node=None,
        section="5.2.2.1",
        basis="confirmed_manual",
        severity="error",
        file=None,
    ):
        filename = file or self.htm.name
        for i, d in enumerate(self.diagnostics):
            if (d.code, d.file, d.element) == (code, filename, node.tag if node else None):
                self.diagnostics[i] = d.model_copy(update={"occurrences": d.occurrences + 1})
                return
        if len(self.diagnostics) >= self.policy.max_diagnostics - 1:
            self.diagnostics.append(
                ComplianceDiagnostic(
                    code="VALIDATION_DIAGNOSTIC_LIMIT",
                    severity="error",
                    description="Diagnostic budget reached; validation incomplete",
                    file=self.htm.name,
                    section="project processing limits",
                    basis="project_policy",
                    remediation="Resolve reported failures and rerun",
                )
            )
            self.complete = False
            raise ScanLimit
        self.diagnostics.append(
            ComplianceDiagnostic(
                code=code,
                severity=severity,
                description=description,
                file=filename,
                element=node.tag if node else None,
                line=node.line if node else None,
                section=section,
                basis=basis,
                remediation=remediation,
            )
        )

    def read(self, path, limit, format):
        self.context.check()
        try:
            data = read_bounded(path, limit)
        except (OSError, ValueError):
            self.diagnostic(
                "FILE_UNAVAILABLE_OR_LIMIT",
                "File is absent, linked, unreadable or exceeds its byte budget",
                "Supply a regular bounded file in the owned artifact root",
                file=path.name,
                basis="project_policy",
            )
            return None
        self.snapshots[path] = digest(data)
        self.evidence.append(
            FileEvidence(filename=path.name, sha256=digest(data), bytes=len(data), format=format)
        )
        if sum(e.bytes for e in self.evidence) > self.policy.max_total_bytes:
            self.diagnostic(
                "ARTIFACT_BYTE_LIMIT",
                "Combined artifact byte budget exceeded",
                "Review bounded artifact limits",
                basis="project_policy",
            )
            self.complete = False
            raise ScanLimit
        return data

    def characters(self, source):
        if not source.isascii():
            self.diagnostic(
                "HTML_RAW_EXTENDED_BYTES",
                "HTM contains raw extended bytes",
                "Represent disclosure using verified references without transliteration",
                section="5.2.2.6",
            )
        if any(c < 32 and c not in (9, 10, 13) or c == 127 for c in source):
            self.diagnostic(
                "HTML_CONTROL_BYTE",
                "Control bytes are outside the document profile",
                "Resolve source encoding without discarding disclosure",
                section="5.2.2.6",
                basis="project_policy",
            )
        text = source.decode("ascii", errors="replace")
        cursor = 0
        while (start := text.find("<!--", cursor)) >= 0:
            end = text.find("-->", start + 4)
            if end < 0 or "--" in text[start + 4 : end] or text[start + 4 : end].startswith((">", "->")):
                self.diagnostic(
                    "HTML_COMMENT_AMBIGUOUS",
                    "Malformed comment may hide markup differently across parsers",
                    "Use unambiguous canonical comments or remove the malformed wrapper",
                    basis="project_policy",
                )
                break
            cursor = end + 3
        # Comments have no rendered character references.
        rendered = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        explicit = {
            name2codepoint[n]
            for n in (
                "fnof",
                "hellip",
                "dagger",
                "Dagger",
                "permil",
                "Scaron",
                "lsaquo",
                "OElig",
                "trade",
                "scaron",
                "rsaquo",
                "oelig",
                "Yuml",
            )
        }
        for match in re.finditer(r"&(#(?:[xX][0-9A-Fa-f]+|[0-9]+)|[A-Za-z][A-Za-z0-9]*)(;?)", rendered):
            self.context.check()
            token, terminator = match.groups()
            if not terminator:
                self.diagnostic(
                    "ENTITY_TERMINATOR_REQUIRED",
                    "Ambiguous unterminated entity/reference",
                    "Use complete references preserving the intended character",
                    section="5.2.2.6",
                    basis="project_policy",
                )
                continue
            try:
                code = (
                    int(token[2:], 16)
                    if token.startswith(("#x", "#X"))
                    else int(token[1:])
                    if token.startswith("#")
                    else name2codepoint[token]
                )
            except (ValueError, KeyError):
                self.diagnostic(
                    "ENTITY_UNKNOWN",
                    "Reference is not in the verified HTML4/Latin-1 repertoire",
                    "Verify an unambiguous source-character mapping",
                    section="5.2.2.6",
                    basis="unresolved",
                )
                continue
            verified_html4 = (
                self.policy.html_profile in {"edgar_flow_v1", "edgar_layers_v1"}
                and code in name2codepoint.values()
            )
            if not (
                code in (9, 10, 13)
                or 32 <= code <= 126
                or 160 <= code <= 255
                or code in explicit
                or verified_html4
                or self.policy.html_profile == "edgar_layers_v1"
                and code in VERIFIED_REFERENCES
            ):
                self.diagnostic(
                    "ENTITY_MAPPING_UNVERIFIED",
                    "Character reference has no approved mapping in this conservative profile",
                    "Verify the manual/W3C mapping; never substitute or transliterate disclosure",
                    section="5.2.2.6",
                    basis="unresolved",
                )
            if 128 <= code <= 159:
                self.diagnostic(
                    "ENTITY_LEGACY_REMAP",
                    "Legacy C1 numeric reference may change meaning in browsers",
                    "Use a verified named or Unicode reference for the intended character",
                    section="5.2.2.6",
                    basis="project_policy",
                )
        return text

    def nodes(self, scanner):
        profile = self.profile
        blocked_profile = {"plaintext", "listing", "xmp", "isindex"}
        anchors = {}
        images = []
        links = []
        for node in scanner.nodes:
            self.context.check()
            if node.tag not in profile["tags"]:
                self.diagnostic(
                    "HTML_TAG_PROHIBITED",
                    "Element is absent from the manual's permitted vocabulary",
                    "Use a permitted representation or report an incompatibility",
                    node,
                    section="5.2.2.2; 5.2.2.3; 5.2.2.4",
                )
            elif node.tag in blocked_profile:
                self.diagnostic(
                    "HTML_TAG_OUTSIDE_PRODUCT_PROFILE",
                    "Manual-listed legacy/interactive element is unsupported by this accepted-final product profile",
                    "Use a noninteractive representation and revalidate disclosure",
                    node,
                    basis="project_policy",
                )
            if node.tag == "r":
                self.diagnostic(
                    "REDLINE_CONTEXT_REQUIRED",
                    "Redlining is manual-supported but outside accepted-final output",
                    "Do not introduce redlining after accepting all revisions",
                    node,
                    section="5.2.2.8",
                    basis="project_policy",
                )
            if node.tag == "table" and "table" in node.ancestors:
                self.diagnostic(
                    "HTML_NESTED_TABLE",
                    "TABLE is nested inside TABLE",
                    "Reconstruct using nonnested permitted layout",
                    node,
                    section="5.2.2.3",
                )
            for name, value in node.attrs.items():
                if name.startswith("on") or name in profile["restricted_attributes"].get(node.tag, []):
                    self.diagnostic(
                        "HTML_ATTRIBUTE_PROHIBITED",
                        "Event or explicitly restricted attribute",
                        "Remove active/restricted behavior without changing disclosure",
                        node,
                        section="5.2.2.4; 5.2.2.5",
                    )
                    continue
                parents = profile["attributes"].get(name, [])
                if node.tag not in parents and "MANY" not in parents:
                    self.diagnostic(
                        "HTML_ATTRIBUTE_UNLISTED",
                        "Attribute is not explicitly listed for this element",
                        "Resolve attribute permissions against the manual",
                        node,
                        section="5.2.2.5",
                        basis="unresolved" if name in {"face", "width", "height"} else "confirmed_manual",
                    )
                elif "MANY" in parents and not (
                    self.policy.html_profile in {"edgar_flow_v1", "edgar_layers_v1"}
                    and name == "style"
                    and flow_style_allowed(node.tag)
                ):
                    self.diagnostic(
                        "ATTRIBUTE_SCOPE_UNVERIFIED",
                        "MANY does not enumerate this attribute's complete per-tag scope",
                        "Approve a source-backed per-tag interpretation before strict filing validation",
                        node,
                        section="5.2.2.5",
                        basis="unresolved",
                    )
                if name == "style":
                    flow = self.policy.html_profile in {"edgar_flow_v1", "edgar_layers_v1"}
                    for code in (
                        (
                            layer_style_problems(value or "")
                            if self.policy.html_profile == "edgar_layers_v1"
                            else flow_style_problems(value or "")
                        )
                        if flow
                        else style_problems(value or "", profile)
                    ):
                        self.diagnostic(
                            code,
                            "Inline formatting is outside the safe literal grammar",
                            "Remove active/unsupported CSS or report exact fidelity incompatibility",
                            node,
                            section="5.2.2.5; project security policy",
                            basis="project_policy",
                        )
                    if not flow:
                        self.diagnostic(
                            "CSS_PERMISSION_UNVERIFIED",
                            "Safe CSS syntax alone does not establish permitted EDGAR property/value scope",
                            "Resolve the manual's CSS scope before strict validation",
                            node,
                            section="5.2.2.5",
                            basis="unresolved",
                        )
                if name in {"rowspan", "colspan", "border", "cellpadding", "cellspacing", "size"} and (
                    value is None
                    or re.fullmatch(r"[0-9]{1,6}", value) is None
                    or name in {"rowspan", "colspan"}
                    and int(value) == 0
                ):
                    self.diagnostic(
                        "ATTRIBUTE_VALUE_INVALID",
                        "Numeric attribute is outside this bounded product grammar",
                        "Use an appropriate nonnegative integer or report unsupported semantics",
                        node,
                        section="5.2.2.5",
                        basis="project_policy",
                    )
            for name in ("id", "name"):
                if name == "name" and node.tag != "a":
                    continue
                if name not in node.attrs:
                    continue
                value = node.attrs[name]
                if not value or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value) is None:
                    self.diagnostic(
                        "BOOKMARK_INVALID",
                        "Bookmark is empty or outside the conservative literal grammar",
                        "Use an unambiguous unique bookmark and update links",
                        node,
                        basis="project_policy",
                    )
                elif value in anchors and anchors[value] != node.number:
                    self.diagnostic(
                        "BOOKMARK_DUPLICATE",
                        "Multiple elements define the same bookmark",
                        "Resolve ambiguous destinations",
                        node,
                        basis="project_policy",
                    )
                else:
                    anchors[value] = node.number
            if node.tag == "img":
                if not node.attrs.get("src"):
                    self.diagnostic(
                        "IMAGE_SOURCE_REQUIRED",
                        "IMG lacks a local source",
                        "Supply a validated JPG/GIF reference",
                        node,
                        section="5.2.2.3",
                    )
                else:
                    images.append((node, node.attrs["src"]))
            if node.tag == "a" and "href" in node.attrs:
                links.append((node, node.attrs["href"]))
        return anchors, images, links

    def references(self, anchors, images, links, assets):
        referenced = set()
        for node, target in images:
            if not valid_filename(target, (".jpg", ".gif")):
                self.diagnostic(
                    "IMAGE_REFERENCE_INVALID",
                    "IMG source is not a root-relative JPG/GIF filename",
                    "Remove remote/data/traversal references and normalize graphics",
                    node,
                    section="5.2.2.3",
                )
                continue
            referenced.add(target)
            if target not in assets:
                self.diagnostic(
                    "IMAGE_MISSING",
                    "Referenced graphic is absent from the explicit asset manifest",
                    "Supply the exact case-sensitive local asset",
                    node,
                    section="5.2.2.1",
                )
        for name in set(assets) - referenced:
            self.diagnostic(
                "ASSET_UNUSED",
                "Manifest includes an unreferenced image",
                "Exclude unused assets from final filing output",
                file=name,
                basis="project_policy",
                section="project sections 8 and 10",
            )
        for node, target in links:
            target = target or ""
            if (
                not target
                or any(ord(c) < 33 or ord(c) > 126 for c in target)
                or "\\" in target
                or "%" in target
            ):
                self.diagnostic(
                    "HYPERLINK_INVALID",
                    "Hyperlink is empty, encoded or outside the literal URL profile",
                    "Resolve the intended target without silently deleting the hyperlink",
                    node,
                    section="5.2.2.3",
                    basis="project_policy",
                )
                continue
            try:
                parsed = urlsplit(target)
            except ValueError:
                self.diagnostic(
                    "HYPERLINK_INVALID",
                    "Hyperlink cannot be parsed unambiguously",
                    "Repair the original target",
                    node,
                )
                continue
            if parsed.scheme or parsed.netloc:
                if not (
                    parsed.scheme == "https"
                    and parsed.netloc == "www.sec.gov"
                    and parsed.path.startswith("/Archives/edgar/data/")
                    and not parsed.query
                    and not any(p in {".", ".."} for p in parsed.path.split("/"))
                ):
                    self.diagnostic(
                        "HYPERLINK_EXTERNAL_PROHIBITED",
                        "External hyperlink is not an ordinary SEC Archives reference",
                        "Use an allowed SEC target or resolvable submission reference",
                        node,
                        section="5.2.2.1; 5.2.2.3",
                    )
            elif parsed.path in {"", self.htm.name} and not parsed.query:
                if parsed.fragment and parsed.fragment not in anchors:
                    self.diagnostic(
                        "HYPERLINK_FRAGMENT_MISSING",
                        "Internal bookmark target does not exist",
                        "Restore the exact destination",
                        node,
                        section="5.2.2.1; 5.2.2.3",
                    )
            else:
                self.diagnostic(
                    "HYPERLINK_OUTSIDE_PACKAGE_PROFILE",
                    "Local target is outside this one-HTM artifact manifest; such submission links may be manual-permitted",
                    "Provide complete authorized submission context or resolve the product ZIP constraint",
                    node,
                    section="5.2.2.3; project section 10",
                    basis="project_policy",
                )

    def asset(self, path):
        data = self.read(path, self.policy.max_asset_bytes, "image")
        if data is None:
            return 0
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as im:
                    width, height = im.size
                    format = im.format
                    if format not in {"JPEG", "GIF"} or (format == "JPEG") != (path.suffix.lower() == ".jpg"):
                        self.diagnostic(
                            "IMAGE_FORMAT_INVALID",
                            "Actual image encoding disagrees with permitted JPG/GIF filename",
                            "Decode and normalize the image, not merely rename its extension",
                            file=path.name,
                            section="5.2.2.3",
                        )
                        return 0
                    if width * height > self.policy.max_image_pixels:
                        raise ValueError
                    if getattr(im, "n_frames", 1) != 1:
                        self.diagnostic(
                            "IMAGE_ANIMATION_OUTSIDE_PROFILE",
                            "Animated images are outside the static reconstruction profile",
                            "Use a validated static source graphic",
                            file=path.name,
                            basis="project_policy",
                        )
                    im.verify()
                with Image.open(io.BytesIO(data)) as im:
                    im.load()
            self.evidence[-1] = self.evidence[-1].model_copy(
                update={"format": format, "width": width, "height": height}
            )
            return width * height
        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            self.diagnostic(
                "IMAGE_CORRUPT_OR_LIMIT",
                "Image is corrupt or exceeds the decoded-pixel budget",
                "Supply a bounded valid permitted image",
                file=path.name,
                basis="project_policy",
            )
            return 0


def validate_files(
    htm: Path,
    assets: tuple[Path, ...] = (),
    submission: SubmissionContext | None = None,
    policy: ValidationPolicy | None = None,
    context: ProcessingContext | None = None,
) -> ComplianceResult:
    htm = Path(htm)
    policy = policy or ValidationPolicy()
    context = context or ProcessingContext()
    context.check()
    checks = Checks(htm, policy, context)
    if policy.html_profile in {"edgar_flow_v1", "edgar_layers_v1"}:
        checks.diagnostic(
            "LOCAL_FORMATTING_PROFILE",
            "Formatting and HTML4 character mappings use the documented local EFM78 interpretation; this is not an SEC validation result",
            "Review browser differences and perform authorized EDGAR document/test validation before filing",
            section="5.2.2.5; 5.2.2.6; 5.2.2.10",
            basis="project_policy",
            severity="warning",
        )
    limits_checked = False
    try:
        manifest = {}
        if len(assets) > policy.max_assets:
            checks.diagnostic(
                "ASSET_COUNT_LIMIT",
                "Asset manifest exceeds its file-count budget",
                "Review bounded asset limits",
                basis="project_policy",
            )
            raise ScanLimit
        for path in (htm, *map(Path, assets)):
            if not valid_filename(path.name, (".htm",) if path == htm else (".jpg", ".gif")):
                checks.diagnostic(
                    "FILENAME_INVALID",
                    "Filename violates the 32-character ASCII root-file profile",
                    "Use a deterministic compliant name",
                    file=path.name,
                    section="5.1.1",
                )
            if path.parent.resolve() != htm.parent.resolve() or path.is_symlink():
                checks.diagnostic(
                    "ASSET_PATH_INVALID",
                    "Manifest file is outside the HTM root or is linked",
                    "Use regular files in the owned artifact root",
                    file=path.name,
                    basis="project_policy",
                )
                continue
            if path != htm:
                if path.name.casefold() in {n.casefold() for n in manifest}:
                    checks.diagnostic(
                        "ASSET_NAME_COLLISION",
                        "Asset names collide under case-insensitive resolution",
                        "Use unique portable filenames",
                        file=path.name,
                        basis="project_policy",
                    )
                manifest[path.name] = path
        raw = checks.read(htm, policy.max_html_bytes, "HTML")
        if raw is not None:
            source = checks.characters(raw)
            scanner = SourceScanner(policy, checks.diagnostic, context)
            scanner.feed(source)
            scanner.close()
            if scanner.rawdata.strip():
                checks.diagnostic(
                    "HTML_INCOMPLETE_SOURCE",
                    "Unconsumed/unterminated source markup remains",
                    "Resolve malformed bytes before parser repair",
                    basis="project_policy",
                )
            anchors, images, links = checks.nodes(scanner)
            checks.references(anchors, images, links, manifest)
            # Guidance is supplementary to the supplied manual; repeated equivalent tiny
            # formatting wrappers are rejected without claiming all mixed emphasis is illegal.
            parsed = html.document_fromstring(source)
            if any(sum(n.tag == tag for n in scanner.nodes) > 1 for tag in ("html", "head", "body")):
                checks.diagnostic(
                    "HTML_MULTIPLE_DOCUMENTS",
                    "Multiple document containers have ambiguous parser behavior",
                    "Supply one coherent HTML document",
                    basis="project_policy",
                )
            for paragraph in parsed.findall(".//p"):
                fonts = paragraph.findall(".//font")
                keys = {
                    re.sub(r"(?:width|margin-left|display):[^;]+;?", "", font.get("style", ""))
                    for font in fonts
                }
                if (
                    len(fonts) >= 4
                    and len(keys) == 1
                    and all(len(font.text_content().split()) <= 1 for font in fonts)
                ):
                    checks.diagnostic(
                        "HTML_REDUNDANT_WORD_FORMATTING",
                        "Equivalent formatting is independently repeated for words or characters",
                        "Coalesce equivalent formatting runs and revalidate source layout",
                        section="SEC filing limits guidance: item 1",
                        basis="sec_guidance",
                    )
        pixels = 0
        for path in manifest.values():
            pixels += checks.asset(path)
            if pixels > policy.max_total_image_pixels:
                checks.diagnostic(
                    "IMAGE_TOTAL_PIXEL_LIMIT",
                    "Combined decoded graphics exceed their budget",
                    "Review bounded asset complexity",
                    basis="project_policy",
                )
                break
        size = sum(e.bytes for e in checks.evidence)
        if size > policy.max_total_bytes:
            checks.diagnostic(
                "ARTIFACT_BYTE_LIMIT",
                "Artifact files exceed the local byte budget",
                "Review bounded artifact limits",
                basis="project_policy",
            )
        if submission:
            limit = (
                600_000_000
                if submission.form_type
                in {"ABS-EE", "ABS-EE/A", "NPORT-NP", "NPORT-NP/A", "NPORT-P", "NPORT-P/A"}
                else 800_000_000
                if submission.form_type in {"10-D/ABS-EE", "10-D/ABS-EE/A"}
                else 200_000_000
            )
            if submission.encoded_submission_bytes < size or submission.encoded_submission_bytes > limit:
                checks.diagnostic(
                    "SUBMISSION_SIZE_INVALID",
                    "Encoded whole-submission size is inconsistent or exceeds the form's limit",
                    "Supply actual complete MIME-encoded submission accounting",
                    section="5.2.2.10; 7.3.2",
                )
            else:
                limits_checked = True
            if submission.form_type in {"ABS-15G", "ABS-15G/A"} and raw is not None and len(raw) > 25_000_000:
                checks.diagnostic(
                    "HTML_FORM_SIZE_LIMIT",
                    "HTML document exceeds the ABS-15G per-document limit",
                    "Resolve the form-specific attachment size",
                    section="5.2.2.10",
                )
            if submission.form_type.startswith("10-D/ABS-EE"):
                limits_checked = False
                checks.diagnostic(
                    "SUBMISSION_COMPONENT_CONTEXT_REQUIRED",
                    "Combined filing also needs separate 10-D and ABS-EE component accounting",
                    "Verify the 200/600 MB component limits in addition to the 800 MB total",
                    section="5.2.2.10",
                    basis="unresolved",
                )
        else:
            checks.diagnostic(
                "SUBMISSION_CONTEXT_REQUIRED",
                "Form and whole encoded submission size are not supplied",
                "Complete submission-context checks before filing qualification",
                section="5.2.2.10; 7.3.2",
                basis="project_policy",
                severity="warning",
            )
        for path, before in checks.snapshots.items():
            context.check()
            try:
                unchanged = (
                    digest(read_bounded(path, max(policy.max_html_bytes, policy.max_asset_bytes))) == before
                )
            except (OSError, ValueError):
                unchanged = False
            if not unchanged:
                checks.diagnostic(
                    "VALIDATED_FILE_CHANGED",
                    "A file changed during validation",
                    "Revalidate an immutable artifact manifest",
                    file=path.name,
                    basis="project_policy",
                )
    except ScanLimit:
        checks.complete = False
        if not any(d.code == "VALIDATION_DIAGNOSTIC_LIMIT" for d in checks.diagnostics):
            checks.diagnostic(
                "HTML_COMPLEXITY_LIMIT",
                "Source scan exceeded node/depth/attribute limits",
                "Review bounded HTML complexity",
                basis="project_policy",
            )
    except (ValueError, AssertionError, etree.ParserError):
        checks.complete = False
        checks.diagnostic(
            "HTML_PARSE_FAILED",
            "Source cannot be parsed safely without recovery ambiguity",
            "Repair the actual file bytes",
            basis="project_policy",
        )
    passed = checks.complete and not any(d.severity == "error" for d in checks.diagnostics)
    return ComplianceResult(
        html_profile=policy.html_profile,
        formatting_profile_sha256=layer_profile_digest()
        if policy.html_profile == "edgar_layers_v1"
        else flow_profile_digest()
        if policy.html_profile == "edgar_flow_v1"
        else None,
        registry_sha256=checks.registry_hash,
        manual_sha256=checks.profile["manual"]["sha256"],
        passed=passed,
        strict_passed=passed and limits_checked and policy.html_profile == "legacy_strict",
        checks_complete=checks.complete,
        submission_limits_checked=limits_checked,
        files=tuple(checks.evidence),
        diagnostics=tuple(checks.diagnostics),
    )
