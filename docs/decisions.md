# Development decision log

## 2026-11-05 — ADR-001: PDF-first independent services

Decision: separate JSX Next.js, FastAPI, Celery and converter modules; generated accepted-DOCX PDF is the layout authority. Context: confidentiality and long-running conversions. Alternatives: Next.js conversion routes or generic DOCX-to-HTML. Reasoning: mandatory workflow and isolation. Consequences: independent deployment, persistent state, versioned layout and explicit gates. See architecture/interfaces.

## 2026-11-05 — ADR-002: Provider qualification

Decision: licensed self-hosted Aspose.Words candidate adapter, explicitly selected LibreOffice fallback, no production Word COM. Context: Microsoft does not support unattended noninteractive Office automation. Alternatives: COM, hosted conversion or LibreOffice alone. Reasoning: vendor-described revision/PDF capabilities support evaluation without external disclosure transfer; no engine assumed equal to Word. Consequences: Stage 3 licensing/platform/fonts and all-page qualification; fail when no provider qualifies. See architecture for primary sources. No SDK installed or qualified.

## 2026-11-05 — ADR-003: Evidence-based rules

Decision: bind registry to supplied Volume II v78 hash; distinguish manual facts, product policy and unresolved interpretations. Context: EDGAR differs from modern HTML, with table/example tensions. Alternatives: generic sanitizer or assumed CSS rules. Reasoning: traceable compliance and honest diagnostics. Consequences: design registry is not an approved strict validator; required unknowns block later strict success.

## 2026-11-05 — ADR-004: Durable jobs/private publication

Decision: PostgreSQL state/event/outbox store, Redis/Celery transport, private artifacts, leased idempotent attempts. Context: crashes/redelivery and cancellation races. Alternatives: Redis-only state or synchronous work. Reasoning: durable ownership and recoverability. Consequences: Stage 2 tests outbox/lease behavior; duplicate attempts cannot publish; downloads recheck access and passing gate hashes.

## 2026-11-05 — ADR-005: Strict fidelity evidence

Decision: all-page content, geometry and controlled raster comparisons; zero unexplained discrepancies. Context: antialiasing differs and scalar averages conceal lost content. Alternatives: screenshot threshold alone or full-page images. Reasoning: disclosure must remain selectable and verifiable. Consequences: pinned profiles, raw differences, bounded corrections and explicit failures; no premature pixel-perfect claim.

## 2026-11-05 — ADR-006: Updated fixture identities

Decision: preserve filenames and use hashes plus explicit aliases. Context: initial roles were reversed; user replaced DOCX fixtures and final roles agree. Alternatives: agent renaming/editing references. Reasoning: content evidence outranks suffix assumptions. Consequences: final inventory is baseline; Stage 3 establishes semantic equivalence and PDF correspondence, including differing media inventories.

## 2026-11-05 — ADR-007: Stage 2 capability boundary

Decision: workers perform actual source hash and package admission, then record `blocked / awaiting_conversion_engine` with `PIPELINE_NOT_AVAILABLE`. Context: only the backend foundation is authorized and no later conversion gate exists. Alternatives: fake conversion success, fail every upload as invalid, or leave already-admitted work silently queued. Reasoning: an explicit unavailable capability preserves truthful state and prevents unsafe download. Consequences: no completed-state/publication path is present; later stages must deliberately resume eligible blocked jobs and extend readiness. This job state is separate from AI stage-checkpoint statuses.

## 2026-11-05 — ADR-008: Durable dispatch and retention implementation

Decision: implement SQLAlchemy schema v1 for SQLite development/PostgreSQL production, atomic job/event/outbox writes, owner-row quota/idempotency serialization, versioned worker claims and tokenized dispatcher leases. Context: broker outages, duplicate deliveries, process crashes and cancellation/expiration races. Alternatives: direct enqueue only, Redis-only jobs or process-local state. Reasoning: durable outbox and compare-and-swap state changes recover without publishing stale work. Consequences: a supervised dispatcher is mandatory; artifacts are removed only after active admission leases, then expired metadata is purged. Stage 11 adds infrastructure enforcement and later schemas require explicit migrations. Redis/PostgreSQL live-service tests remain opt-in, not claimed as executed locally.

## 2026-11-05 — ADR-009: Inert source relationships and dormant declarations

Decision: preserve inert source HTTP/HTTPS/mailto hyperlinks as data without fetching; reject external images/templates/objects, active relationships/fields, macros and actual OLE parts. Evaluate active MIME declarations against existing parts. Context: the original fixture has an unused OLE default declaration but no `.bin` parts or object relationships. Alternatives: reject all source hyperlinks/unused declarations, or allow external rendering resources. Reasoning: preserve disclosure and admit valid fixture bytes while denying executable/resource dependencies. Consequences: source admission is distinct from final EDGAR hyperlink/asset validation; no rule relaxes final compliance and renderers must remain offline and disable field updates. No original fixture was rewritten.

## 2026-11-05 — ADR-010: Bounded authenticated event replay

Decision: SSE returns persisted events after a cursor and an explicit reconnect instruction instead of holding long polling threads and database transactions indefinitely. Context: expiry/deletion and bearer authorization must be checked regularly. Alternatives: unlimited streaming or polling alone. Reasoning: bounded replay supports reliable progress and reauthorization with simple resource bounds. Consequences: clients reconnect after two seconds using Last-Event-ID; ordinary polling remains available. No fabricated percentages are exposed.
