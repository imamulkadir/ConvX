# Pixel-level visual validation - Stage 7

`converter.visual_validation.compare_visuals` compares a generated PDF against actual Chromium print and screen rendering of its HTM/assets. It requires unchanged, complete passing strict PDF evidence and a fresh matching strict local SEC result with supplied whole-submission context. Gate hashes, source/file hashes, policy and browser/font environment are recorded. No earlier failed or missing gate is promoted by a good-looking screenshot.

Current prospectus conversion still fails the Word-reference PDF gate. Current generated inline-styled candidates also fail unresolved CSS/MANY permissions in Stage 6. They do not enter production visual comparison. This stage implements the engine and diagnostic evidence; it does not resolve those earlier incompatibilities.

## Installation and diagnostic use

Free dependencies are pinned in the package and resolved environment: Playwright 1.64.1, its Chromium revision 1248 / version 156.0.8078.4, NumPy 2.5.4, PyMuPDF 1.26.7 and Pillow 13.0.0. Browser installation is separate from runtime and does not receive a document:

```powershell
.venv/Scripts/python -m pip install -r services/api/requirements-lock.txt
.venv/Scripts/python -m pip install --no-deps -e packages/converter
.venv/Scripts/python -m playwright install chromium
```

The default matching Playwright cache is used; optional `PLAYWRIGHT_BROWSERS_PATH` is resolved before launching the isolated child. It never falls back to an arbitrary system browser. Browser version is checked against its packaged manifest, and the actual executable SHA and revision are recorded.

Explicit read-only diagnostic comparison is available for safe HTM that still has permission uncertainty:

```powershell
.venv/Scripts/python -m converter.visual_validation.cli SOURCE.pdf CANDIDATE.htm NEW_PRIVATE_OUTPUT --assets image001.jpg --inspection-only
```

Omit `--assets` when no images are referenced. Input/output paths must be locally authorized, and output must be a new directory. Inspection requires the source-byte safety/asset checks to complete; it allows only specified unresolved permission diagnostics, never active/remote/malformed resource content. It always reports `mode=inspection_only`, no passing gate hashes and `strict_passed=false`, even for an exact comparison. The result model rejects attempts to promote inspection by changing the strict flag. CLI exit zero means diagnostic measurements agree; it cannot authorize a ZIP or SEC-ready claim.

## Controlled Chromium rendering

The parent captures verified HTM/assets as bytes, copies them into a private child workspace, and runs a trusted fixed Python module through the existing deadline/RSS/output/artifact-bounded process runner. Cancellation and owned-descendant cleanup are preserved. The runner now tolerates disappearing native temporary files without a size-monitor race.

Chromium is headless with its sandbox enabled, document JavaScript disabled, service workers blocked and downloads disabled. Requests are fulfilled only from the exact captured virtual HTTPS manifest; other requests are aborted, while restrictive CSP also blocks document script/connect/frame/object/remote-image behavior. Links are not followed. Background-networking features are disabled. No local file URL or general filesystem server is exposed. This is application-level resource isolation plus Chromium's sandbox; OS egress/CPU/disk/job isolation and Linux service qualification remain Stage 11 work.

Media is print; locale en-US, timezone UTC, light colors, reduced motion, software rendering flags, fixed viewport and device scale are recorded. DPI is 96 or 144. Print PDF uses the source page dimensions, zero print margins, background graphics and no headers/footers. Playwright print-size units are inches derived from PDF points, not unsupported pt arguments.

The engine also captures browser screen clips of each source-sized page container. Containers must have matching extents, x=0 and consecutive, nonoverlapping y positions. Single-page content can use its viewport; ambiguous continuous multi-page flow fails screen mapping. Full-page capture enables clips beyond the first viewport. Mixed-size/rotated source pages are explicitly unsupported by this fixed print profile and fail before rendering. Neither screenshot nor source raster is resized, translated, blurred or cropped to conceal an error.

## Independent content and geometry checks

Chromium's printed PDF provides independently extracted selectable text. Source and rendered text must agree exactly; glyph segmentation is reported separately. Character origins/bounds, font names excluding subset prefixes, size, bold/italic, color/alpha/direction, page dimensions and native text-paint metadata are compared. Font resource/size sets are diagnosed even when text cannot be aligned. Native line counts are evidence rather than an automatic semantic claim. Per-character displacement boxes are retained up to a global limit, with truncation explicit; alignment-dependent metrics are meaningful only when `text_alignment_available=true`.

