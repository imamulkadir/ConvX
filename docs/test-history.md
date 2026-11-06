# Test history (append only)

## 2026-11-05 — Stage 1: initial inspection

Environment: Windows PowerShell, Python 3.12.10. Commands: `rg --files` with fixture/progress filters; `Get-Content AGENTS.md`; `git status --short`; read-only Python inspection of accessible fixture directories and ZIP/XML/PDF contents.

Result: no prior progress records or application code. Git status could not run because Git was unavailable on PATH. No Git writes performed. Located Volume II v78 in Downloads. Initial DOCX role mismatch identified; user later replaced their contents. Do not use the initial role mapping as the final baseline.

Analysis dependency command: `python -m pip install --target "$env:TEMP\convx-stage1-analysis" pypdf`; installed pypdf 6.21.4. Application dependencies were not installed.

Manual extraction command: inline Python/pypdf over all 607 pages into temporary `convx-stage1/manual.txt`; `rg -n` and selected-line reads inspected Chapter 5. One selected-text output failed due to Windows cp1252 console encoding; re-ran with `PYTHONIOENCODING=utf-8`, successfully reading the remaining sections. This was an inspection-output failure, not a conversion test. Automated application tests: 0 passed, 0 failed, not implemented.

## 2026-11-05 — Stage 1: updated fixture inventory

Command: `$env:PYTHONPATH="$env:TEMP\convx-stage1-analysis"; python tools/inspect_references.py --output docs/fixture-inventory.json`.

Result: succeeded after the user's DOCX update; all 5 fixtures inventoried. Original has 17 insertions/14 deletions, accepted baseline no inventoried revisions; ZIP CRC valid. Reference PDF: all 23 pages inspected, 612 x 792 pt, rotation 0 and nonempty extracted text. Volume II title/version/date verified. This is inventory evidence, not acceptance or visual regression. Automated application tests: 0 passed, 0 failed, not implemented. Stage 1 verification suite pending.

## 2026-11-05 — Stage 1: evidence and documentation verification

Command: `python tools/verify_stage1.py`. Environment: Windows PowerShell, Python 3.12.10; standard library only for verification, persisted pypdf 6.21.4 inspection evidence.

Result: 8 passed, 0 failed. Checks cover fixture byte/hash identity, original/accepted revision inventories, every reference PDF page, primary manual identity and registry binding, rule statuses and source sections, required documents/local links, synchronized tracking and absence of later-stage application code. Completed-stage record update follows this successful run; re-run the same suite after that update before handoff.

Outstanding qualification: no revision acceptance, PDF export, compliance engine, visual fidelity, integration or E2E tests exist yet. No authorized EDGAR submission performed. Git unavailable on PATH; no Git writes. Strict compliance profile remains unapproved, as intended for a design-only registry.

## 2026-11-05 — Stage 1: completed-record handoff check

Command: `python tools/verify_stage1.py`. Same Windows/Python environment. Result: 8 passed, 0 failed after status/checkpoint were marked completed and awaiting next-stage approval. No additional application tests run. Remaining limitations are unchanged. Final file listing confirms design documents, evidence and inspection/verification tools only; Stage 2 was not started.

## 2026-11-05 — Stage 2: recovery, environment and intermediate checks

Environment: Windows/PowerShell, Python 3.12.10. Read AGENTS/status/checkpoint/decisions/history and relevant specifications. `python tools/verify_stage1.py`: 8 passed, 0 failed before implementation. Located `C:/Program Files/Git/cmd/git.exe`; read-only status/diff found a pre-existing user README title edit, preserved throughout. No Git write operations. Docker, local Redis/PostgreSQL services and a configured WSL distro were unavailable.

Commands: `python -m venv .venv`; `.venv/Scripts/python -m pip install ...` for backend/test libraries; `.venv/Scripts/python -m pip install -e services/api[test]`. Result: installed successfully, backend editable package built. Exact resolved versions are in `services/api/requirements-lock.txt`; no renderer installed.

Intermediate `python -m pytest -q` runs:

- 54 passed / 2 failed: a dormant OLE MIME declaration in the original fixture was rejected despite no `.bin` parts. Refined validation to check actual parts and active relationships; both fixtures then admitted unchanged.
- 66 passed / 1 failed: a fail-closed configuration test inherited test worker token environment. Removed that environment specifically for the default-config test; production behavior remained fail closed.
- 67 passed / 0 failed / 2 skipped: expanded API/state/Celery tests passed; real Redis/PostgreSQL absent. One Starlette/httpx test-client deprecation warning.
- 68 passed / 1 failed / 2 skipped: a newly added heartbeat test block was accidentally placed under the metadata-purge test, causing an undefined test variable. Corrected placement.
- 71 passed / 1 failed / 2 skipped: new separate-process startup probe did not retry Windows connect timeouts during server startup. Corrected the probe to retry connection errors/timeouts within a bounded deadline and detect early process exit. Focused process suite then passed 3/3, including explicit schema CLI, separate Uvicorn HTTP process and real heartbeat lifecycle.

Ruff found and corrected imports/unused names/formatting during development; one explicit subprocess lint exception documents the fixed trusted argv used for the local server test. Initial read-only `git diff --check` flagged Markdown hard-break trailing spaces in modified status lines; removed them in the final status update. No unresolved application failures from these runs remain.

## 2026-11-05 — Stage 2: final backend verification

