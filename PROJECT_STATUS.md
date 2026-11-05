# EDGAR Converter - Project Status

## Overall Status

Current Stage: 9 - Next.js Frontend

Stage Status: completed

Last Completed Stage: 9

Next Stage: 10 - Full Integration and Testing (requires explicit authorization)

Last Updated: 2026-11-05 (Asia/Dhaka)

## Project Objective

Build a free secure DOCX-to-PDF-to-searchable EDGAR HTM web application. Compliance, disclosure integrity and strict visual evidence control ZIP eligibility. No paid/trial renderer or premium service is included.

## Completed Stages

1. Requirements and architecture, immutable fixtures/manual evidence and recovery records.
2. Backend admission, private storage, persistent jobs/outbox and independent workers.
3. Revision acceptance, free native LibreOffice PDF and strict reference comparison.
4. Hash-bound PDF layout and nonqualifying diagnostic inspection.
5. Searchable HTM reconstruction with explicit unsupported cases.
6. Versioned actual-file SEC validation and image normalization.
7. Pinned Chromium print/screen/content/geometry/pixel comparison.
8. Deterministic clean ZIP, independent audit and protected download checks.
9. Next.js JSX web workspace and protected diagnostic previews. User authorized with continue. Stop before Stage 10.

## Current Stage and Implemented Features

Added apps/web: Next 16.4.5, React 19.3.1, Tailwind 4.3.4, DaisyUI 5.7.50, Lucide 1.69.0 and PDF.js 6.5.438. JSX/JavaScript only, npm lock, independent UI/API, no heavy Next conversion route. Trusted same-origin API rewrites forward each user's bearer header. Token stays in page memory; only opaque tab job IDs and local theme preference persist.

Batch picker/drop, configured file/request/batch limits, empty/extension checks, removable selection and actual XHR upload progress. Actual jobs poll without overlapping cycles; failures back off and remain visible. Search/filter, per-document stage/check/diagnostic/manual/remediation views, job-ID recovery, confirmed cancellation/removal and eligible retry are implemented. Downloads require actual backend availability and final checks, never UI assumptions.

Authenticated session returns admission limits. Owned stopped-attempt preview serves bounded current generated PDF or declared PNGs after source/PDF/path/state/retention checks. PDF.js uses a local worker, no eval/XFA or mounted annotations. HTM is a real existing Chromium capture, with print overlay/difference, page/zoom and synchronized scrolling controls. Missing captures after prior failures are explained; no active untrusted HTM is served. Diagnostic previews never grant eligibility.

Responsive light/dark workspace, reduced motion, visible focus/labels/skip link, keyboard tabs and native focus-trapped help. Actual desktop/mobile screenshots inspected. See [frontend operation](docs/frontend.md), [interfaces](docs/interfaces.md), [decisions](docs/decisions.md) and [redacted evidence](docs/stage9-frontend-regression.json).

## Reference Qualification and Known Limitations

Original fixtures remain unchanged. Supported revision acceptance removes 31 markers, retains ordered content/table structure across 18 stories and preserves five media parts; complete DOCX formatting equivalence remains unproven. Actual free LibreOffice export has 23 pages but fails strict Word-reference fidelity on all 23. Normal conversion stops before layout/HTM. Native inspection retains 85,798 characters but never approves reconstruction. See [PDF qualification](docs/stage3-regression.md).

Styled HTM still fails unresolved CSS/MANY/Unicode permission checks. Whole encoded submission/form context is not supplied by ordinary uploads. Actual print equality can retain screen differences (1,169 in the earlier smoke). No gate relaxation, source substitution, rasterized disclosure or fabricated passing engine/result occurred. No SEC acceptance is claimed.

No successful fully qualified filing ZIP/HTTP download has been demonstrated. UI download controls are implemented and stay disabled for genuine failed/queued jobs. Positive complete pipeline remains Stage 10 qualification. Chromium captures can be absent after earlier failures; PDF.js is a diagnostic review view, not new fidelity proof. PNG routes are API-tested; native UI browser review exercised real PDF plus honest missing-HTM behavior.

During native UI setup, longer Windows system-TEMP/UUID storage produced INVALID_PDF_OUTPUT; a shorter owned ignored var/stage9 path succeeded and retained actual SEC failure. Arbitrary Windows path lengths remain unqualified. Only Chromium and automated axe/inspected responsive views were checked; manual assistive technology/other browsers, real Redis/PostgreSQL and Linux OS/network/process deployment remain pending. No hosted deployment occurred. See [limitations](docs/limitations.md).

## Files Created or Modified

Added JSX app/components/hooks/API/job helpers, local PDF worker-copy script, locked npm config, Node/Playwright/axe tests and disposable real API/native browser launcher. Added diagnostic previews service, session/preview routes and nine API preview tests. Updated ignore rules, README/AGENTS, architecture/interfaces/backend/limitations/decisions, frontend docs and persistent records. No fixture or Git-state writes.

## Tests Executed

Recovery focused run: 87 passed. Full Python command: 363 passed, 0 failed, 2 optional service skips, one existing Starlette/httpx warning, 86% parent coverage, 267.24 seconds. After the capture-DPI metadata addition, focused API/preview boundary run passed 28 tests and final preview rerun passed 9/9 in 6.17 seconds. Child/manual coverage is not collected.

Final npm test: 3 passed. Production build passed. Final npm run test:ui: 5 passed against actual disposable API/SQLite and native LibreOffice negative job. Covers independent batch/drop admission, theme/reconnect/ID recovery, removal, invalid access/files, keyboard tabs/help, nonblank actual PDF canvas, missing HTM explanation and axe checks on empty/queued/failed/light/dark states. No mocked conversion success or Redis deployment is claimed.

Prettier check passed; Ruff lint/format passed (103 Python files); pip check clean; npm audit reported zero advisories. Initial tests exposed wrong build-time proxy origin, missing test-only import root, mixed file-path/buffer input fixture, test ambiguity with Next route announcer, unavailable dimension-mismatched screen diff, and two contrast issues. Corrected implementation/test boundaries; no fidelity rule was weakened. Detailed chronology is in [append-only test history](docs/test-history.md).

## Architectural Decisions

ADR-029: independent JSX UI/per-user authorization. ADR-030: diagnostic previews separate from eligibility. ADR-031: actual API/native negative UI qualification. Free LibreOffice and all PDF/SEC/visual/ZIP gate policies remain unchanged.

## Pending Tasks and Next Actions

User review/manual commit/push and explicit authorization before Stage 10. Next: genuine whole-pipeline integration, resolve actual PDF/SEC/screen failures, qualify successful final package/download, then deployment/security work in Stage 11. No automatic continuation.

## Suggested Commit Message

feat: add filing workspace UI and protected diagnostic previews

## Resume Instructions

Read AGENTS.md, this file, checkpoint, decisions/history and frontend docs; inspect read-only repository state and verify tests. Stage 9 is complete and awaits review. Leave unrelated changes untouched. Never perform Git writes. Begin Stage 10 only after explicit authorization.
