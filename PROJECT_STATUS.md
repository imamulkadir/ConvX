# ConvX - Simplification Refactor Status

Current Stage: 6 - SEC EDGAR Renderer

Stage Status: completed

Last Completed Stage: 6

Next Stage: 7 - ZIP Packaging (explicit authorization required)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Work

Revised stages 1-6 are complete within their documented supported cases. One Next.js server invokes bounded local Python processes. No token, public Python API, Redis/Celery/database, paid license or external conversion service. Run `.\.venv\Scripts\python dev.py`. Read [Stage 6 recovery](docs/stage6-resume.md) and [EDGAR renderer](docs/edgar-renderer.md) on resume; do not repeat completed stages or start Stage 7 without authorization.

## Stage 6 Implemented

Separate authoritative EDGAR normal-flow HTM renderer reuses verified shared PDF layout and existing typography/merged-table/graphic primitives, with fresh source consistency checks. Deterministic SEC-compatible <=32-character .htm names, local JPG/GIF normalization, exact native JPEG preservation when possible, selectable text, source-bound local validation and actual isolated browser DOM/print/pixel verification. Internal standard/edgar mode persists through eligible retries and safe hash-bound PNG previews. Standard remains the default, independent HTML5 renderer.

The new CSS2/HTML4 formatting profile is an explicit local interpretation of EFM78, backed by the supplied manual and W3C scopes/mappings, separately hashed and reported. Default legacy strict uncertainty behavior remains intact. New-profile strict_passed and SEC acceptance stay false; whole-submission checks are separate. No legacy Word proof is forged. No page raster fallback for ordinary text. Actual missing words or major print displacement fail; all pixel differences remain measured.

Final review fixed potential CSS-looking disclosure rewriting by editing attributes only, with exact-body-text checks and regression coverage. A bounded rectangle-only exception handles actual LibreOffice page-edge rounding; nontrivial clipping still fails.

## Files Changed in Stage 6

New edgar_html.py, sec_validation/flow_profile.py, new EDGAR unit/integration tests, EDGAR/recovery/evidence docs; updated input/runtime/mode transport, validator opt-in policy/result hashes, shared browser checks, preview/UI check labels, Node/production UI tests and active test configuration. Updated AGENTS/README/runtime docs, decisions/test history and progress records. Previous Stage 5 changes remain preserved. No source fixture, user .env/data or Git metadata/history was changed.

## Tests and Evidence

Full active pytest: 380 passed, 548.20 seconds. Final focused renderer/SEC/actual Standard browser suite: 111 passed, 19.30 seconds. Focused renderer/SEC/independent EDGAR native/image/table suite: 103 passed, 9 reference-named cases deselected, 37.17 seconds. New actual major-displacement/mixed-print negative cases: 2 passed, 8 deselected, 6.51 seconds. These focused scopes overlap; they are not additional unique full-suite totals. Full collection preceded final CSS-looking-text regression and two final negative cases; focused runs verify those additions.

Final Node: 13 passed, 62.35 seconds. Production Next/Chromium browser: 6 passed, 2.8 minutes, including genuine EDGAR DOCX processing/preview, Standard DOCX/PDF, upload/recovery/deletion and responsive light/dark keyboard/axe behavior. Final small serialization/label/error changes were checked by focused Python/browser tests and format/lint checks. No mock conversion or successful ZIP. Earlier failures and fixes are retained in [test history](docs/test-history.md).

Actual production EDGAR smoke: one page, 15 source characters, zero assets, 613-byte HTM, local profile passed, strict false, zero missing printed words, maximum word-origin difference 1.6689 points. Screen channel MAE 0.06231/255, print 0.05753/255, exact pixels false. This small independent document is not evidence of complex-fixture success. See [actual evidence](docs/stage6-edgar-regression.json).

## Known Limitations

**Both supplied DOCX files and the supplied 23-page PDF fail EDGAR_CLIPPING_UNSUPPORTED on page 1.** Their genuine preparation, failure diagnostics and unchanged sources are verified. Successful EDGAR conversion for those fixtures is not claimed; Standard behavior remains available. Unsupported clipping, rotations/vertical text, annotations, overlap/unresolved table/vector/link cases fail explicitly. Mixed EDGAR print dimensions are unsupported; end-user paper settings can affect print. Local font/pixel differences, OCR and broader platform support remain limitations. No SEC acceptance or universal fidelity claim.

## Next Steps and Approval Gate

Successful current jobs stop at PACKAGING_ENGINE_PENDING; download stays disabled. ZIP packaging is Stage 7, final checkbox/minimal UI Stage 8, genuine four-path package integration Stage 9 and cleanup Stage 10. Status/checkpoint/decisions/test history are saved. All named test sessions have finished. Review, commit and push manually, then explicitly authorize Stage 7. Agents must perform no Git write operations.

Suggested Commit Message: refactor: add manual-constrained EDGAR flow rendering
