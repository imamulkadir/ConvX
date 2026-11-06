# ConvX - Simplification Refactor Status

Current Stage: 9 - Full Integration Testing

Stage Status: completed

Last Completed Stage: 9

Next Stage: 10 - Final Cleanup and Optimization (not authorized)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Work

Revised stages1-9 complete within documented supported cases. One Next server invokes bounded local Python. Start `.\.venv\Scripts\python dev.py` and use its printed URL; restart after app updates. Minimal DOCX/PDF form, default-off EDGAR checkbox, real progress/ZIP download and optional comparison remain available. No token, separate backend, broker/database, premium license or external conversion service. See [interface](docs/simple-interface.md), [integration verification](docs/integration-testing.md), [safe evidence](docs/stage9-integration-regression.json) and [current recovery](docs/stage9-resume.md).

## Stage9 Implemented

Added independent verification of actual saved HTTP ZIPs against fresh production download proof and authoritative PDF text. QA rereads CRC/exact root document/assets/byte hashes and archived HTML; Standard requires exact ordered per-page native character equality, EDGAR per-page character counts and a document word multiset in addition to production flow/word-position checks. Optimized Python is explicitly rejected by this assertion-based QA utility. No new service or production gate.

New four-path bounded-runtime subprocess matrix exercises both inputs/modes. Independent DOCX contains bold/italic text and accepted deleted/inserted financial figures; independent PDF contains a ruled table and genuine JPEG. Source hashes, tracked-change acceptance, actual browser verification, source-basename archives, correct internal extension/assets and corrupted saved-ZIP rejection are checked. Supplied Standard cases now check archived source text; supplied EDGAR failures check recursively that no ZIP exists. Browser tests audit actual saved responses, not mocked completion.

The new DOCX exposed a native Calibri-Italic zero-width ligature continuation with0.022003pt backward advance. Current EDGAR renderer narrowly accepts only same-span/baseline nonsynthetic zero-width glyph-free continuations up to0.05pt, retaining source text/order/coordinates and warning the user. Ordinary/larger/cross-run reversals remain rejected. Legacy Builder default remains strict and is verified against the actual exported layout. All browser/text/word/pixel gates remain mandatory.

## Files Changed

New tools/verify_download.py and tests/integration/test_conversion_matrix.py; updated active pytest paths, generator/EDGAR renderer, warning copy, generator guards, supplied input/EDGAR regressions and real UI download tests. Updated AGENTS/README/runtime/interface, decisions/test history/integration/recovery/evidence and root progress records. No dependency, fixture, user .env/data or Git metadata changes; no Git writes.

## Actual Verification

Full active Python suite435passed,0failed,729.04sec. It began before the narrow ligature patch; final affected paths were explicitly rerun: generator guards plus four actual runtime paths45passed73.25sec; current EDGAR browser cases7passed37.92sec (3supplied cases separately covered by full run). Node16passed99.46sec. Production Next/Chromium browser11passed4.7min, with6 actual saved ZIPs independently verified, including both inputs/modes,23-page reference PDF and network recovery. No mocked conversion/download or fabricated reference evidence.

Initial new matrix3passed1failed57.48sec exposed the real ligature defect; second4passed113sec and final45-case run passed after the fix. Full history retains the failure. All3supplied Standard inputs produce23-page archives with exact authoritative text: each DOCX84,555characters, direct PDF85,798characters. DOCX-to-PDF authority is LibreOffice output; Microsoft Word equivalence is not claimed. All3supplied EDGAR inputs fail EDGAR_CLIPPING_UNSUPPORTED page1 without ZIP. Reference PDF raw screen max MAE9.370503/255 and print0.945788 remain nonzero.

Changed Python Ruff/check+format, web Prettier and clean-environment pip check passed; initial formatting findings corrected. Optimized-Python QA CLI returned the expected safe rejection. Final fixture/context/history checks are recorded in test history. No exact-pixel or SEC acceptance claim. All test sessions finished; QA-owned servers stopped automatically.

## Known Limits and Next Steps

Complex EDGAR clipping, unsupported geometry/mixed EDGAR print/OCR/platform, local fonts/LibreOffice compatibility and single Node limits remain. Stage9 verifies supported cases and honest unsupported failures, not every possible document. Current runtime report.stage remains7 intentionally, reflecting the implemented packaging capability rather than development stage.

Stage10 cleanup/optimization is the only remaining stage and requires explicit user authorization. Review, commit and push manually. Do not advance automatically. All durable records and current recovery/evidence are saved.

Suggested Commit Message: test: verify conversion matrix and saved ZIP integrity
