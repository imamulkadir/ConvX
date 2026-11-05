# Simplification refactor — Stage 1 audit

Date: 2026-11-05. Scope: existing repository audit and design only. No application refactor, service removal, dependency installation, queue operation or new conversion is performed in this stage. Existing modified/untracked startup-repair files are preserved. This new stage numbering follows the revised AGENTS.md; earlier implementation history remains valid historical evidence, not completion of the revised stages.

## Requirements that now govern the application

One page accepts DOCX or PDF, an unchecked-by-default SEC EDGAR checkbox, a conversion action, simple progress and a ZIP download. Standard mode generates **.html** with embedded modern CSS and referenced modern assets. EDGAR mode generates **.htm** with only manual-permitted markup and JPG/GIF. Both use one analyzed PDF model and preserve selectable disclosure rather than page screenshots. The final extension update overrides all earlier both-modes-.htm statements; those contradictions are removed from the active instructions.

The authoritative layout source is the uploaded PDF or the PDF actually generated from accepted DOCX. The Word fixture PDF remains a regression comparison, not an extra file every user must supply. Renderer differences from Word must be reported accurately. Existing strict safety/content checks must be preserved; the old Word-reference eligibility contract must be deliberately replaced for the new workflow, not tricked with self-comparison or relabelled inspection evidence.

## Verified current state and requirement gaps

| Area | Existing evidence/code | Gap under revised requirements |
| --- | --- | --- |
| Startup | dev.py starts Next, FastAPI and an independent SQLite local worker; default infrastructure is Redis/Celery | One command still hides several services and database/account machinery. Replace runtime rather than require users to manage it. |
| Browser | apps/web/components/workspace.jsx, hooks/use-workspace.js, lib/api.mjs | DOCX-only batch dashboard, API connection/token/local-access form, recovery/search/preview tooling; no EDGAR checkbox or Standard mode. |
| Admission | services/api/app/services/admission.py; storage.safe_filename | Strong bounded DOCX ZIP/XML checks, but path/type admission and saved source.docx assume DOCX. No PDF upload API. |
| Revisions | converter.revisions and ooxml | Deterministic supported revision acceptance/media preservation; unsupported revisions fail safely. Reuse. |
| PDF export | converter.pdf_export.libreoffice/process | Real free LibreOffice, private profile/process budgets/cancellation. Word equivalence is unproven; Windows long workspace paths have failed. Retain with explicit diagnostics. |
| Orchestration | converter.pipeline.process_docx, cli.py | DOCX-only. Requires separate reference PDF and strict matching before analysis. Imports API admission/settings through CLI. No unified input-kind/mode boundary. |
| Layout | converter.pdf_analysis and layout | Detailed native text/typography/graphics/tables/reading order. Its production gate/schema requires legacy strict reference evidence; inspection is explicitly ineligible. Extractor internals are reusable, eligibility contracts need redesign. |
| Renderer | converter.html_generator | Only conservative EDGAR-oriented normal flow. Rejects rotations/overlaps/complex paint. No modern positioned Standard renderer. |
| Assets | converter.assets.normalize | Source-bound real graphics and content checks, constrained to SEC JPG/GIF. Cannot serve both modes unchanged. |
| SEC rules | converter.sec_validation/efm-v78.2.json and validator | Actual-file/manual-derived diagnostics, with unresolved CSS/MANY/character permissions. Preserve fail-closed EDGAR behavior. Do not apply it to Standard mode. |
| Visual checks | converter.visual_validation | Real controlled Chromium/PDF/content/geometry/pixels. Production entry depends on strict SEC and external reference; inspection also applies SEC-related safety policy. Reuse measurement/process controls, separate mode-specific validation. |
| Packaging | converter.packaging | Real deterministic root-only ZIP, CRC/header/manifest checks. Names accept only .docx and always .htm; archive permits only .htm/.jpg/.gif and requires SEC/legacy visual evidence. Generalize by explicit mode. |
| OCR | PDF parsing tests and local executable discovery | No OCR pipeline; tesseract was not found on PATH. Scanned/uncertain-text documents need an honest diagnostic or explicitly verified optional OCR later. |
| Completion | docs/live-instance-regression.json | Real original DOCX upload blocked on reference; matching reference then failed all 23 PDF pages. No qualified filing ZIP produced. Do not reinterpret these as successful conversions. |