Image placements/transforms/decoded identities, vector geometry/paint and embedded font-program hashes are compared independently. Fonts are not treated as equivalent merely because they have similar names or metrics. System/user font bytes are fingerprinted before and after comparison; actual print font evidence is separately checked. Hidden/nonrendering text is diagnosed, while whitespace-only formatting nodes are counted separately. Full-page disclosure rasterization cannot pass the selectable-content comparison.

## Pixel metrics and strict decisions

Every corresponding page gets source-PDF, browser-print and browser-screen RGB comparisons. Raw changed-pixel count/fraction and mean absolute channel error are retained. The difference heatmap marks unresolved pixels red and verified print antialias edge candidates amber; overlays retain the source/rendered context. Missing/extra pages, overflow, missing images, denied requests and incomplete evidence all fail.

Print antialias classification is intentionally narrow: neutral intermediate edge tones, unchanged dark cores, local black/white edge support and source text bounds. Automatic explanation additionally requires exact content/geometry/paint and embedded font-program agreement, with no image on the page. Colored graphics, image changes and structural mismatches are never explained away by this method. Font programs/layout that cannot be proven equivalent leave differences unresolved.

Screen pixels do not inherit a print-geometry waiver. Screen antialias candidates are counted for diagnosis, but are not suppressed without separate proof of screen geometry. This matters in actual tests: an identical Chromium print PDF can still disagree with the screen's glyph rasterization. The observed smoke fixture had zero print differences but 1,169 unresolved screen pixels, and correctly failed strict visual validation. This is not hidden by a percentage threshold or an image normalization pass.

`comparison_passed` requires all page/content/geometry/print/screen checks to agree and complete managed evidence. `strict_passed` additionally requires production mode and the bound earlier gates. SEC acceptance remains unconfirmed. A successful isolated diagnostic or a negative-regression test passing is not successful prospectus conversion.

## Private artifacts and bounds

Each new evidence directory contains `visual.json`, source/print/screen page PNGs, print/screen heatmaps and overlays. `browser/` contains captured inputs, Chromium print PDF, screen clips and private control metadata. Browser error details, if needed, stay in private `browser-error.json`; stdout contains only static codes/phase/type. No disclosure excerpts are placed in public metrics/logs. All these intermediates are excluded from any eventual filing ZIP.

Budgets cover input HTML/assets, source/print PDFs, page/aggregate raster pixels, text, DOM nodes, process RSS/time, geometry records and managed PNG evidence. Evidence truncation is explicit and cannot pass strict validation; comparisons continue page by page so failures are not hidden by missing heatmaps. The evidence-byte count covers managed comparison PNGs; private input/print/browser intermediates have separate input/PDF/process artifact limits. Native parsing, font hashing and decoding remain cooperative operations needing OS isolation in deployment. Peak memory and image dimensions are not assumed small merely because compressed files are small.

No source correction is applied automatically. Current discrepancies would require unapproved formatting or unproven font/geometry changes; the report records that no eligible evidence-backed correction was available. Font/image readiness is stabilized before rendering. Repeatedly rasterizing, deleting text or relaxing gates is not a correction strategy. Later implementation/integration work must revalidate SEC and visual evidence after any actual approved edit.

## Integration, regression and handoff

The worker enters `comparing_formatting` only after prior file checks and the visual engine rechecks their strict evidence. Failed visual comparison returns `VISUAL_STRICT_VALIDATION_FAILED`; missing Chromium is blocked with an explicit code. A passing result stops at `blocked / awaiting_packaging / PACKAGING_ENGINE_NOT_AVAILABLE`; no ZIP/download completion exists. The owned validation API can report fidelity evidence; raw artifacts remain private. Browser resource settings are in `.env.example`.

Tests use real Chromium, genuine PDFs, raw raster/geometry checks, stale gate failures, safety interception/CSP, limits, cancellation and no-download lifecycle. The 23-page mandatory Word PDF is compared against a deliberately empty 23-page document solely as a negative inspection regression: all 85,798 source characters remain accounted for and every page reports missing disclosure. This document is not a conversion result or a replacement for the generated-PDF gate. Original fixtures are unchanged. See [Stage 7 metrics](stage7-visual-regression.json), [test history](test-history.md) and [status](../PROJECT_STATUS.md).

Stage 8 packaging requires separate explicit authorization. No frontend/UI, final package, authorized SEC TEST filing or Linux production qualification was added.

Primary tooling references: [Playwright browser version coupling](https://playwright.dev/python/docs/browsers), [page PDF/screenshot API](https://playwright.dev/python/docs/api/class-page), [browser context resource routing](https://playwright.dev/python/docs/api/class-browsercontext). These describe tooling, not SEC permission or acceptance.