Command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov-report=term-missing`.

Result: **72 passed, 0 failed, 2 skipped**, 87% reported line coverage, one known Starlette/httpx test-client deprecation warning. Parent-process coverage does not collect the CLI/Uvicorn subprocesses, although their behavior is tested. Covered real fixture admission, hostile package rejection, authorization/ownership, API restart persistence, mixed batches, idempotency, request/file/quota limits, deletion/expiry, outbox outage/backoff, duplicate/stale claims, cancellation races, metadata purge, source tampering, heartbeat lifecycle and real Celery delivery using its in-memory test transport.

Skipped: optional real Redis delivery (`CONVX_TEST_REDIS_URL` absent), optional PostgreSQL transaction/idempotency (`CONVX_TEST_DATABASE_URL` absent). These skips are not service-integration passes. Linux prefork, deployed limits/sandbox, revision acceptance, PDF export, HTM/SEC/fidelity/full conversion E2E and SEC submissions were not executed.

Other commands: `.venv/Scripts/ruff check services workers tests` passed; `.venv/Scripts/python -m pip check` reported no broken requirements; historical `python tools/verify_stage1.py` passed 8/8 with current fixture hashes. Final progress/documentation handoff checks follow separately.

## 2026-11-05 — Stage 2: completed-record handoff

After marking Stage 2 completed/awaiting next-stage authorization: `python tools/verify_stage1.py` passed 8/8; Ruff lint passed; `ruff format --check services workers tests` reported all 31 Python files formatted; read-only `git diff --check` passed with only Git's LF/CRLF conversion notices. Read-only status confirms the intended code/documentation/configuration changes and no fixture modifications. The user's README title edit remains preserved. No Git writes performed. Stage 3 was not started.

## 2026-11-05 — Stage 3: recovery and free renderer setup

Authorization: user “go for it”, followed by explicit requirement for free components only and no premium licensing. Read persistent context and inspected read-only Git state; the prior stage was committed by the user. Baseline `.venv/Scripts/python -m pytest -q`: 72 passed, 2 skipped, 1 existing Starlette/httpx warning. No Git writes performed.

No LibreOffice or commercial SDK was initially installed. An initial unpinned PyMuPDF download selected the newer AI/layout dependency bundle; stopped that agent-owned installer and selected the minimal pinned PyMuPDF 1.26.7 plus Pillow 13.0.0/psutil 7.2.2. They installed successfully; `pip check` reported no broken requirements and no numpy/onnx/networkx bundle was installed. No paid provider was installed.

`python tools/fetch_libreoffice.py`: vendor MSI downloaded and SHA-256/size verified against official metadata. Administrative workspace extraction via `msiexec /a ... /qn TARGETDIR=.../.tools/libreoffice` returned 0, with hidden UI. Free LibreOffice 26.8.2.2 and system-font fingerprint recorded in qualification evidence. No document transmitted to a renderer service.

The first editable converter install ran before the pdf_export directory existed and failed package discovery; after actual provider modules were created, `pip install --no-deps -e packages/converter` built/installed successfully. An initial CLI run used an extra `LibreOffice` directory in the executable path and correctly reported unavailable. Corrected the path to the verified extraction's `program/soffice.com`.

## 2026-11-05 — Stage 3: actual revision and PDF qualification

Commands: actual `accept_revisions` and `compare_accepted_content` on supplied fixtures; `python -m converter.cli <source> <private-workspace> --libreoffice <verified-executable> --reference-pdf <fixture-pdf> --expected-accepted-docx <accepted-fixture>`.

Revision result: all 31 markers accepted; zero detected revisions remain. Ordered paragraph/table structure agrees in all 18 story parts; source SHA unchanged; all five original media parts byte-identical. Nine accepted-fixture media names represent the same four unique source image hashes. This does not establish complete DOCX format equivalence.

Native PDF runs: initial 512 MiB RSS profile failed safely with `RENDERER_MEMORY_LIMIT`. Explicit documented 1 GiB profile completed real PDF export: 23 pages versus 23 Word-reference pages. **Strict reference result failed on all 23 pages**, with font metric, geometry/order/content and raster discrepancies; CLI exited nonzero and did not continue to HTML. At 96 DPI exact RGB comparison, page difference fractions span about 1.23%–30.74%. Page 1 actual/reference images were visually inspected; floating header/logo/table/spacing differences were visible. No font/margin/anchor edits or relaxed pixel thresholds were used to force a pass.

Additional real rendering: supplied accepted DOCX through the same LibreOffice provider. Compared against independently accepted source's LibreOffice PDF: 22 identical pages, page 1 differing (66 word boxes shifted +9 pt horizontally). OOXML inspection found floating-table/style serialization differences in supplied baseline/source. This is recorded as format ambiguity, not silently repaired or treated as equivalent. Full private evidence stays in ignored `var/`; redacted all-page metrics are in `docs/stage3-regression.json` and findings in `docs/stage3-regression.md`.

## 2026-11-05 — Stage 3: incremental automated verification

Environment: Windows/PowerShell, Python 3.12.10, pinned local packages and actual LibreOffice. Test commands: `python -m pytest -q` and coverage variant `--cov=app --cov=workers --cov=converter --cov-report=term-missing`.

Results as components were added: 100 passed / 2 skipped (then fixed a test-string invalid-escape warning); 106 passed / 2 skipped / 1 existing warning after real renderer/process/lifecycle tests; 109 passed / 2 skipped / 1 warning with 87% reported line coverage after explicit property/PDF bounds and blank-page handling. Subsequent focused unit suite: 70 passed. Real same-renderer one-page export passes strict reference comparison; the full 23-page fixture is a negative qualification test that correctly detects its unsuccessful reference conversion. Self-comparison passes all 23 reference pages; page-23-only modification is detected. Cancellation test verifies owned renderer child termination. Failed/blocked work never enables download.

Skipped tests remain real Redis/PostgreSQL integrations with no configured services. No HTM/layout-model/SEC/ZIP/frontend/full pipeline or Linux production qualification executed. Final evidence-byte quota and renderer-memory tests plus handoff checks follow separately. Existing Starlette/httpx deprecation warning remains; it is not suppressed.

## 2026-11-05 — Stage 3: final automated verification

Command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`.