## Reuse, adapt and retire

Retain converter.revisions, ooxml, PDF export provider/process runner, PDF layout extraction primitives, Pydantic records, actual SEC registry/validator, graphic decoders, geometry/pixel measurements, atomic file publication and archive audit concepts. Keep useful fixtures, tests, locked dependencies and append-only decisions/history. Reuse Next/JSX/Tailwind/DaisyUI/Lucide, accessible inputs, real upload progress, light/dark styling and clear error handling.

Adapt admission into a converter-level module independent of app Settings/Problem; split configuration into small conversion limits and renderer configuration. Refactor layout provenance into validated input-PDF/generated-PDF sources with shared safe extraction, rather than promoting inspection flags. Keep generator-specific unsupported layout judgments out of shared parsing where another renderer can faithfully handle them. Reuse EDGAR flow rendering where supported; implement Standard rendering separately from the same model.

Retire the runtime FastAPI server, SQLAlchemy models/repositories, PostgreSQL client, Redis/Celery/outbox/heartbeat services, token-account connection UI and separate API reverse-proxy configuration after replacements work. The local development queue is a transitional repair, not the target architecture. Preserve historical reports and the user's stored documents; retiring runtime paths must not erase personal .env, var/artifacts, existing database, unrelated files or Git state. Do not uninstall packages from the user's environment as part of an application dependency cleanup.

Dependency removal candidates: FastAPI, Uvicorn/Starlette, SQLAlchemy/psycopg, Redis/Celery and their broker/process helper dependencies. Audit imports/lock resolution before removing transitive packages; some HTTP/async packages may still support tests/Playwright. Keep PyMuPDF, Pillow, lxml, Pydantic, psutil and practical visual-comparison tooling. Keep PDF.js only if the simplified UI actually retains a preview; it is not needed for a minimal download utility. No new OCR, font or multipart dependency is approved by this audit without a demonstrated need.

## Target architecture and boundaries

```text
One Next.js page
    -> internal Node request/status/download handlers
    -> bounded private per-conversion directory and small file manifest
    -> directly spawned Python conversion process (no public Python API)
    -> input admission -> DOCX acceptance/native PDF export OR original PDF
    -> shared safe PDF analysis/model
    -> Standard HTML5/CSS renderer OR EDGAR renderer
    -> mode-specific validation + practical visual/content measurements
    -> mode-specific root-only ZIP audit
    -> download and temporary-file cleanup
```

Use the Node runtime, not Edge/serverless assumptions. Child processes have fixed trusted argv, bounded concurrency, time/RSS/output/disk controls and no shell interpolation. An internal lightweight file-manifest job/status endpoint is sufficient for conversions exceeding request timeouts; no database, broker or user-managed worker. Restarted/interrupted tasks must become clear failures, never invented completions. Source uploads, logs and reports stay outside the final ZIP. Downloads recheck current manifest/assets and expose only opaque unguessable job capabilities; default binds loopback. Public deployment requires appropriate access/rate controls without an initial account system.

Stream/bound input bytes and verify signatures in Python after filename checks; do not trust extension/MIME or Content-Length alone. Reuse ZIP-bomb/XML defenses. PDF admission must reject invalid/encrypted/active/unsupported packages with meaningful diagnostics and bound pages/pixels/parser work. No external fetches or macro execution. Clean only resolved owned temporary paths, including Windows path constraints, and never the source fixtures.

Proposed engine boundary: input path, original basename, explicit standard/edgar mode, owned output directory and limits. Shared PDF output/layout is consumed by exactly one selected renderer. Result records include actual input/PDF hash, chosen mode, content/asset checks, measured fidelity/limitations, local SEC result when applicable, archive name/member hashes and clear completion/failure. Never use fabricated submission size or SEC acceptance flags to make EDGAR pass.

## Mode-specific behavior

