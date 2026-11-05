# ConvX ? Simplification Refactor Status

## Overall Status

Workflow: simplification-refactor (revised AGENTS.md; same existing repository)

Current Stage: 1 - Existing Project Audit

Stage Status: completed

Last Completed Stage: 1

Next Stage: 2 - Simplify Architecture (explicit authorization required)

Last Updated: 2026-11-05 (Asia/Dhaka)

## Objective and Mode Contract

One simple page accepts DOCX/PDF, defaults to Standard mode (.html with embedded modern CSS), optionally selects SEC EDGAR (.htm with confirmed manual-permitted markup/JPG/GIF), then returns input-basename.zip containing only the document and its referenced root-level assets. Processing stays local, with a single Next application invoking bounded Python processes. No user-managed API connection, Redis/Celery/database/accounts. This is the revised target, not implemented behavior.

## Stage 1 Findings and Completed Work

Inspected current UI, API/admission/config/database/workers, DOCX revision/PDF providers, shared extraction/model, renderer, assets, SEC validation, visual checks, packaging, dependencies and tests. The existing workflow is DOCX-only and couples reconstruction/publication to external Word-reference and SEC gates. No Standard renderer, direct PDF upload, optional EDGAR mode or .html packaging exists.

Useful components include supported revision acceptance, bounded native rendering/process controls, detailed PDF extraction, manual-derived SEC checks, graphics decoding, comparison metrics and real archive audit. Plan to adapt these while retiring public FastAPI, queues/broker/database orchestration and connection/dashboard UI after working replacements exist. No runtime code or service was removed in Stage 1.

Created [audit and staged migration plan](docs/refactor-audit.md), corrected contradictory mode extensions in AGENTS.md and updated recovery instructions. Preserved prior records byte-for-byte in [historical status](docs/history/pre-refactor-status.txt) and [historical checkpoint](docs/history/pre-refactor-checkpoint.json). Original nine implementation stages and live startup/reference tests are history, not completion of the revised refactor stages. Root checkpoint schema 2 identifies the new workflow explicitly.

## Files Changed in This Stage

AGENTS.md, README.md, PROJECT_STATUS.md, .agent-checkpoint.json, docs/refactor-audit.md, docs/history/pre-refactor-status.txt, docs/history/pre-refactor-checkpoint.json, docs/decisions.md, docs/test-history.md and tools/verify_stage1.py. The verification helper now distinguishes existing-project audit from the original empty-project stage. All pre-existing modified/untracked application/startup files were preserved; no application refactor or Git write.

## Tests Executed

Focused existing converter unit suite: 216 passed, 0 failed, one existing Starlette/httpx warning, 9.70 seconds. Covers revisions, PDF analysis, legacy HTM, SEC/assets and packaging mechanics. Node helper tests: 3 passed. Frontend format check and pip check passed. Initial historical fixture/context checker: 7 passed / 1 failed because revised AGENTS.md removed its recovery phrase; restored compatible onboarding and made the scope check workflow-aware. Final fixture/context checks passed 8/8; archived SHA-256, active documentation links and read-only diff checks passed.

No full suite, new conversion, native Word-reference rerun, browser UI suite, production build or deployment was run for this audit. Passing existing tests does not qualify the revised input/mode combinations.

## Known Bugs and Limitations

Legacy runtime still requires a separate reference before production PDF analysis. Prior actual fixture test failed all 23 Word-reference PDF pages. Current generated styling fails unresolved SEC permissions/character interpretation. No working Standard HTML5 renderer or scanned-PDF OCR. Existing .htm-only/JPG-GIF-only ZIP checks cannot support the revised Standard path unchanged. Complex layouts/font permission, Windows long paths, wider browsers and deployment isolation remain unqualified. Fixtures and user artifacts remain unchanged.

## Decisions and Pending Tasks

See ADR-033 onward in [decisions](docs/decisions.md). Next Stage 2 replaces infrastructure with minimal internal Next handlers and bounded Python processes, separates admission/config from app imports and preserves existing security/content behavior. Later stages add unified inputs, shared layout, mode-specific renderers/ZIP and the minimal UI. Do not relabel diagnostic or self-comparison evidence as old strict qualification. The generated/uploaded PDF becomes the runtime visual authority under an explicit revised contract; Word fixture matching remains regression evidence.

## Suggested Commit Message

refactor: audit existing converter and plan simplified dual-mode architecture

## Resume Instructions

Read AGENTS.md, this file, checkpoint, audit, decisions and relevant test history. Inspect actual source and read-only Git state; preserve all uncommitted prior work. Stage 1 is complete and awaits manual review/commit/push. Begin Stage 2 only after explicit authorization. No automatic continuation or Git writes.