Result: **111 passed, 0 failed, 2 skipped**, 87% reported line coverage, 1 existing Starlette/httpx warning, 87.23 seconds. Native LibreOffice tests executed; genuine same-renderer positive PDF gate passed, while the supplied 23-page Word reference remained an unsuccessful conversion correctly detected by the negative qualification test. Evidence-byte truncation still computes every page's failure metrics; process memory/cancellation/owned-child tests passed. No false completion/download was enabled. Two skips are optional real Redis/PostgreSQL integrations; neither was simulated as a real-service pass. Manual CLI and subprocess coverage are not collected by parent coverage.

Other commands: Ruff lint passed; formatting check reported all 50 Python files formatted; `pip check` reported no broken requirements; read-only `git diff --check` passed with LF/CRLF notices only. `python tools/verify_stage1.py` passed 8/8 before final progress-record updates, confirming fixture hashes and context consistency. Final completed-record checks follow separately. No source fixtures modified, no Git writes and no Stage 4 implementation.

## 2026-11-05 — Stage 3: completed-record handoff

After marking Stage 3 implementation completed and awaiting Stage 4 authorization, `python tools/verify_stage1.py` passed 8/8. An additional read-only Python check verified all root/docs Markdown local links, parsed the completed checkpoint and confirmed redacted qualification evidence contains 23 failed reference pages and zero strict passes. Read-only `git diff --check` passed with LF/CRLF notices only. Source fixtures remain unchanged; ignored `.tools/` and `var/` contain local renderer/intermediate evidence, not final filing outputs. Stop at Stage 3; no Git writes and no automatic next stage.

## 2026-11-05 ? Stage 4: recovery and incremental verification

Environment: Windows/PowerShell, Python 3.12.10, pinned PyMuPDF 1.26.7, actual local LibreOffice. Read AGENTS/status/checkpoint/decisions/history, inspected read-only Git (initially clean), and reran baseline: 111 passed, 2 optional live-service tests skipped. User explicitly authorized Stage 4 with ?pushed, continue?; free-only requirement retained.

Implemented typed layout/native extraction and ran `.venv/Scripts/python -m pytest tests/unit/test_pdf_analysis.py -q`: 30 passed, 0 failed. The real one-page positive pipeline initially failed because a harmless native outer-page clip was treated as unresolved. Fixed by testing exact clip containment against actual content, preserving every native clip and blocking relevant unresolved associations; focused genuine positive export passed (1 passed). No clip or pixel tolerances were relaxed.

First full coverage command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`: 141 passed, 0 failed, 2 skipped, 89% line coverage, 1 existing Starlette/httpx warning, 89.20 seconds. This included native positive export and failed Word-reference gate tests. Subsequent script/all-page extraction checks: 32 passed in 23.49 seconds. No-download completion lifecycle focused test: 1 passed. Full unit/integration rerun after these additions: 143 passed, 2 skipped, 89% coverage, 1 warning in 89.10 seconds. Discovered the historical default testpaths excluded the new regression directory; added it so future default runs always include the mandatory 23-page extraction regression. Final combined default-suite result follows below.

Read-only inspection CLI executed on all 23 Word-saved reference pages: 85,798 characters, 1,263 lines, 13 font resources, four assets in five image placements, 4,847 native vector paths and eight ruled-table candidates. Private schema-v1 JSON: 40,725,093 bytes. Per-page native character SHA/length, vector and image counts agree in regression tests; original PDF hash remains unchanged. Output is inspection_only/reconstruction_eligible=false, not a qualified conversion. Generated LibreOffice reference fidelity still fails and does not enter analysis.

Ruff initially found unused fixture loop variables and formatting; corrected them. Final lint passes, 64 files already formatted, pip check clean. Live Redis/PostgreSQL remain skipped; Linux sandbox/prefork and later HTML/SEC/ZIP/UI stages remain unexecuted.

## 2026-11-05 ? Stage 4: final combined suite and handoff

Command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`. Result: **144 passed, 0 failed, 2 skipped**, 89% line coverage, one existing Starlette/httpx deprecation warning, 127.71 seconds. Default collection now includes unit, integration and regression directories. Actual free LibreOffice positive export/layout and negative Word-reference qualification both executed; all 23 reference pages passed read-only extraction accounting. The negative conversion test passing does not mean Word-reference fidelity passed. Two skips remain unconfigured real Redis/PostgreSQL services.

Final Ruff lint and formatting passed (64 files); pip check clean; historical fixture/context checks passed 8/8; all root/docs local links and generated schema matched; read-only git diff --check passed with LF/CRLF notices only. Completed records updated atomically where applicable. No original fixtures changed, no Git writes, no Stage 5 implementation and no HTM/ZIP/download readiness claimed. Stop for user review and explicit next-stage authorization.

## 2026-11-05 - Stage 5: recovery, implementation and incremental verification

Read persistent context and manual sections 5.2.2.2-.6; initial read-only Git state clean. User explicitly authorized Stage 5. Recovery test `.venv/Scripts/python -m pytest tests/unit/test_pdf_analysis.py -q`: 31 passed. Actual manual text extraction printed pages 158-163; Windows cp1252 output could not encode page 164 bullet text, so the command failed at console encoding without modifying the manual. Existing character uncertainty remained unresolved.

