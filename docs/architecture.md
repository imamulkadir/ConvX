# Architecture — Stage 1 design

Status: Stage 1 design, updated 2026-11-05 after Stage 2 implementation. API, durable jobs, private local storage, outbox dispatcher and Celery admission worker are implemented. Conversion, frontend, object storage and deployed sandbox remain future stages. See [backend operation](backend-development.md) for current behavior and limitations.

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

Design target: self-hosted, licensed Aspose.Words adapter for revision acceptance and PDF export, subject to Stage 3 qualification. Vendor documentation describes revision acceptance and PDF rendering without Office ([revision support](https://docs.aspose.com/words/python-net/track-changes-in-a-document/), [PDF export](https://docs.aspose.com/words/python-net/convert-a-document-to-pdf/)). This is a candidate, not a fidelity claim. Validate licensing, runtime/platform support, fonts, unsupported revisions, evaluation restrictions and the full reference regression before enabling strict production jobs. Never use watermarked/evaluation output as accepted output.

LibreOffice is an explicitly selected fallback only after separate qualification; it has a documented [headless command-line mode](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html). Give each process its own profile, disable macros and network access, terminate the process tree on deadline, and report font substitutions. Never silently change providers on a failed fidelity gate.

Microsoft states unattended, noninteractive [server-side Office automation is unsupported](https://support.microsoft.com/en-gb/visio/considerations-for-server-side-automation-of-office). Therefore Word COM is excluded from the production worker design. Desktop Office licensing is not assumed to cover a server workload. Any supported Microsoft service alternative needs separate support, licensing, confidentiality and revision-capability review. No proprietary SDK, Office or LibreOffice conversion was executed in Stage 1.

## Trust and lifecycle

Reverse proxy -> authenticated API -> private upload -> database/outbox -> Redis -> isolated worker -> gated artifact publication -> authenticated streaming download. Pass IDs through the broker, not disclosure text or file contents. Service identities receive only the storage permissions they need. Renderer processes have no outbound network, a read-only runtime, private temporary directory and bounded memory/CPU/process counts.

Cancellation marks a requested state and stops active process trees; all publication paths recheck cancellation, lease ownership and expiration immediately before a transaction makes a result available. Deletion revokes access first, cancels work, then removes artifacts with retryable cleanup. Retention expiration follows the same path. Incomplete attempts never become downloadable.

## Stage sequencing

1 architecture; 2 backend; 3 revisions/PDF; 4 layout; 5 HTML; 6 compliance; 7 visual validation; 8 ZIP; 9 frontend; 10 integration; 11 deployment; 12 audit. Each stage requires explicit authorization. Converter contracts remain planned; Stage 2 admission/lifecycle behavior is documented separately.
