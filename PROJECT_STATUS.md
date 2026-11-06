# ConvX - Simplification Refactor Status

## Overall Status

Workflow: simplification-refactor (revised AGENTS.md; existing repository)

Current Stage: 3 - DOCX and PDF Input Support

Stage Status: completed

Last Completed Stage: 3

Next Stage: 4 - PDF Layout Analysis (explicit authorization required)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Stages

Stage 1: [existing-project audit and migration plan](docs/refactor-audit.md). Stage 2: one self-hosted Next.js application invokes bounded Python internally, without API tokens, FastAPI/Redis/Celery/database setup. Stage 3: both DOCX and PDF uploads now enter a unified authoritative PDF preparation/analysis path. Earlier implementation stages remain [historical status](docs/history/pre-refactor-status.txt) and [checkpoint](docs/history/pre-refactor-checkpoint.json), not evidence of revised-stage completion.

## Stage 3 Implemented Features

- DOCX: existing bounded ZIP/XML/macro admission, tracked-change acceptance into a separate copy, free local LibreOffice PDF export and shared analysis. Original input stays unchanged; export/provider/font-environment hashes and a Word-compatibility warning are recorded.
- PDF: extension/signature/size checks, bounded structural/object/page/geometry validation, rejection of encryption, embedded files, active content and repair requirements. Direct exact-byte private PDF copy goes to the same analyzer, without renderer calls or any DOCX conversion.
- Explicit authoritative_pdf layout mode and generated/uploaded-PDF provenance replace the routine extra Word-reference prerequisite. No self-comparison, fabricated passing gate or inspection promotion. Legacy strict analysis/rendering/package checks remain unchanged and do not authorize these new models.
- Image-only pages receive an OCR limitation with no invented text. Actual text, mixed dimensions/rotation, font/image/vector/table records use the existing extractor; Stage 4 must extend and qualify this shared model.
- The existing upload page accepts both extensions, skips DOCX-only stages/checks for PDFs, labels structural PDF validation correctly and serves hash-verified previews for either type. The final minimal redesign and mode checkbox remain Stage 8.

## Current Behavior and Limitations

Prepared documents stop at MODE_RENDERER_PENDING after real analysis. Revised HTML renderers and ZIP packaging are pending approved later stages; no final conversion or downloadable ZIP is claimed. This is input-stage completion only. Standard .html/EDGAR .htm mode selection is not implemented yet. OCR is not installed/integrated. Complex layout/font/annotation issues remain explicit in private layout diagnostics; input preparation is not rendering qualification.

Both supplied DOCX variants and the 23-page PDF reach shared analysis, with unchanged source hashes. Accepted DOCX content matches the supplied accepted baseline. Historical LibreOffice-vs-Word comparison still failed all 23 pages; those tests/evidence remain unchanged and do not block the revised input contract. LibreOffice layout equivalence to Word is not verified. SEC styling/character ambiguities and the positive whole-chain download remain unqualified.

## Files Changed

New converter input_pipeline.py and pdf_admission.py; runtime.py selects source extension and invokes unified preparation; pdf_analysis/extract.py exposes the shared authoritative entry and layout/models.py records its distinct provenance mode. Web runtime/upload helpers/components support PDF and verified previews. Added tests/runtime/test_inputs.py and expanded real Node/browser tests. Updated README, AGENTS, runtime/pipeline documentation, decisions, test history, Stage 3 evidence and these progress records. No new dependencies or paid licenses. User .env, prior data, fixtures and Git history remain untouched.

## Testing

Final fast focused Python input/admission/runtime/PDF-analysis/revisions: 83 passed, 3 native/reference cases deselected. Real supplied DOCX variants both passed the separate native regression rerun; final direct supplied PDF rerun passed (28.24 seconds). Legacy renderer/packaging compatibility checks: 89 passed. Initial broader focused run: 85 passed before the additional security regression; subsequent inline-action/outline guard defects were fixed and retested. Node: 12 passed. Production-build browser checks: 5 passed, covering actual DOCX/PDF uploads, native export/shared analysis, unchanged sources and verified PDF review. No mocked engine or successful ZIP simulation. See [test history](docs/test-history.md) and [Stage 3 evidence](docs/stage3-input-regression.json).

## Startup and Progress Tracking

Run `.\.venv\Scripts\python dev.py` and open its printed URL. No token or independently started backend. See [setup and limits](docs/simplified-runtime.md).

Status/checkpoint/decisions/test history synchronized. Await review/manual commit/push and explicit Stage 4 authorization. Stage 4 will qualify/extend shared PDF layout; Stages 5-7 implement the two renderers and packaging, Stage 8 final UI, Stage 9 four-path integration and Stage 10 cleanup. Single Node instance only; public access/rate controls, stronger OS sandboxing and broader OS/browser/font qualification remain pending. No automatic stage advancement or Git writes.

## Suggested Commit Message

refactor: unify DOCX and PDF input preparation
