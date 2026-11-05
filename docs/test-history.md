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
