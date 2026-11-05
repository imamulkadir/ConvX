# HTM reconstruction - Stage 5

`converter.html_generator.generate_htm` implements PDF-first normal-flow reconstruction. It consumes an eligible schema-v1 layout, the unchanged source PDF and the exact passing strict PDF report. It produces a private `candidate.htm`, source/layout/content hashes, graphic asset requests and diagnostics. It does not accept an inspection model, failed PDF proof or stale source. No paid component is used.

## Supported reconstruction

Whitespace partitioning builds independent columns and horizontal bands from source coordinates. Inline-block DIV columns and ordinary flow DIV rows reserve measured point dimensions and spacing. Paragraph lines preserve source wrapping with `white-space:pre`; each character remains a text node, with source origin-to-origin advances represented as inline widths. No disclosure spaces, line-break characters, headings or table labels are invented. Margins/indents and alignment use measured coordinates rather than guessing a paragraph's alignment setting. Page extents and print page breaks are explicit.

FONT and B/I/U/SUP/SUB preserve observed size, RGB, emphasis and script hints. Script source baselines and font sizes override browser default scaling. Standard Times/Helvetica/Courier families map to Times New Roman/Arial/Courier New; other safely encoded names retain the extracted family. Font availability, glyph metrics and baselines still require actual browser measurement. Numeric serialization uses 12 significant digits; the original model retains full native precision.

Resolved ruled tables become actual TABLE/TR/TD markup with point widths/heights, zero padding/spacing, individual source border widths/colors, and physical rowspan/colspan relationships. Table disclosure is emitted once using canonical character membership. No TABLE descends from another TABLE. Candidate table rows/cells require consistent grids, complete row boundaries, unique membership and nonoverlapping text contained within each cell. Uncertain borderless tables require semantic resolution before output. Header names from detection never become invented disclosure.

Horizontal/vertical opaque solid rules and supported standalone rectangular graphics use permitted elements and inline borders/background. Underline and table border evidence is consumed explicitly rather than emitting duplicate drawing objects. Interlocking/overlapping content, arbitrary curves, unsupported compositing, strokes/dashes/opacity, rotated pages/text/images, uncertain clipping and unsupported image sources fail with explicit diagnostics. These features are not silently discarded or rasterized as disclosure.

PDF images produce deterministic root-relative JPG requests with source PDF hash, asset xref, soft-mask xref and all placement IDs. Repeated placements reuse the same request. No image binary is fabricated. Asset normalization is a separate pending pipeline capability; candidates with requests cannot be previewed/published as complete until every image is materialized and validated. Graphic-only rasterization of complex vector paths is not implemented here and currently fails explicitly.

## Content, links and safety

Character IDs and text must match the complete native ledger exactly once. The serialized HTM is reparsed and its BODY text must exactly equal emitted text, including whitespace and Unicode. Non-table disclosure order must match the extractor's proposed line graph; table content follows resolved rows/cells. An unresolved reading order fails instead of silently interleaving columns. Inferred source semantics remain provisional pending visual/OOXML verification.

Only generated literal tags/attributes are emitted; no input markup is copied. Text/attributes are escaped by lxml; output bytes are ASCII with numeric Unicode references. C0/C1 controls (except tab/line-break text) and surrogate characters fail. Unicode/manual character mapping is explicitly pending Stage 6. There are no scripts, stylesheets, fonts, SVGs, absolute positioning, CSS transforms or remote images. The generator is not a general-purpose HTML sanitizer.

Links are associated with disclosure characters. This candidate profile conservatively permits literal HTTPS references under `www.sec.gov/Archives/edgar/data/` and internal page/nearest-line bookmarks. It rejects unsupported schemes/hosts, traversal, encoded targets and arbitrary external/local attachments. Unsupported links fail without dropping their meaning. Nearest-line destinations carry geometry warnings; final link/fragment resolution belongs to Stage 6. This narrow generation contract does not assert all other historical EDGAR link constructs are prohibited.

Generation bounds total characters, items/page, partition work, nodes, bytes and sampled process RSS. Deadline/cancellation checks cover pages, leaves and publication. An output must be a new private `candidate.htm`; exclusive atomic hard-link publication prevents overwrite races and preserves existing files. Failed preflight produces diagnostics with no partial candidate. DOM/serialization allocate before some checks; production OS memory/CPU/disk isolation remains Stage 11 work. No endpoint serves these private files yet.

## Compliance and fidelity boundary

The supplied manual's sections 5.2.2.2-.5 explicitly supply the tag vocabulary, forbid SPAN/TBODY/nested TABLE, and list STYLE for MANY elements. The candidate profile is documented in [profile evidence](compliance/efm-v78.stage5-candidate.json); it is a generator contract, not an approved SEC rule registry. CSS property/value permissions, MANY scope and character mapping remain unresolved. Consequently every generated result explicitly sets SEC compliance, visual fidelity and strict validation to false. No SEC-ready or pixel-perfect claim is made.

Stage 6 must resolve/approve a versioned rules profile and validate actual HTM, references and assets. Stage 7 must render in Chromium and compare all pages against the generated PDF, including font searchability, baselines, wraps, borders and page breaks. Any observed incompatibility must fail strict validation. Candidate generation passing is evidence of implemented reconstruction and content accounting, not proof of visual equivalence.

## Integration, evidence and next stage

The worker now executes `generating_htm` only after PDF/layout gates pass, persists `html_generation` in the owned attempt report and stops at `blocked / awaiting_sec_validation` with `SEC_ENGINE_NOT_AVAILABLE`. Existing Stage 4 `HTML_ENGINE_NOT_AVAILABLE` jobs may be explicitly resumed; there is no automatic replay. Final completion and download remain unavailable. CLI exit zero means candidate generation only; inspect its report before drawing any downstream conclusion.

The user's Word Save As PDF provenance and free-only requirement remain unchanged. The genuine LibreOffice one-page baseline exercises the complete current pipeline through HTM. The 23-page Word fixture still fails PDF validation on every page and produces neither layout nor HTM. Reconstruction tests use genuine synthetic PDFs with self-comparison only to isolate engine mechanics; they do not qualify DOCX rendering or replace the mandatory fixture.

See [test history](test-history.md), [Stage 5 metrics](stage5-reconstruction-regression.json), [layout analysis](pdf-layout-analysis.md), [Word qualification](stage3-regression.md) and [project status](../PROJECT_STATUS.md). Stop after Stage 5; Stage 6 requires explicit authorization.