Implemented normal-flow HTM reconstruction, source/proof gates, exact disclosure accounting, physical tables, graphic requests, links and pending-gate lifecycle. Installed editable converter 0.5.0 successfully. Initial focused run: 5 passed / 23 failed due to a PageGeometry field-name mismatch (rotation versus rotation_degrees); corrected the caller. Next run: 26 passed / 2 failed (script fixture native clipping correctly blocked by the existing extraction gate, and a work-budget test used only one item). Used a genuine unclipped native text fixture and meaningful multi-item work input; no gate bypass. A new reading-order guard correctly rejected ambiguous font-fragment order; the positive script fixture was separated into unambiguous source lines. Focused 28 passed. Native positive LibreOffice current-pipeline test: 1 passed in 36.88 seconds.

First full coverage suite: 173 passed, 0 failed, 2 skipped, 89% line coverage, one existing Starlette/httpx warning, 135.20 seconds. Actual negative Word-reference conversion still failed at the PDF gate before layout/HTM. Subsequent work-budget limits and no-download lifecycle focused run: 29 passed. Added internal-link, Unicode, memory and exclusive-publication tests. Internal-link test exposed a one-based destination-page mismatch; corrected conversion and prevented repeated bookmark emission across split lines/cells. Expanded focused generator suite: 34 passed, 0 failed. Final combined suite follows separately.

Explicit private synthetic-PDF runs produced a 2,403-byte 12-character candidate and a 5,343-byte merged-table candidate retaining 23 characters, one table and no nested table. Both keep strict/compliance/fidelity false. They isolate engine mechanics using PDF self-comparison, not DOCX qualification. Original reference fixtures remain unchanged; full artifacts stay under ignored var/stage5.

## 2026-11-05 - Stage 5: final combined verification and handoff

Command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`. Result: **179 passed, 0 failed, 2 skipped**, 90% reported line coverage, one existing Starlette/httpx warning, 132.01 seconds. Includes 34 generator tests, actual LibreOffice positive current pipeline, unsuccessful 23-page Word-reference negative gate and mandatory all-page extraction regression. The two skips remain unconfigured real Redis/PostgreSQL services; no actual-service pass was fabricated. No Chromium/SEC/ZIP/full filing qualification was performed.

Ruff lint passed; formatting check reported 71 files formatted; pip check clean; all root/docs local links and Stage 5 JSON artifacts verified. Read-only git diff --check passed with LF/CRLF notices only. Completed status/checkpoint updated; fixture/context verification follows. All candidate strict/compliance/fidelity flags remain false. No paid components, source-fixture edits, Git writes or automatic Stage 6 work.

Completed-record verification: `.venv/Scripts/python tools/verify_stage1.py` passed 8/8, confirming unchanged fixture hashes, manual evidence and synchronized completed Stage 5 progress.

## 2026-11-05 - Stage 6: recovery, research and implementation

Read AGENTS/status/checkpoint/decisions/history and read-only Git (initially clean). User explicitly authorized "go for stage 6". Recovery command `.venv/Scripts/python -m pytest tests/unit/test_html_generator.py -q`: 34 passed. Extracted actual supplied manual pages 144, 157, 162-168 and 170 using ASCII-safe JSON output; no fixture bytes changed. Checked official SEC v78 PDF (607 pages), SEC filing-limit/formatting guidance and W3C HTML4 entity/DTD/CSS background. Direct loose.dtd browsing returned unsupported content type, not an SEC permission source. MANY/CSS and conflicting character mappings remain explicit unresolved cases. Supplementary SEC guidance motivated generator v2 shared formatting runs.

Implemented source-first runtime v78.2 rules, actual-file diagnostics, conservative CSS/encoding/link/asset/name checks, context-dependent sizes, source-bound graphic normalization and worker/API lifecycle. First source/generator focused suite: 102 passed. Added genuine JPEG/alpha/gradient graphics: 105 passed / 5 failed because the native alpha fixture had an isolated outer full-page Normal group, which Stage 5 conservatively rejected. Added the narrowly scoped generator-v2 white-canvas normal group strategy with explicit pending visual warning; no PDF/style proof bypass. Focused source/asset/generator suite then passed 110 tests. Further ambiguous-comment, file-mutation and actual 25 MB ABS-15G checks passed; final focused run 115 passed, 0 failed, one existing warning.

Converter 0.6.0 editable install succeeded. An attempted no-build-isolation wheel build failed because this local venv lacks setuptools.build_meta; the standard isolated build succeeded without changing runtime dependencies. Final wheel build succeeded; packaged registry and source bytes matched the repository, and isolated Python imported the wheel (rather than the editable checkout) and passed actual-file confirmed-subset validation using packaged rules. Build output stays ignored, not a final filing artifact.

## 2026-11-05 - Stage 6: full regression and completed handoff

Command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`. First full run: 256 passed, 0 failed, 2 skipped, 89% coverage, one existing warning, 140.79 seconds. Final expanded run after comment/mutation/context tests and consistent normalization budgets: **261 passed, 0 failed, 2 skipped**, 90% reported line coverage, one existing Starlette/httpx warning, 155.62 seconds.

Actual LibreOffice positive PDF regression now reaches HTM/materialization and correctly fails local CSS/MANY permission uncertainty. The real Word-reference conversion still fails all 23 PDF pages and produces no downstream HTM/SEC success. All-page read-only extraction regression still passed. The two optional skips remain unconfigured real Redis/PostgreSQL services; none were simulated as live passes. No Chromium visual validation, SEC Doc Validation/TEST filing, ZIP/full filing pipeline, UI or Linux production sandbox/prefork qualification was executed.

