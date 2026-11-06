> FINAL HANDOFF: Stage 5 is COMPLETED. Full Python 340 passed; focused Windows/runtime/Standard 31 passed; Node 12 passed; final production UI 5 passed (1.8 minutes). No tests remain running. Current root status/checkpoint supersede intermediate progress descriptions below. Stop before Stage 6 until explicitly authorized. See [Standard renderer](standard-renderer.md) and [final evidence](stage5-standard-regression.json).

# Stage 5 recovery checkpoint - 2026-11-06

User warned the five-hour usage window is nearly exhausted and requested durable status before reset. Stage 5 is now completed; intermediate investigation below is retained as history. Do not start Stage 6. No Git writes, branches, staging, commits or pushes; user handles Git manually. Do not spawn agents (not authorized). Preserve all existing changes and user fixtures/data.

## Read first

Read AGENTS.md, PROJECT_STATUS.md, .agent-checkpoint.json, latest decisions/test history and this note. Inspect read-only Git state. Revised stages 1-4 complete; Stage 5 Standard HTM Renderer is the active task. Do not restart or repeat completed audits.

## Implemented Stage 5

- New packages/converter/standard_html.py: actual HTML5 with embedded CSS, page sections, native SVG paint serialization with text_as_path=False, selectable text, exact model text/geometry/source binding, scoped SVG IDs/fragment references and local extracted JPG/PNG/GIF/WebP assets. No page raster replacement, JavaScript/external CSS/fonts or SEC restrictions.
- Native SVG serialization is necessary to retain thousands of clipping scopes beyond the shared model's scope associations. Both engines still use the same verified PDF model; no independent DOCX/PDF conversion engines.
- Common PostScript family aliases use local fonts. No font files are redistributed. Measured differences remain explicit, no pixel-perfect claim.
- Synthetic spaces from PDF TJ gaps are inserted only when the verified model marks them synthetic; explicit source-derived SVG positions keep real glyphs fixed. Prefer synthetic insertion before matching an adjacent real space (fixed page 16 of native DOCX).
- Authoritative shared analysis defaults to preserve_clipped_text=True, clearing native TEXT_MEDIABOX_CLIP. This retains clipped source paint text that SVG serializes (LibreOffice margin paint was previously absent from default rawdict). Legacy inspection/strict pipeline defaults remain False. Verification uses the same declared extraction flags. Existing source clipping is preserved; this is not a redaction tool.
- New standard_visual.py: isolated pinned Chromium, scripts disabled/network restricted, actual DOM text/page checks, screen screenshots, named-size print PDF, all-page raw pixel differences, overlay and actual print-difference PNGs. Actual browser artifact hashes bind previews. No altered/blurred metrics or fabricated successful ZIP.
- Browser worker writes bounded control.json separately from stdout: inherited FORCE_COLOR/NO_COLOR notices broke JSON parsing. Worker strips unrelated Node preload hooks and FORCE_COLOR. Runtime resolves the host Chromium cache before HOME isolation.
- Input pipeline defaults Standard, generates actual HTML and real browser comparison, then stops at PACKAGING_ENGINE_PENDING (ZIP is Stage 7; EDGAR Stage 6; final UI Stage 8). New previews serve hash-bound actual HTML captures via existing safe PNG endpoint, checking current HTML/assets/capture digests.
- Release the persisted glyph model and gc.collect() before Chromium to reduce process-tree memory. Keep the existing bounded 1.5 GiB/320-second runtime; no extra infrastructure.
- UI labels actual browser rendering, hides SEC checks for Standard, offers real HTML preview. Choose-button color transition disabled after axe caught transient low contrast during dark-theme switching. Final minimal redesign is not implemented early.
- Discovered real Windows progress-file replace sharing failure: failed job left progress.part=accepting_revisions while progress.json=validating; identical DOCX later passed admission. pipeline.write_report now retries only Windows sharing/access-denied rename failures for at most one second, retaining the prior complete JSON. New test_windows_reports.py uses real CreateFileW locks (short lock recovery and permanent-lock bounded failure).
- Runtime supervisor preserves safe typed process-failure codes instead of always discarding the cause.

## Actual test results so far