| Concern | Standard (default) | EDGAR |
| --- | --- | --- |
| Internal document | Exactly one .html | Exactly one .htm; manual filename constraints |
| Styling | Embedded CSS, positioned page containers/transforms where useful | Confirmed manual-permitted markup/style only |
| Text | Selectable/searchable exact content; safe renderer-generated markup | Exact disclosure with manual-compatible encoding |
| Graphics | Locally referenced JPG/PNG/GIF/SVG/WebP as required | Validated JPG/GIF only |
| Fonts | Source/system metrics; font embedding only when permission verified | No external/unsupported font resources |
| Safety | No script dependencies/remote resources; safe static markup/assets | Same safety plus manual restrictions |
| Verification | Real source-PDF text/pages/assets/geometry and measured render differences | Same measurement plus actual-file SEC validation |
| ZIP | Input basename.zip, document and referenced permitted assets at root | Same root-only contract with EDGAR names/formats |

The new model must distinguish content/safety failure from measured visual limitation. User instructions require maximum achievable fidelity and honest reporting, not the old globally coupled zero-difference/Word-reference publication gate. Define this contract explicitly in the relevant stages; never silently call mismatching output pixel-perfect. Preserve original Word-reference differences as regression evidence. Legal font-embedding permission cannot be inferred solely from PDF presence. No full-page screenshot/outlined disclosure substitution is allowed.

## Stage sequence and review boundaries

1. Audit only (this document, progress migration and checks). No runtime change.
2. Simplify runtime/config/dependencies: Next internal handler -> Python process, bounded private manifests, one startup; migrate CLI admission away from app imports. Keep a real legacy-backed processing path with explicit existing limitations. Do not claim Standard/PDF support before their stages. Retire old service paths only after startup/status/failure behavior works.
3. Add safe DOCX/PDF admission and unified PDF entry; make generated/uploaded PDF authoritative; external Word fixture comparison becomes a regression path, not a routine upload prerequisite. Add scanned/encrypted/malformed diagnostics without invented OCR.
4. Adapt shared layout schema/provenance and retain bounded extraction; test mixed sizes/orientation, columns, borders, image placements and reading/content integrity. Preserve explicit uncertainty.
5. Implement Standard modern renderer, local modern assets and permitted fonts; exact selectable text and measured multi-layout comparisons. No SEC validation on Standard output.
6. Adapt and verify the EDGAR renderer, confirmed registry restrictions, JPG/GIF and errors for unresolved permissions/unsupported layout. Local compliance is not SEC acceptance.
7. Implement/audit mode-specific document extension and allowed asset sets; preserve original ZIP basename; exact reference/CRC/root checks, no reports/intermediates/unused files.
8. Replace dashboard/auth panels with the specified single upload/checkbox/action/progress/download page, accessible responsive light/dark UX. Checkbox default is false and maps to Standard .html.
9. Genuine live tests for all four input/mode combinations, including actual ZIP contents and all-page fixture/independent layout regression. Record real EDGAR failures if unresolved; do not call a major broken path complete.
10. Final cleanup, dependencies/security/performance/error/output audit and documentation; no new enterprise infrastructure.

Do not compress the implementation stages into this audit or pretend removing a gate implements a renderer. Approval is required after each stage.

## Current checks and remaining qualification

Focused legacy engine tests: 216 passed, one existing Starlette/httpx warning, 9.70 seconds. They cover revisions, native PDF analysis, existing HTM generation, SEC/asset validation and archive mechanics; they do not prove the revised four conversion paths. Node helpers: 3 passed. Frontend formatting passed. pip check clean. Legacy fixture/context checker initially passed seven of eight, failing because the revised AGENTS.md omitted its expected recovery phrase. Restored that consistent onboarding instruction and made the historical scope check phase-aware: an existing-project audit must not assert that application directories are absent. Final fixture/context checks are recorded in test history.

No new browser/Word export/23-page conversion, full suite, production build, OCR or public deployment was run for this documentation-only audit. Previous real native reference failures remain in historical reports. All five current fixtures (including the additional Volume I manual) remain unchanged. Plan further tests by implementation stage rather than delete old tests to hide incompatible assumptions.

## Exit from Stage 1

Archive the pre-refactor status/checkpoint so the nine old stages and user-authorized startup/live checks remain recoverable. Root progress records now track the revised workflow at Stage 1 completed, next Stage 2 awaiting explicit approval. Correct active extension contradictions in AGENTS.md. No application code, credentials, user data, live service or Git state is changed. Review and commit the audit documentation manually before authorizing Stage 2.