Actual private confirmed-subset HTM with real form/whole encoded-size context passed strict local checks; actual styled HTM failed ATTRIBUTE_SCOPE_UNVERIFIED/CSS_PERMISSION_UNVERIFIED. Both retain SEC acceptance and visual qualification false. Real JPEG passthrough bytes, exact GIF/alpha roundtrip, gradient JPEG difference recording, stale xref/mask/source/candidate failure and budgets were exercised. The redacted local compliance evidence is docs/stage6-compliance-regression.json; it is not reference-conversion qualification.

Final Ruff lint passed; 81 Python files passed formatting. Pip check clean. Root/docs links and JSON parsed; runtime/documented registries matched; final wheel source/data matched; read-only git diff --check passed with LF/CRLF notices only. Completed records saved atomically where applicable; historical fixture/context check follows. No original fixtures, Git state or premium licensing were changed. Stop before Stage 7 and await explicit authorization.

Completed-record `tools/verify_stage1.py` passed 8/8: unchanged fixture hashes and synchronized completed Stage 6 context.

## 2026-11-05 - Stage 7: recovery, provisioning and real-browser implementation

Read persistent context and read-only Git (initially clean). User explicitly authorized continue; a repeated continue during this active stage retained Stage 7 and did not authorize Stage 8. Recovery source/asset/generator command passed 115 tests. Installed free pinned Playwright 1.64.1, NumPy 2.5.4, pyee 14.0.0 and greenlet 3.5.6. Actual Chromium 156.0.8078.4 revision 1248 and matching headless shell installed from Playwright vendor distribution. Read official Playwright browser/PDF/screenshot/routing documentation.

Implemented isolated trusted browser worker, manifest/CSP/script restrictions, source/file/gate capture, print/screen measurement, native geometry/paint/font/image/vector checks, raw/edge-candidate pixel metrics, private artifacts and strict/nonqualifying model consistency. First smoke print failed because pt print-size arguments were unsupported; changed print configuration to inches derived from source points. The relative workspace caused invalid temporary paths under the child working directory; resolved it before launching. Genuine browser smoke then produced matching print content/geometry and zero print pixel differences, while screen had 1,169 unexplained pixels. Strict failure was retained instead of relaxing thresholds.

First focused visual suite: 20 passed / 2 failed (blank source correctly rejected by the existing selectable-text PDF gate, and font changes also changed text alignment so needed independent resource-set diagnostics). Positive production-entry exercise now uses actual selectable Chromium text and retains its real screen failure; blank matching pages are diagnostic-only. Strengthened SEC/stale-gate tests use an actual passing PDF proof. Later focused run: 19 passed / 2 failed / 1 error due to disappearing transient Chromium profile files in the shared storage monitor. Fixed the stat race and enabled full-page clip capture beyond the viewport after the 23-page inspection exposed screenshot clipping failure. Focused pixel/browser/all-page suite then passed 23 tests in 85.57 seconds.

Added direct browser CSP/script behavior and overlapping page-container checks, global geometry record bounds, pinned browser manifest verification and inspection result promotion protection. A brief indentation error in the new geometry counter caused three collection errors and was corrected before testing. First full coverage run: 285 passed / 1 failed / 2 skipped, 87% coverage, 248.86 seconds. The failing assertion expected a route denial, but CSP blocked the remote image before any network/route callback. Updated the test to assert that stronger actual behavior (zero denied-request callbacks, image unloaded, script not executed). No safety rule was weakened. Independent strengthened gate/promotion checks passed 4/4.

## 2026-11-05 - Stage 7: final full suite and handoff

Command: `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`. Result: **286 passed, 0 failed, 2 skipped**, 87% parent-reported coverage, one existing Starlette/httpx warning, 261.06 seconds. Actual Chromium children and manual processes run, but their coverage is not collected by parent coverage. Native LibreOffice, current PDF/SEC gate failures and all 23 mandatory reference extraction/negative visual pages were exercised. The two optional skips are unconfigured real Redis/PostgreSQL, not simulated live successes.

Actual source-bound smoke rerun confirmed zero print differences and 1,169 unexplained screen pixels, with strict result false and bound earlier evidence. Explicit negative inspection compared the original Word-saved 23-page fixture to a deliberately empty 23-page HTM: all 85,798 source characters accounted for, missing disclosure diagnosed on every page, strict=false. This is a negative engine regression, never a prospectus conversion result or PDF-gate bypass. Redacted actual metrics are docs/stage7-visual-regression.json; originals remain unchanged.

Editable converter 0.7.0 install and wheel build succeeded. Final wheel source bytes matched visual/control/process code; isolated wheel parent and child loaded packaged code and executed actual Chromium comparison, retaining nonqualifying inspection status. Ruff lint passed; final formatting check reported 92 Python files; pip check clean. Final documentation/context/fixture/read-only diff checks follow completed records. Browser/intermediate artifacts remain private and ignored; no final ZIP, UI, authorized SEC TEST filing, Linux production qualification, premium component, source correction or Git write was performed. Stop before Stage 8 and await explicit authorization.

Completed-record historical fixture/context verification passed 8/8. All root/docs links and redacted Stage 7 evidence counts parsed correctly; final Ruff lint/format (92 files), pip check and read-only git diff --check passed. Original fixtures remain unchanged.

## 2026-11-05 - Stage 8: recovery and deterministic packaging

