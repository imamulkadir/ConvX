# ConvX - Simplification Refactor Status

## Overall Status

Workflow: simplification-refactor (revised AGENTS.md; existing repository)

Current Stage: 2 - Simplify Architecture

Stage Status: completed

Last Completed Stage: 2

Next Stage: 3 - DOCX and PDF Input Support (explicit authorization required)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Stages

Stage 1 audited the existing project and produced the [staged migration plan](docs/refactor-audit.md). Stage 2 replaced the active service architecture with one self-hosted Next application invoking bounded local Python processes. Stage 3 is not started. Earlier implementation stages are preserved in [historical status](docs/history/pre-refactor-status.txt) and [historical checkpoint](docs/history/pre-refactor-checkpoint.json); they do not qualify the revised feature requirements.

## Stage 2 Implemented Features

- Single startup with `.\.venv\Scripts\python dev.py`; internal Next routes handle upload/status/diagnostics/preview/retry/delete/download. No API token, connection form, separate public Python server, Redis/Celery/database or account setup. See [setup and runtime](docs/simplified-runtime.md).
- Real converter subprocess execution with actual progress/diagnostics, upload bounds, private UUID paths, one active conversion, cancellation/process-tree supervision, interrupted-state handling and retention cleanup. Existing conversion/security/content gates remain intact.
- Pure converter admission/configuration/artifact audit modules remove API/ORM import dependencies. Existing API admission becomes a retired adapter. Download requests still independently validate evidence and captured ZIP bytes.
- Minimal runtime/dev requirements and clean-environment lock. User .env, prior database/artifacts and all source fixtures preserved. Old services/workers/tests are explicitly historical, retained for recovery and later cleanup.
- Transitional UI auto-connects to same-origin handlers and keeps real upload progress, diagnostics and PDF review. Final minimal page and optional mode checkbox remain Stage 8 work.

## Files Changed

Core: dev.py, requirements*.txt, pyproject.toml, packages/converter/{admission,runtime_config,runtime,artifacts,cli}.py and package metadata. Web: internal app/api routes, lib/server/runtime.mjs, token-free API/hook/components, Next config, browser setup/tests and Node runtime tests. Verification: active converter integration tests and pure admission/runtime cases; original service-specific cases preserved in tests/legacy. Documentation: README, AGENTS, environment examples, simplified-runtime, historical setup banners, decisions, test history, redacted Stage 2 evidence and progress records. Retired service/worker README files identify inactive code.

## Testing

Clean Python active suite: 270 passed, 0 failed, 83% parent-process coverage, 322.86 seconds. Subsequently added 18 pure admission cases; focused runtime suite: 25 passed, 0 failed. These are separate runs, not a claimed 288-test full-suite result. Node: 11 passed. Production-build browser tests: 4 passed, including real native conversion reaching the existing missing-reference block and actual PDF preview. No mocked conversion service. Format, targeted Ruff, pip, fixture/context/archive hashes and read-only diff checks passed; details in [test history](docs/test-history.md) and [Stage 2 evidence](docs/stage2-runtime-regression.json).

## Known Limitations and Pending Tasks

This architecture stage intentionally retains DOCX-only admission and the legacy strict reference/SEC pipeline. A DOCX without operator-provided reference blocks with PDF_REFERENCE_REQUIRED. The historical 23-page Word regression failed all pages; that evidence is unchanged. Styled SEC permissions/character ambiguities remain unresolved. No successful qualified whole-chain ZIP or high-level download path is demonstrated. No Standard renderer, direct PDF upload, new dual-mode packaging or scanned-PDF OCR exists yet. Do not describe application startup as successful document conversion.

Stage 3 must adopt the revised generated/uploaded-PDF visual authority contract and both input types while keeping Word-reference comparison as honest regression evidence. Stages 4-8 implement shared layout, distinct Standard/EDGAR renderers, mode-specific ZIP and the minimal page; Stage 9 tests all four input/mode paths; Stage 10 final cleanup. Single Node instance only; public access/rate controls, OS isolation, broader platforms/fonts/layouts remain unqualified. Bounded temporary state uses product budgets documented in the runtime guide.

## Progress Tracking and Resume

Status, checkpoint, decisions and test history synchronized. Stage 2 completed; awaiting user review/manual commit/push and explicit Stage 3 authorization. Read AGENTS, these records, audit/runtime docs and relevant source; inspect read-only Git state and preserve all existing uncommitted work. No automatic advance or Git writes.

## Suggested Commit Message

refactor: consolidate conversion runtime inside Next.js
