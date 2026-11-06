# Full conversion integration checks

Stage9 tests use actual local LibreOffice, PyMuPDF, the bounded Python runtime, Next.js and pinned Playwright/Chromium. No uploaded document is sent to an external conversion service. No premium license is required.

## Matrix and archive verification

`tests/integration/test_conversion_matrix.py` runs DOCX and PDF through both modes in supervised runtime subprocesses. The independent DOCX includes bold/italic text and deleted/inserted financial figures; acceptance must retain 123.45 and remove 999.99 without modifying the original. The independent PDF includes a ruled table and a real JPEG. Both must produce genuine browser-verified, downloadable archives.

`tools/verify_download.py` checks actual saved ZIP bytes against the fresh production download audit and authoritative PDF. It independently reads ZIP CRCs, exact root members, asset bytes/hashes and archived HTML. Standard requires exact ordered per-page native character ledgers. EDGAR requires per-page character counts and a document word multiset, alongside existing production reading-order, browser and word-position checks. These QA checks complement the production gate; they do not replace it. Run Python with assertions enabled; optimized Python is explicitly rejected.

The browser suite saves real HTTP ZIP responses and invokes that verifier. It covers both input types/modes, source-basename filenames, current-job recovery/reset, cancellation, network recovery, optional comparison, accessibility and the supplied reference PDF. Safe summaries live under ignored `var/refactor-stage9/downloads`; no private reports, source PDFs or screenshots enter user ZIPs.

The supplied three complex inputs run in Standard Mode with source/ZIP character checks. Their EDGAR cases must fail `EDGAR_CLIPPING_UNSUPPORTED` on page1 and create no archive anywhere in the attempt directory. This limitation is a recorded failure, not successful EDGAR support.

## Discovered typography defect

Real DOCX export exposed a Calibri-Italic `fi` continuation whose native `i` has zero width/no glyph and a 0.022003pt backward advance to the following glyph. Current EDGAR generation now permits only a nonsynthetic zero-width, glyph-free continuation in the same formatting span/baseline with a positive backward advance at most 0.05pt. Source text, ordering and coordinates remain unchanged; the renderer emits a warning and all browser/text/word-position checks still apply. Ordinary glyph reversals, larger backsteps and cross-span/baseline cases remain rejected. Legacy Builder defaults remain strict and are tested against the real exported layout.

## Run

From the configured root environment:

```powershell
.\.venv\Scripts\python -m pytest
cd apps/web
npm.cmd test
npm.cmd run test:ui
npm.cmd run check:format
```

The UI test command starts and stops its own production Next server. Set `CONVX_TEST_PYTHON` to a configured interpreter if needed. The archive verifier can also be run as `python tools/verify_download.py <saved-zip> <private-job-root>`. Keep job paths and identifiers private. It is a read-only QA utility, not an application service.

See [test history](test-history.md), [Stage9 recovery](stage9-resume.md) and [safe evidence](stage9-integration-regression.json) for actual results. Raw nonzero pixel differences remain visible; no pixel equivalence, SEC acceptance or universal-layout support is claimed.