User explicitly authorized "proceed". Read recovery documents and initially clean read-only Git state; baseline focused tests passed 86. Implemented pre-gate naming, real root-only deterministic stored ZIPs, independent headers/CRC/member/manifest/archived SEC validation, gated atomic publication, original-name worker flow, configurable budgets, proof-chain completion and captured-byte owned download checks. No Git write, premium dependency, fixture mutation or gate relaxation occurred.

Initial archive unit command passed 47 tests; existing worker/API boundary command passed 21; genuine browser failed/stale evidence, corrupt completed metadata, completion flags and path/header tests passed 18. Four genuine selectable glyph print/screen probes at 96 and 144 DPI retained actual strict failures (96 DPI unexplained screen pixels 17/36/41/4; 144 DPI 26/55/42/7). These were diagnostics only, never reference output or manufactured passing gates. No positive high-level publication/HTTP download was fabricated. Archive mechanics independently retain conversion_eligible=false.

## 2026-11-05 - Stage 8: full suite, final cleanup tests and wheel

Command `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`: **351 passed, 0 failed, 2 skipped**, one existing Starlette/httpx warning, 86% parent coverage, 260.20 seconds. Windows Python 3.12.10, actual LibreOffice and pinned Chromium. Full 23-page Word PDF failure and negative visual accounting remain intact. Optional real Redis/PostgreSQL skipped for absent configured services. Child/manual coverage is not collected; genuine positive package publication/HTTP serving remains unqualified because actual gates fail.

Added three targeted exclusive-write/cancellation/oversize cleanup cases after full-suite collection, with no implementation change. Final command `.venv/Scripts/python -m pytest tests/unit/test_packaging.py tests/integration/test_packaging_gates.py -q --tb=short`: **68 passed, 0 failed**, one existing warning, 6.62 seconds. The exclusive-writer created guard prevents deleting an existing file on a failed exclusive open; cancellation and size-limit failures remove only their own partial file.

Ruff check/format passed, 100 Python files formatted; pip check clean. Editable converter 0.8.0 installed. Initial wheel command with --no-build-isolation failed because runtime setuptools.build_meta was absent; normal isolated build succeeded. Wheel 0.8.0 source/data bytes matched all 53 files. An isolated -I Python process imported the actual wheel and wrote two identical 937-byte HTM/JPG ZIPs; independent actual archived SEC/header/CRC/manifest audit passed with conversion_eligible=false. Evidence is docs/stage8-packaging-regression.json. This verifies archive mechanics, not successful DOCX conversion or HTTP download. Completed-record fixture/link/JSON/read-only diff verification follows. Stop before Stage 9.

Completed-record tools/verify_stage1.py passed 8/8 (including unchanged fixtures and synchronized Stage 8 records). Root/docs Markdown links and JSON parsed successfully; read-only git diff --check passed with LF/CRLF notices only. No Stage 9 work started.

## 2026-11-05 - Stage 9: recovery, frontend and diagnostic preview boundaries

User authorized continue; read persistent context and initially clean read-only Git state. Recovery packaging/API command passed 87. Applied Sites local-only workflow guidance; no hosting, Git write or premium dependency. Checked official Next rewrites, Tailwind and DaisyUI documentation. Installed pinned Next 16.4.5, React 19.3.1, Tailwind 4.3.4, DaisyUI 5.7.50, Lucide 1.69.0, PDF.js 6.5.438, Playwright 1.64.1, axe 4.14.0 and Prettier 3.9.10 with npm lock.

Implemented JSX workspace, memory-only per-user authorization, configured admission-limit session endpoint, real batch upload/progress/polling, filtering/recovery/removal/retry, diagnostics, protected PDF/declared-PNG previews and guarded download UI. No active untrusted HTM or Next conversion route. Diagnostic review never promotes strict eligibility.

Initial Python preview command: 8 passed / 1 failed because a genuine size-mismatched screen comparison had no screen-difference image. The UI now explicitly uses existing print overlay/print-difference evidence; absent screen captures remain unavailable. Final preview command passed 9/9. Existing worker/API checks also passed 37 before preview expansion. No comparison rule was relaxed.

Browser setup first failed for missing test-only root import; corrected test launcher. Initial UI run: 4 failed due to API origin baked at build time and insufficient muted contrast. Config now builds with its actual test origin. Subsequent run: 1 passed / 3 failed for mixed file path/buffer fixture, Next live-route announcer test ambiguity and genuine native preview unavailability. Corrected selectors/payloads. The long system-TEMP/UUID native renderer workspace produced INVALID_PDF_OUTPUT; shortening the disposable owned workspace under ignored var/stage9 produced real PDF/HTM and its expected SEC permission failure. This is documented Windows path qualification risk, not manufactured output. An intermediate four-case run then passed 4/4.

Added real drop admission, roving keyboard tabs and axe on queued/failed details. First expanded run: 3 passed / 2 failed due to DaisyUI inactive-tab contrast; set explicit readable tab colors. Five-case rerun passed. Strengthened native PDF assertion to require actual opaque nonwhite rendered canvas pixels, rather than default canvas dimensions; corrected frontend resumable code to the repository's actual LAYOUT_ENGINE_NOT_AVAILABLE.

## 2026-11-05 - Stage 9: final qualification and handoff

Full command `.venv/Scripts/python -m pytest -q --cov=app --cov=workers --cov=converter --cov-report=term-missing`: **363 passed, 0 failed, 2 skipped**, one existing Starlette/httpx warning, 86% parent coverage, 267.24 seconds. Windows Python 3.12.10, real LibreOffice, pinned Chromium and all-page reference regressions. Optional real Redis/PostgreSQL remain skipped. Parent coverage does not collect actual browser child/manual execution.

