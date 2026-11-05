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
