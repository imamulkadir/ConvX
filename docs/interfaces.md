# Proposed module and API contracts

Stage 3 implements the revision/PDF subset of the converter contracts below; layout/HTM/compliance/visual-HTM/packaging remain future specifications. Current [backend operation](backend-development.md) and [document processing](docx-processing.md) describe actual signatures and behavior. Schema v1 remains compatible. Converter processing modules do not import FastAPI or Celery; the CLI admission/orchestration boundary uses the installed backend package.

## Shared records

`Job`: UUID, owner_id, original_filename (display only), source_sha256, state, stage, state_version, attempt_id, lease_until, cancel_requested, created_at, updated_at, expires_at, renderer_profile_id, rule_profile_id, comparison_profile_id, diagnostic_ids, artifact_ids. Persist timestamps in UTC and expose ISO 8601. Batch uploads create independently owned jobs; frontend groups their IDs.

`ArtifactRef`: opaque ID, job_id, attempt_id, kind, private storage key, sha256, byte_count, media_type. `Diagnostic`: code, severity, stage, description, artifact_id/file, element path, page/bbox where applicable, manual section/rule_id if applicable, remediation, resolved flag, evidence IDs. Reports contain private document excerpts only when necessary and never enter logs or ZIPs.

`GateResult`: passed, diagnostics, evidence references, method/version, configuration hash. Unknown is not passed. `ProviderCapabilities`: provider/version, revision types and supported stories, font environment hash, licensing status. `RevisionResult`: accepted_docx, before/after revision inventories, media integrity report, unsupported features. `PDFResult`: generated_pdf, provider profile, font substitution diagnostics. Do not compare DOCX binary equality as content equivalence.

## Sequential callable boundaries

| Protocol operation | Input | Output / rejection |
| --- | --- | --- |
| `validate_docx` | Private source, admission limits | Safe package inventory; reject ZIP/XML hazards |
| `accept_revisions` | Validated package, provider profile | RevisionResult; fail unsupported or remaining revisions |
| `export_pdf` | Accepted DOCX, renderer profile | PDFResult; never substitute reference PDF |
| `validate_pdf` | Generated PDF, optional authorized reference, comparison profile | GateResult with all-page dimensions, text and render evidence |
| `analyze_pdf` | Validated PDF, accepted DOCX hints | DocumentLayout v1 with extraction diagnostics |
| `generate_htm` | Layout, approved rule profile | Candidate HTM + asset requests + incompatibilities |
| `normalize_assets` | PDF graphics, asset requests | Root-relative names and asset manifest |
| `validate_files` | Actual HTM/assets, rule profile, submission context | GateResult, including source bytes and references |
| `compare_visuals` | PDF, local HTM/assets, fixed browser/fonts/profile | All-page content, geometry and pixel GateResult |
| `correct_layout` | Evidence-backed discrepancies | Bounded candidate update; invalidate subsequent gate results |
| `package` | Current passing gates + exact candidate manifest | ZIP; independent reopened archive inspection |

Each operation receives a deadline and cancellation context. Publish only outputs of the current attempt. Safe corrections cannot alter disclosure text, bypass rules or rasterize pages. Re-run compliance and visual gates after every correction. Stop on repeated candidates or configured correction budget; unresolved differences fail strict mode.

## DocumentLayout v1

Document: source PDF SHA-256, schema/extractor versions, provider/font profile, metadata, ordered pages, assets, semantic hints and diagnostics. Coordinates are PDF points, top-left origin, explicit normalized rotation transform, original MediaBox/CropBox and page index (one-based externally). Store floats without early rounding.

Page: geometry, reading-order graph, text blocks/paragraphs/lines/spans/characters, tables/cells/merged-cell relations, images, vectors, links, header/footer candidates and uncertainty. Every object has stable ID, source page/bbox, provenance and confidence. Text includes exact Unicode, font family and PDF font identity, size/weight/style/color, baseline/direction, character boxes, superscript/subscript and underline evidence. Distinguish inferred semantics from extracted facts. Images include source IDs, placement matrix, clipping, color space and alpha. Vectors include paths, strokes, fills and clipping. Unsupported rotation, glyph mapping or table ambiguity produces a diagnostic, never invented content.

## API v1

| Endpoint | Planned behavior |
| --- | --- |
| `POST /api/v1/conversions` | Authenticated multipart batch; stream per-file limits; 202 with job IDs; structured per-file admission errors; idempotency key scoped to owner |
| `GET /api/v1/conversions/{id}` | Owned job state, stage, diagnostics summary, available artifact kinds |
| `GET /api/v1/conversions/{id}/events` | Owned SSE stream with monotonic event IDs, replay cursor, heartbeat; polling alternative |
| `GET /api/v1/conversions/{id}/preview` | Owned artifact selector, page and short-lived isolated preview access |
| `GET /api/v1/conversions/{id}/validation` | Owned detailed diagnostic/gate report |
| `GET /api/v1/conversions/{id}/download` | Stream final ZIP only for completed, unexpired job with current passing gates |
| `DELETE /api/v1/conversions/{id}` | Idempotent cancellation/deletion request; 202 during cleanup |
| `GET /api/v1/health` | Process liveness, no private infrastructure details |
| `GET /api/v1/readiness` | Database/broker/storage/worker capability checks; 503 when unavailable |