After the final capture-DPI metadata addition, API/preview boundary command passed 28 tests; final `.venv/Scripts/python -m pytest tests/integration/test_previews.py -q --tb=short` passed **9/9**, one existing warning, 6.17 seconds. Actual PNG/PDF serving, corrupt/changed source/artifact rejection, ownership, expiry, missing and invalid-page behavior were exercised. Original fixtures remain unchanged; failed real gate evidence remains unsuccessful.

Final `npm.cmd run test:ui`: **5 passed, 0 failed** in approximately one minute against real disposable API/SQLite and production Next. Includes real two-file upload and independent jobs, tab recovery/theme/cancellation, invalid access/file rejection, keyboard/help/roving tabs, genuine native negative diagnostic and nonblank PDF canvas, honest missing HTM, axe WCAG A/AA checks on empty light/mobile dark/queued/failed views and real drag-drop upload. Screenshots inspected at 1440x1100 and 390x844; private images/traces stay ignored. No mocked conversion engine, fake successful ZIP, live Redis or public deployment was used.

`npm.cmd test`: **3 passed**. Production builds succeeded. Final Prettier check passed; Ruff lint/format passed (103 Python files), pip check clean; npm audit reported zero advisories. Initial DaisyUI join optimizer warnings disappeared after using a simple native mode group. Existing Starlette/httpx and Playwright NO_COLOR/FORCE_COLOR notices remain non-failing. No ESLint, other-browser or assistive-technology qualification is claimed. Stage 9 evidence is docs/stage9-frontend-regression.json; positive fully qualified package/HTTP download remains Stage 10 work. Stop before Stage 10.

Completed-record historical fixture/context verification passed 8/8. Root/docs links and JSON parsed; read-only diff whitespace check passed with LF/CRLF notices only. Generated worker/node_modules/.next/test artifacts remain ignored. No Stage 10 or Git write performed.

## 2026-11-05 - Explicitly authorized post-Stage 9 local startup repair

User's live job was queued with zero attempts; readiness showed absent Redis and worker. User requested one-command startup. Added root dev.py, real separate serial local SQLite runner, development-only configuration guard and readiness transport reporting. The worker invokes the unchanged admission/conversion function, preserves atomic claims/leases/cancellation/cleanup/all proof gates, and selects only queued local-owner jobs. Launcher preserves user .env and existing processes, finds free ports, uses separate .next-local, discovers free LibreOffice and supervises owned process trees. Production Redis/Celery default unchanged. Disabled Next's automatic generated agent-rules file after reading the installed version's documentation; removed only the file created by this smoke run.

First focused collection failed because importing the decorated worker module eagerly constructed token settings before test environment setup; moved the worker import into actual processing. Initial lint found trusted fixed-argv subprocess calls; documented their trusted input boundaries. Subsequent focused runs passed 25 then 34. Final `.venv/Scripts/python -m pytest tests/integration/test_local_dev.py tests/unit/test_config.py tests/integration/test_api.py -q --tb=short`: **35 passed, 0 failed**, one existing warning, 3.66 seconds. Includes genuine local revision acceptance, unavailable-renderer failure, rejected production/token/non-SQLite modes, other-owner exclusion, occupied-port preservation and owned-process shutdown. Node tests: 3 passed. Ruff lint/format and frontend config Prettier checks passed. Full suite/UI suite not repeated for this scoped fix.

Actual `.venv/Scripts/python dev.py --no-reload` started real API/UI/local worker on 8000/3000, served the workspace, and processed the previously queued real upload. It reached revision acceptance and generated PDF, then correctly blocked with PDF_REFERENCE_REQUIRED on attempt 1. Readiness reported local transport/worker foundation ready, full strict conversion readiness remained false. No mock job, substituted source, removed gate, premium service, Git write or Stage 10 work. Live development services remain available for the user's review; their launcher owns shutdown.

## 2026-11-05 - Explicit real test through the running UI/API/worker

User asked to check the blocked conversion and perform a real running-instance test. Queried live readiness: real local worker alive and queue transport available. Existing recent user job was blocked at PDF_REFERENCE_REQUIRED. Used actual Chromium against http://127.0.0.1:3000, selected local access, uploaded the original mandatory DOCX with the real file input and Start conversion button. Actual XHR response was 202 with job 654ba6ac-b3fc-4070-b74a-ced8958075d4. Existing worker independently claimed attempt 1, accepted revisions (zero remaining), generated 23 pages and blocked on missing reference. No HTTP interception, fake response or substituted output.

Verified the stored source hash against the exact fixture, then provisioned the supplied matching Word-exported reference PDF into only that job's private reference.pdf through the documented operator workflow. POST resume returned 202. Actual worker attempt 2 generated PDF again and compared all 23 pages against the 23-page original reference: **23 pages failed**, diagnostic PDF_STRICT_VALIDATION_FAILED, final state failed. Source/original fixture hashes unchanged; PDF preview metadata 200; ZIP request 409; download_available=false; no HTM generation. This is real negative qualification, not a successful filing E2E. Captured actual UI screenshot/private reports under ignored var/live-instance-check; redacted metrics are docs/live-instance-regression.json. No gate was relaxed, paid renderer added, user job deleted, Git write performed or full Stage 10 implementation started.

## 2026-11-05 - Revised workflow Stage 1: existing-project audit

