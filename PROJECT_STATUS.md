# ConvX - Current Project Status

Current Stage: 10 - Final Cleanup and Optimization

Stage Status: completed

Last Completed Stage: 10

Next Stage: None - ten-stage refactor and authorized EDGAR repair complete

Last Updated: 2026-11-07 (Asia/Dhaka)

## Current result

The reported EDGAR failure is fixed for all three supplied complex regression documents. The former partial-page clipping guard and flow partitioner could not reconstruct the source layout. A separate source-associated rectangular CSS2 strategy now preserves clipping, native tables/rules/images and selectable text. Standard mode and original strict/flow-profile defaults remain intact.

The actual configured running app converted the previously failing23-page DOCX and served a saved, independently verified1,574,472byte ZIP: one HTM and four JPG files, all at the root. Source characters, actual printed words, assets and CRC passed; uploaded source remained unchanged. See [safe evidence](docs/edgar-clip-regression.json).

## Running the application

Run `.\.venv\Scripts\python dev.py` from this repository and open its printed URL. The development app was left running at http://127.0.0.1:3000. Upload DOCX/PDF, optionally enable EDGAR, convert and download. One Next server invokes bounded local Python processes. No API token, separate backend, Redis/Celery/database or paid conversion license is required.

## Implemented repair and files

Added edgar_clips, edgar_layers, edgar_reflow, edgar_symbols, edgar_spacing, edgar_words and sec_validation/layer_profile. Changes also cover current conversion/validation/packaging/runtime modules, download QA, UI result notes, independent/source regressions and persistent docs. Source-derived reflow and character recovery are independently verified. Actual printed PDFs remain private evidence, freshly checked during packaging/download/QA. Forged reflow targets and erased financial figures fail. Supervision failure preserves safe diagnostics and revokes any prematurely published completion.

No dependencies, source fixtures, user configuration or Git metadata changed. No Git writes occurred.

## Final verification

- Full Python: **460 passed**, 0 failed,763.76seconds.
- Node server: **15 passed**, 0 failed,100.90seconds.
- Production build and real Chromium UI: **12 passed**, 0 failed,5.0minutes, including supplied DOCX EDGAR conversion and saved-download QA.
- All three supplied complex EDGAR inputs now produce verified packages; Standard and four-path runtime regressions pass.
- Actual running-app HTTP conversion/download:23pages,84,555characters,oneHTM/fourJPG,source unchanged and independent source/print/assets/CRC checks passed.

Final context/fixture/history/hash/format checks are recorded in [test history](docs/test-history.md). Prior Stage10 results remain historical in [final review](docs/stage10-review.md).

## Remaining limitations and pending tasks

Vertical sidebar text deliberately moves into horizontal lines in vacant source-derived page bands, with visible warnings; full originally clipped text is retained. Forbidden external destinations become inactive with labels preserved. Measured font/pixel differences remain. No exact fidelity, Word equivalence, universal support, legacy strict proof or SEC acceptance is claimed. Curved/unsupported clipping and other unsupported geometry fail without a ZIP. OCR is not integrated; public hosting and complete hostile-document OS sandboxing remain unqualified.

No pending implementation or next stage. Read [current recovery](docs/edgar-fix-resume.md), [repair details](docs/edgar-rectangular-layout.md), [decisions](docs/decisions.md) and [limitations](docs/limitations.md) before future work.

Suggested commit message: `fix: preserve clipped EDGAR layouts with verified text and ZIP output`
