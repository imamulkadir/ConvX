# ConvX - Simplification Refactor Status

## Overall Status

Workflow: simplification-refactor (revised AGENTS.md; existing repository)

Current Stage: 4 - PDF Layout Analysis

Stage Status: completed

Last Completed Stage: 4

Next Stage: 5 - Standard HTM Renderer (explicit authorization required)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Stages

Stage 1 audited the existing project; Stage 2 consolidated the runtime into one Next server with bounded internal Python processes; Stage 3 added DOCX/PDF preparation and generated/uploaded-PDF authority. Stage 4 now extends and verifies the common layout and retains real private image resources. See [audit](docs/refactor-audit.md), [runtime](docs/simplified-runtime.md) and [shared layout contract](docs/shared-layout.md). Earlier implementation status/checkpoint remain archived under docs/history.

## Stage 4 Implemented Features

- Current-source provenance checks before authoritative analysis; no fabricated Word-reference pass or promotion of inspection. One extraction model serves both future output modes.
- Independent native verification of exact text/count/order, glyph origins/bounds, font resource membership and span typography, image resource association/dimensions/transforms, page geometry/rotation and image/vector counts. Typed source/page verification survives serialization; mismatches fail with explicit diagnostics.
- Bounded real native image payloads and separate soft masks in private per-attempt resources, with deterministic safe basenames, sizes and SHA-256. Repeated placements share assets and JPEG bytes are retained without recompression. No unlicensed font embedding or page screenshots.
- Existing tables/merged-cell ledgers, paragraph/line relationships, rotation/crop matrices, vectors/paint order, header/footer/page-number candidates and reading orders remain shared. Summary reports add verification and font/image/vector/table/resource counts.
- Explicit inline-image association and shading limitations; no invented resources or silently omitted unsupported paint.

## Files Changed

New pdf_analysis/verification.py and resources.py, additive typed fields in layout/models.py, policy resource limits, authoritative extraction/provenance checks and summaries, and input_pipeline integration. New tests/unit/test_shared_layout.py; Node test diagnostics improved. Updated README, AGENTS, runtime/shared-layout docs, decisions/test history, Stage 4 evidence and progress records. No new dependencies, paid licenses or Git writes; original fixtures/user data unchanged.

## Testing

293 unit/runtime/regression Python tests passed (228.73 seconds), including real supplied DOCX variants/PDF and preserved legacy checks. New shared-layout suite: 20 passed. Final Node suite: 12 passed; initial isolated PDF case failed once, then focused/full reruns passed, root cause not established. Production-build browser suite: 5 passed (2.0 minutes). Real direct PDF output: 23 verified pages, 85,798 characters, 13 fonts, 5 placements, 4 extracted resources/123,008 bytes, 4,847 vectors and 8 table candidates; unchanged source. These are extraction checks, not HTML visual fidelity. See [test history](docs/test-history.md) and [evidence](docs/stage4-layout-regression.json).

## Known Limitations and Pending Work

Jobs still stop at MODE_RENDERER_PENDING. Standard/EDGAR rendering, mode selection, mode-specific ZIP and final minimal UI remain later stages; no final conversion/download success is claimed. Semantic tables/headers/footnotes, arbitrary clipping/annotations, bidirectional order, inline payloads, shading and font licensing remain explicit uncertainty. Native consistency does not prove every vector parameter or pixel-perfect HTML. OCR remains unavailable. Historical Word comparison failed 23 pages and is unchanged. The Node test's isolated initial failure is recorded without an invented explanation.

Single Node instance only; stronger OS isolation, public access/rate controls and broader platform/font/browser coverage remain unqualified. Partial private assets from failed attempts are retained only until normal cleanup, never packaged as successful output.

## Startup and Resume

Run `.\.venv\Scripts\python dev.py`, open its printed URL and upload DOCX/PDF. No token or separate backend. Status/checkpoint/decisions/test history synchronized. Await manual review/commit/push and explicit Stage 5 authorization; do not advance automatically. Stage 5 implements Standard HTML5, Stage 6 EDGAR, Stage 7 packaging, Stage 8 minimal UI, Stage 9 integration and Stage 10 cleanup.

## Suggested Commit Message

refactor: verify shared PDF layout and retain image resources