User explicitly authorized "yeah proceed" after replacing AGENTS.md with the simplified DOCX/PDF two-mode plan. This is revised Stage 1, not the old Stage 10. Read persistent state/source, inspect read-only Git and preserve existing modified/untracked repair files. Inspected UI/admission/orchestration/config/database/worker, revision/native rendering, shared layout, generator, assets, SEC/visual/package modules and dependency locks. No services stopped, user data removed, application refactored or Git state changed.

Command `.venv/Scripts/python -m pytest tests/unit/test_revisions.py tests/unit/test_pdf_analysis.py tests/unit/test_html_generator.py tests/unit/test_sec_validation.py tests/unit/test_assets.py tests/unit/test_packaging.py -q --tb=short`: **216 passed, 0 failed**, one existing Starlette/httpx warning, 9.70 seconds. Existing engine mechanics only; not revised four-path conversion qualification. `npm.cmd test`: **3 passed**, 0 failed. `npm.cmd run check:format` and pip check passed. OCR executable tesseract not found on PATH; no OCR conversion was claimed.

Initial tools/verify_stage1.py: **7 passed, 1 failed**, because the updated instruction file lacked its expected onboarding phrase. Restored compatible recovery wording and made only the historical stage-scope check phase-aware: the revised Stage 1 audits an existing application and cannot assert that application files are absent. Archived old progress byte-for-byte, added audit/migration plan and revised root checkpoint/status. Final checks follow. No full suite, new native/23-page conversion, browser UI suite, build or deployment was run; historical live negative evidence remains valid and unchanged.

Final revised Stage 1 tools/verify_stage1.py passed 8/8 in 0.070 seconds. Archived records match their pre-refactor SHA-256 exactly; active audit/context links and checkpoint JSON verified. Read-only git diff --check passed with LF/CRLF notices only. Stage 2 not started.

## 2026-11-06 - Revised Stage 2: simplify architecture

Authorized by the user's "go on" and subsequent "continue". Recovered AGENTS/status/checkpoint, inspected source and read-only Git. Implemented the direct Next/Python runtime, pure admission/artifact audit, single-server launcher, token-free transitional UI and reduced dependency setup. Existing user .env/database/artifacts and reference fixture bytes were preserved. No Git write, Stage 3 feature implementation or full-chain conversion success is claimed.

Environment: Windows, Python 3.12.10, Node 22.19.0; installed requirements-dev.txt into ignored var/refactor-stage2/clean-env and captured requirements-dev-lock.txt. Import probes confirmed FastAPI/Celery/Redis/SQLAlchemy/psycopg are absent and converter.runtime imports. Clean pip check passed. No licensed Aspose or Office automation dependency was added; actual native rendering uses free local LibreOffice.

`var/refactor-stage2/clean-env/Scripts/python -m pytest -q --cov=converter --cov-report=term`: **270 passed, 0 failed, 322.86 seconds, 83% parent-process coverage**, no warnings. Includes real native and browser visual/converter regressions; subprocess coverage is not collected. After adding 18 pure admission security regressions migrated from retired API tests, `python -m pytest tests/runtime -q`: **25 passed, 0 failed, 4.43 seconds** (7 prior runtime + 18 admission). The full suite preceded those additional tests; do not report a fabricated full-suite total of 288. Original mixed API integration sources were preserved under tests/legacy before retaining converter cases; old service-only modules are opt-in historical checks, not current passes.

Final `npm.cmd test`: **11 passed, 0 failed**, 9.18 seconds. Covers real Python invalid-input processing, filename/origin/byte/path guards, rollback, cancellation, interrupted state, expiry and download denial. `npm.cmd run test:ui`: **4 passed, 0 failed, 1.2 minutes**, using a production Next build and the clean Python interpreter, with no separate API or mocked conversion responses. Browser checks cover automatic startup, real upload/reload/recovery/deletion, native one-page DOCX processing blocked on PDF_REFERENCE_REQUIRED, actual nonblank PDF canvas review, invalid-document rejection and responsive light/dark keyboard/axe behavior. The retained legacy gate is an expected negative outcome, not conversion success. The complete successful proof-chain download remains unqualified.

Initial failures resolved: import-isolation test revealed eager API imports in root conftest (made lazy and asserted in a separate process); browser writes exposed Next normalizing request URL host to localhost (validate against incoming Host and add Node regression); UI selectors matched duplicate diagnostic codes and a PowerShell-encoded middle-dot literal (precise/regex selectors, no engine bypass). Initial production build traced dynamic filesystem paths and emitted nine warnings; explicit Turbopack dynamic-path exclusions fixed tracing and subsequent production builds passed. Final browser run followed removal of obsolete token state/arguments. Only inherited FORCE_COLOR/NO_COLOR notices remained.

`npm.cmd run check:format`, targeted active Python Ruff and clean pip check passed. Launcher smoke served root 200 and internal session JSON on owned port 3410 with no separate API; the owned QA launcher/descendants were stopped afterward. An initial final-check invocation used the web directory with root-relative Python paths and did not run Ruff/pip; rerun from repository root passed. No other existing user services were stopped. Fixture/recovery, documentation and read-only diff checks are recorded in the final Stage 2 evidence file.

Final Stage 2 recovery/fixture checker: **8 passed, 0 failed**, 0.348 seconds. Historical progress SHA-256 and active local links passed; clean dependency isolation rechecked; targeted Ruff and read-only git diff --check passed (LF/CRLF notices only). Final launcher smoke from the clean interpreter returned root/session HTTP 200 even with a deliberately invalid inherited Node preload (correctly stripped); owned launcher/descendants stopped. Stage 2 completed and checkpoint awaits explicit Stage 3 authorization.