- Full active pytest: **340 passed**, 415.66 seconds, after clipping/synthetic-space fixes. This precedes the final memory release, supervisor diagnostic and Windows atomic-report retry additions. Do not claim a newer full-suite total.
- New Standard unit + real browser integration focused suite: **22 passed**, 16.43 seconds. Additional focused run including seven runtime tests: **29 passed**, 26.31 seconds. Latest focused run including two real Windows lock cases completed: **31 passed**, 22.37 seconds.
- Final Node suite already **12 passed**, 57.53 seconds; includes real 23-page PDF, real PNG preview and stale HTML/source preview rejection. A prior 60-second test wait timed out under concurrent tests; helper now respects the runtime's bounded deadline. No product timeout was relaxed.
- Real browser direct PDF single case **1 passed**, 51.7 seconds total (43.3-second test). Latest full browser run before Windows retry: 4 passed, 1 failed (native DOCX hit the proven Windows progress rename issue). Other earlier runs found terminal color/control JSON, CDP large-upload response eviction and async waitForFunction test issues; fixed with control file and APIRequest polling using the application's stored opaque job ID.
- Latest full browser suite after real Windows report retry completed **5 passed**, 1.8 minutes (former tool session 52994). Starts only production Next on loopback port 3400 with clean Python, no separate API/mocks. Final result was observed: 5 passed.
- Earlier full runs failed native DOCX text checks: initial 331 passed/2 failed (clipped paint excluded); next 338 passed/2 failed (adjacent synthetic vs real spaces). Both fixed; final full 340 passed. Keep failures in test history.
- Python Ruff and clean pip check passed before final retry; rerun targeted lint after final edits. Final docs/checkpoint/fixture/hash/link/Prettier/read-only diff checks passed (fixture/context 8/8).

## Actual visual evidence and limitations

A real successful 23-page PDF run in var/t2ui/8591b413-cc23-4a3f-bb36-7764797fd4e9/attempt001: HTML 2,188,398 bytes, 85,798 exact characters, 4 local assets, all 23 DOM/print page sizes checked. Maximum per-page screen mean absolute channel error 9.370502667607447/255; print maximum 0.9457879190186176/255. pixel_equivalence_verified=false. Reference and actual first-page screenshot were visually inspected; layout/tables preserved, screen font/rasterization differences remain noticeable. Local fonts/aliases are explicitly warned. No licensed font embedding, OCR, universal support or SEC acceptance is claimed.

A geometricPrecision CSS experiment in ignored var/refactor-stage5/precision-652ea51b slightly worsened screen error to 9.393296475787285; REJECTED, not in product CSS. Simple fixture measured small nonzero antialias differences. Offline transparency test initially compared against MuPDF's differing integer alpha rounding by <=1 and failed by 2; corrected to the known fixture RGBA-over-white math, while full PDF comparisons retain all raw differences.

Current known limitations: no EDGAR renderer, mode checkbox or ZIP packaging under revised contract; local font substitution differences, annotation appearance unsupported, exotic native SVG/text mappings may fail meaningfully; native PDF hyperlinks are retained in shared metadata but clickable navigation isn't reconstructed. Clipped paint text can remain searchable in HTML even if clipped visually. No output screenshots/JSON/PDF enter the final HTML asset directory.

## Resume after reset

Read current root status/checkpoint and inspect read-only Git. Stage 5 and all necessary tests/handoff checks are complete. Do not repeat Stage 1-5 or infer Stage 6 approval from old intermediate task lists. Await explicit Stage 6 authorization; user reviews, commits and pushes manually. Suggested commit: refactor: render Standard HTML5 from verified PDF layout.

## Environment and commands

Windows D:/Tools/ConvX, PowerShell. Clean Python: D:/Tools/ConvX/var/refactor-stage2/clean-env/Scripts/python.exe. Root .venv also exists. Git read-only executable: C:/Program Files/Git/cmd/git.exe. Web commands run in apps/web; root-relative Python paths do not work there (several failed auxiliary checks were rerun from root).

Full Python command: clean Python -m pytest -q --tb=short. Focused: tests/runtime/test_windows_reports.py tests/unit/test_standard_html.py tests/integration/test_standard_renderer.py tests/runtime/test_runtime.py. Web: npm.cmd test; set CONVX_TEST_PYTHON to clean Python; npm.cmd run test:ui. Runtime startup remains .\.venv\Scripts\python dev.py. Browser installation for fresh setup: .\.venv\Scripts\python -m playwright install chromium (free, one-time). Test-owned Next server is automatically stopped by Playwright; do not stop unrelated user processes. Ignored var/refactor-stage5 and var/t2ui hold private test evidence; output files are not committed.
