# PDF layout analysis — Stage 4

The free PyMuPDF 1.26.7 extractor creates a private, versioned Pydantic layout model; it does not generate HTML, normalize filing assets or establish SEC compliance. See [schema](layout-schema-v1.json), [regression metrics](stage4-extraction-regression.json), [PDF qualification](stage3-regression.md) and [interfaces](interfaces.md).

## Pipeline and provenance

Normal processing accepts only an unchanged generated PDF whose complete Stage 3 strict reference comparison passed. The layout records the PDF hash, validation-report hash, original/accepted DOCX hashes and renderer identity/version/environment. Failed PDF validation stops before analysis. A successful layout stops the job at `awaiting_htm_generation`; no download becomes available.

The user confirmed the fixture PDF was created by opening the accepted DOCX in Word and saving/exporting it as PDF. LibreOffice also opens the accepted DOCX and exports through its native PDF filter, in an isolated profile. Matching these operations does not make their layout engines equivalent. The free-only requirement remains binding, and the current LibreOffice export still fails all 23 Word-reference pages. No source formatting edits, reference substitution, paid SDK or Office COM service was introduced.

Diagnostic inspection can read any locally authorized PDF, including the immutable reference:

```powershell
.venv/Scripts/python -m converter.pdf_analysis.cli tests/fixtures/06749LWD4_prelim_prospectus_automated.pdf var/stage4/new-inspection.json --inspection-only
```

The output must be new. Inspection models always have `reconstruction_eligible=false` and no passing validation-report hash. This command does not run the DOCX pipeline or override its gate. Full layout JSON contains disclosure text and remains in ignored private storage; committed metrics contain counts/hashes only.

## Coordinates and source facts

Coordinates use PDF points, with origin at the top left of the unrotated crop area. Each page preserves original MediaBox, CropBox, crop offset, displayed bounds, rotation, PDF-to-layout and display/inverse matrices. Extraction temporarily sets rotation to zero in memory to avoid rotated CropBox API inconsistencies, restores it and never saves the PDF. Source SHA is checked before/after extraction.

Native block/line/span/character order, exact whitespace, glyph IDs, quads, origins, typography flags, RGB/opacity, baselines, native line advances, raw font resources, text painting modes and paint sequence are retained. A per-page character count and SHA ledger is validated on model construction and reload. No OCR, whitespace cleanup or text reflow occurs. Reading-order candidates are separate block and line graphs derived by recursive whitespace cuts; overlapping regions remain ambiguous. These graphs are hypotheses, not a replacement for source order.

Image metadata includes each placement, transform, rotation geometry, xref, soft mask and deduplicated decoded-pixel identity. No image binary or embedded font is exported here. Native vector paths retain line/curve/rectangle/quad primitives, colors, widths, fills, opacity, dash settings, clipping hierarchy and additional native properties. Link targets are recorded without following them. Annotations/widgets are captured but their unresolved appearances block reconstruction.

## Inference and limits

Paragraph candidates follow native text blocks. Font bold/italic flags and script hints are preserved as hints; underline may use native flags or conservative horizontal-vector evidence. Relative baselines support subscript/superscript candidates. Font-name collisions retain all candidate resources and a diagnostic. Repeated margin text and page-number patterns are region candidates, never removed from disclosure.

Table analysis uses native ruled-line detection; when no ruled table is found, filtered text alignment can propose borderless tables. Numeric columns and compact text matrices qualify; ordinary long prose grids are rejected. Merged cell candidates retain physical boxes, grid spans, native header metadata, border evidence and character references. Borderless classification and reading order have explicit confidence/uncertainty. This does not guarantee detection of every table, mixed ruled/borderless layout, header or footnote relationship. Later reconstruction must resolve ambiguity using accepted OOXML where needed rather than assume the candidates are exact.

Unknown Unicode mapping, unresolved bidi order, ambiguous cell grids, relevant clipping and annotation appearance produce blocking diagnostics. Exact clip geometry is retained even for harmless outer page clips; a clip fully enclosing all content needs no association inference. Native parser limitations may remain even without a diagnostic: reconstruction eligibility means this extraction gate passed, not that visual fidelity or SEC validation passed.

Configured limits bound PDF bytes/pages, text, vectors/primitives, images/decoded pixels, cells, membership work, serialized bytes and sampled process RSS. Cancellation/deadline checks bracket native operations. Native calls can allocate or stall before a Python check; OS process/network/CPU/disk isolation and deployment qualification remain Stage 11 work. The worker already runs outside the API and keeps private attempt ownership/lease checks.

## Validation and stage boundary

Tests use genuine generated PDFs for typography, whitespace, crop/rotation matrices, image transforms/soft masks, vectors, links, table geometry/merges, column reading order and scripts. Negative tests exercise stale/failed proof, model corruption, budgets and cancellation. All 23 reference pages are independently compared to native character extraction and image/vector counts. The real LibreOffice positive pipeline reaches layout analysis; the failed Word-reference pipeline writes no layout.

Stage 5 requires a separate explicit authorization. This stage implements no HTM generator, SEC validator, visual HTML comparison, ZIP package or frontend.
