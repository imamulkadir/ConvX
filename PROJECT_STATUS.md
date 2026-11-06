# ConvX - Simplification Refactor Status

Current Stage: 7 - ZIP Packaging

Stage Status: completed

Last Completed Stage: 7

Next Stage: 8 - Simplify Frontend (explicit authorization required)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Work

Revised stages 1-7 complete within documented supported cases. One Next.js server invokes bounded local Python. Start `.\.venv\Scripts\python dev.py`; no token, separate API, broker/database, paid license or hosted conversion service. Supported DOCX/PDF conversions now produce actual downloadable ZIPs. Read [Stage 7 recovery](docs/stage7-resume.md) and [ZIP contract](docs/zip-packaging.md) on resume. Do not repeat completed work or start Stage 8 automatically.

## Stage 7 Implemented

Added separate typed source-verified-mode-zip-v1 packaging alongside unchanged legacy strict Word/SEC gates. Standard ZIP contains source-basename .html and exactly referenced local assets; EDGAR contains a deterministic SEC-compatible .htm and JPG/GIF. External ZIP retains source basename, including Unicode/spaces/apostrophes. All members root-only, exact source-qualified HTML bytes retained, no PDF/DOCX/JSON/CSS/JavaScript/reports/captures/unused files. Canonical deterministic stored ZIPs support UTF8 entries with byte/count limits and full header/CRC/payload/reference validation.

Every download freshly checks request/mode/attempt/source/PDF, HTML/assets, actual browser comparison/captures and archive contents. Existing capability, expiration, cancellation and state/version guards remain. Successful processing reports packaged and exits0; Next exposes completed/download. Missing/unsafe archives fail409; RFC5987 filenames escape punctuation correctly. Source-integrity/failure prevents final completion. No legacy strict or SEC acceptance is granted by a current package.

Robustness: a real Node run exposed a finished failed-input result stranded as running after a swallowed publication exception. The original OS error was not captured. Added bounded Windows rename retries and explicit terminal publication-failure fallback; actual CreateFileW reader-lock, cancellation and final production tests pass. No original error code was invented.

## Files Changed

New packaging/current.py and real current archive/offline/tamper tests; updated artifact dispatch/audit, input pipeline/runtime completion, Node secure download/publication handling, Node/production UI tests and input/EDGAR integration expectations. Updated AGENTS/README/runtime/renderer/ZIP docs, decisions/test history, archive evidence/recovery and progress records. Existing fixtures, user .env/data and Git metadata/history preserved; no Git writes.

## Tests and Evidence

Full active Python: 431 passed,0 failed,559.47seconds. Targeted current+legacy package/gates:101 passed,21.32seconds. New current packaging/offline suite:48 passed,9.21seconds. Focused scopes overlap. Full Python precedes the final Node-only publication fix; final Node/browser runs verify that fix.

Final Node:15 passed,0 failed,80.12seconds, including actual ZIP downloads, tamper/missing-file rejection, Unicode/apostrophe names, EDGAR retry and real Windows reader lock. Final production Next/Chromium UI after the fix:6 passed,0 failed,2.4minutes; genuine EDGAR DOCX/Standard DOCX/PDF ZIP saves, source review, recovery/deletion, invalid input and responsive light/dark keyboard/axe. Earlier pre-fix Node14 run13passed/1failed (stranded state), retained in test history; first production UI6passed in3.5minutes. No mocked conversion/download.

Actual supplied PDF Standard ZIP:2,311,996bytes, exactly one2,188,398-byte .html and four images;23pages and85,798characters. Independent EDGAR DOCX ZIP741bytes contains independent.htm613bytes. Actual root names, CRCs and SHA verified. Extracted renamed Standard/EDGAR documents open offline with selectable source text and expected image pixels. See [evidence](docs/stage7-zip-regression.json).

## Limitations

All three supplied complex fixtures still fail EDGAR_CLIPPING_UNSUPPORTED page1 and receive no successful EDGAR ZIP; their Standard conversions package successfully. Local EDGAR CSS/character interpretation is not filing acceptance; strict_passed and sec_acceptance_confirmed stay false. Existing font/pixel differences, unsupported geometry, mixed EDGAR print sizes, OCR and platform qualification limits remain. Stored archives trade larger size for simple bounded mechanics; fresh audit adds local processing time. Single Node instance and public deployment isolation remain unqualified.

## Next Steps

Stage 8: final minimal upload/EDGAR-checkbox interface. Stage 9: broader four-path integration after that interface. Stage 10: cleanup/optimization. Status/checkpoint/decisions/test history are saved; all named test sessions finished. Final fixture/hash/link/format checks follow in test history. Review, commit and push manually, then explicitly authorize Stage 8. Agents must perform no Git write operations.

Suggested Commit Message: refactor: package verified Standard and EDGAR ZIP downloads