Use 401 unauthenticated, 404 for missing or unowned resources, 409 invalid lifecycle, 413 admission size, 415 wrong type, 422 invalid package, 429 quota and 503 infrastructure unavailable. Request/error bodies have stable codes and correlation IDs without document text. Preview assets require ownership too; no arbitrary path selector.

States: `queued -> running -> completed | failed | cancelled`; `expired` removes download eligibility. Running stages follow the mandatory pipeline, with a separate `cancelling` lifecycle if termination is pending. Persist events atomically with state. Progress is stage/page evidence, not simulated percentages. Packaging and completed state require all mandatory gates, including source/revision integrity, strict PDF, compliance, content and fidelity. Stage 2 must not simulate downstream conversion success.

Stage 2 extension: admitted sources enter `blocked / awaiting_conversion_engine` with `PIPELINE_NOT_AVAILABLE` after worker admission. `blocked` is a real unavailable-capability state, not conversion success. No path transitions to `completed` or publishes artifacts. Stage 2 uses `version`, timestamps and deleted/cleanup markers for job state; renderer/rule/profile/artifact schemas remain deferred until their corresponding stages. Events are bounded SSE replays followed by reconnect instructions. DELETE invalidates active attempts immediately and defers file removal through their lease deadline; future renderers must add process termination. The validation endpoint reports pending/failed gates without pretending an EDGAR validator exists.

Stage 3 extension: current workers implement accepted DOCX/PDF export/gates, record stage events and renew live attempt leases. Reports live under the current private attempt UUID; the owned validation endpoint returns structured processing evidence. Full conversion/SEC/fidelity flags remain false. Missing renderer/reference blocks; revision/PDF failures fail; a passing PDF blocks at `awaiting_pdf_analysis`. `POST /api/v1/conversions/{id}/resume` explicitly requeues eligible owned blocked jobs without reusing stale artifacts. No schema change or automatic replay of all Stage 2 jobs occurs. No ordinary API path accepts a server filesystem path; reference CLI paths and authorized internal reference provisioning are described in [document processing](docx-processing.md).

Stage 4 extension: `converter.pdf_analysis.analyze_pdf` consumes the actual PDF and a complete passing strict report; `DocumentLayout` schema v1 is defined in [layout analysis](pdf-layout-analysis.md) and [JSON Schema](layout-schema-v1.json). The model is private, immutable and source-hash bound; `inspect_pdf` is explicitly ineligible for reconstruction. Successful extraction ends at `blocked / awaiting_htm_generation` with `HTML_ENGINE_NOT_AVAILABLE`. Unresolved extraction blockers fail with `PDF_LAYOUT_UNRESOLVED`. No final completion/download or new public artifact route is added. Four environment settings configure text, vector, JSON and sampled-memory budgets.

Stage 5 extension: `generate_htm(layout, source_pdf, validation_report, output, policy, context)` revalidates the typed model and hash-bound passing evidence. It returns GenerationResult with private candidate hash/counts, asset requests and incompatibilities. Unsupported preflight leaves no candidate. Successful generation reports `htm_generated` and ends at `blocked / awaiting_sec_validation / SEC_ENGINE_NOT_AVAILABLE`; compliance, fidelity and completion stay false. Old HTML_ENGINE_NOT_AVAILABLE jobs support explicit owned resume. No new public artifact route. See [HTM reconstruction](htm-reconstruction.md).

Stage 6 extension: `normalize_assets` consumes source PDF, exact candidate/generation hashes and image requests, writes new private filing/ HTM/JPG/GIF files and records pixel changes. `validate_files` consumes actual HTM plus explicit same-root assets and optional SubmissionContext (form and complete MIME-encoded byte count). ComplianceResult distinguishes local passed, strict_passed with submission context, incomplete checks and unverified SEC/visual acceptance. Actual unresolved permissions fail. Passing file checks would stop at awaiting_visual_validation/VISUAL_ENGINE_NOT_AVAILABLE; no final completion/download. See [SEC validation engine](sec-validation-engine.md).

Stage 7 extension: `compare_visuals(source_pdf, htm, assets, pdf_validation, sec_validation, output, policy, context, submission, sec_policy)` binds source/file/gate hashes and rechecks strict prior evidence. `inspect_visuals` is explicitly nonqualifying and still requires source safety. VisualResult distinguishes complete measurements, comparison agreement and strict production eligibility. `visual_validated` stops at awaiting_packaging/PACKAGING_ENGINE_NOT_AVAILABLE; download remains unavailable. The owned API reports strict fidelity metadata only; raw artifacts stay private. See [visual validation](visual-validation.md).

Stage 8 extension: prepare_filing_name finalizes the internal name before SEC/visual checks; create_package requires current strict evidence and publishes a deterministic root-only ZIP after independent audit. PackageResult binds original/download names, manifest and gate hashes. completion_ready guards the completed transition; download_snapshot revalidates source/files/gates and captured archive bytes before owned streaming. No database schema change. Preview remains unavailable. See [ZIP packaging](zip-packaging.md).
