# Architecture — Stage 1 design

Status: Stage 1 design, updated 2026-11-05 after Stage 3 implementation. API, durable jobs, private storage/outbox, revision acceptance, free LibreOffice PDF export and strict PDF gates are implemented. HTM/layout reconstruction, frontend, object storage and deployed sandbox remain future stages. See [backend operation](backend-development.md) and [document processing](docx-processing.md) for actual behavior and limitations.

## Boundaries and stack

The Next.js App Router frontend uses JavaScript/JSX, React, Tailwind, DaisyUI and Lucide. It submits multipart uploads to FastAPI and observes jobs through polling or authenticated SSE. It performs no conversion. FastAPI/Pydantic owns authentication, streaming admission, job ownership, state transitions and authorized artifact access. Celery workers execute the PDF-first converter using Redis as broker, not as the authoritative job database.

PostgreSQL is the production job/event database; SQLite may support single-host development behind the same repository interface. An outbox transaction records jobs and enqueue requests together. Dispatch is at least once: workers claim jobs with leases, compare-and-swap state versions and attempt identifiers. Duplicate deliveries cannot publish a second result. Worker crashes expire leases; only transient infrastructure failures retry with bounded backoff. Invalid content, unresolved revisions, compliance failures and fidelity failures are terminal.

Private filesystem storage serves single-host development. Production uses private object storage plus per-attempt local scratch. Database records reference opaque artifact IDs, never user-controlled filesystem paths. Uploads, accepted DOCX, PDFs, layout data, previews, comparisons and reports remain private and separate from publication candidates.

## Module allocation

| Planned directory | Responsibility |
| --- | --- |
| `apps/web` | Uploads, batch dashboard, diagnostics, authenticated preview and download |
| `services/api/app/{api,core,models,schemas,services}` | API contracts, configuration, job persistence and ownership |
| `packages/converter/revisions` | Revision inventory, acceptance, independent unresolved-revision scan |
| `packages/converter/pdf_export` | Provider adapter and strict PDF gate |
| `packages/converter/pdf_analysis` | PyMuPDF extraction with provenance and confidence |
| `packages/converter/layout` | Versioned layout model independent of HTML |
| `packages/converter/html_generator` | Manual-constrained reconstruction and explicit incompatibilities |
| `packages/converter/assets` | Local JPG/GIF normalization using Pillow; supported vector rasterization |
| `packages/converter/sec_validation` | Source-byte and parsed-file validation against approved registry |
| `packages/converter/visual_validation` | Pinned Chromium/Playwright, PDF renders, content and geometry comparisons |
| `packages/converter/packaging` | Deterministic root-only ZIP and independent reinspection |
| `packages/converter/pipeline.py` | Sequential gates, attempt manifest and cancellation checkpoints |
| `workers` | Celery entry points and isolated renderer orchestration |
| `infrastructure` | Later Docker, reverse proxy, sandbox and deployment definitions |

Use Python typed functions, Pydantic boundary validation, explicit error codes and small provider protocols. Use JSX, never TypeScript. Pin dependencies and renderer/browser/font versions when their implementation stages begin. Preserve source text and provenance; never introduce fixture-specific layout rules. Tests must exercise outcomes and failure boundaries. Creating empty application modules now would imply progress that has not occurred.

## Rendering decision

Stage 3 user requirement: all components must be free of charge, with no premium licensing. The former Aspose candidate is superseded and is not implemented, installed or supported by configuration. Revision acceptance uses an explicit deterministic OOXML subset with independent audits; PDF export uses free LibreOffice. See [document processing](docx-processing.md). Unsupported revisions and strict layout mismatches fail safely.

LibreOffice is the selected free renderer, with a documented [headless command-line mode](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html). Each attempt has its own profile, macro-disabled settings, bounded resources and cancellation checks. OS-level network isolation remains Stage 11 work. Native Word-baseline qualification failed on all 23 pages; no alternate renderer is silently selected and no strict gate is relaxed.

Microsoft states unattended, noninteractive [server-side Office automation is unsupported](https://support.microsoft.com/en-gb/visio/considerations-for-server-side-automation-of-office). Word COM remains excluded. Paid Microsoft/commercial service alternatives are outside the user's free-only scope. Stage 3 executed actual local LibreOffice exports; the historical Stage 1 provider evaluation is retained only in the decision log.

## Trust and lifecycle

Reverse proxy -> authenticated API -> private upload -> database/outbox -> Redis -> isolated worker -> gated artifact publication -> authenticated streaming download. Pass IDs through the broker, not disclosure text or file contents. Service identities receive only the storage permissions they need. Renderer processes have no outbound network, a read-only runtime, private temporary directory and bounded memory/CPU/process counts.

Cancellation marks a requested state and stops active process trees; all publication paths recheck cancellation, lease ownership and expiration immediately before a transaction makes a result available. Deletion revokes access first, cancels work, then removes artifacts with retryable cleanup. Retention expiration follows the same path. Incomplete attempts never become downloadable.

## Stage sequencing

1 architecture; 2 backend; 3 revisions/PDF; 4 layout; 5 HTML; 6 compliance; 7 visual validation; 8 ZIP; 9 frontend; 10 integration; 11 deployment; 12 audit. Each stage requires explicit authorization. Converter contracts remain planned; Stage 2 admission/lifecycle behavior is documented separately.

Stage 4 implementation adds the PDF layout boundary described in [layout analysis](pdf-layout-analysis.md). Workers analyze only strictly validated generated PDFs and write private attempt-local `layout.json`; diagnostic inspection is separately marked ineligible. Stage 5 HTML remains unavailable.

Stage 5 adds a manual-constrained normal-flow HTM generator after the strict PDF/layout gates. Private candidate generation and graphic requests do not authorize downstream success. Supported content/geometry, resource bounds and unsupported cases are documented in [HTM reconstruction](htm-reconstruction.md).
