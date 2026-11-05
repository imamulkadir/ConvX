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
