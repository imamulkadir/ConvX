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
