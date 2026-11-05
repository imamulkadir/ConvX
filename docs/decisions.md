# Development decision log

## 2026-11-05 — ADR-001: PDF-first independent services

Decision: separate JSX Next.js, FastAPI, Celery and converter modules; generated accepted-DOCX PDF is the layout authority. Context: confidentiality and long-running conversions. Alternatives: Next.js conversion routes or generic DOCX-to-HTML. Reasoning: mandatory workflow and isolation. Consequences: independent deployment, persistent state, versioned layout and explicit gates. See architecture/interfaces.

## 2026-11-05 — ADR-002: Provider qualification

Superseded by ADR-011: the user requires free components only. No Aspose/premium provider was implemented or installed.

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

## 2026-11-05 — ADR-011: Free-only revision and rendering implementation

Decision: the user's explicit Stage 3 instruction excludes all premium licensing and paid providers. Implement deterministic OOXML revision acceptance and local free LibreOffice export; remove Aspose from the current architecture. Context: no commercial license is available, and trial/evaluation output cannot represent a production conversion. Alternatives: paid SDK/trial, unsupported unattended Office COM, or native LibreOffice resaving all input OOXML. Reasoning: source property/asset preservation, reproducibility and no paid dependencies. Consequences: unsupported cell/custom-XML/conflict and ambiguous structural revisions fail safely. LibreOffice is implemented, but failed the Word reference qualification; no claim of equivalent Word layout. Module/provider interfaces remain extensible only within the free-only scope.

## 2026-11-05 — ADR-012: Strict PDF gate and reference evidence

Decision: validate all intermediate PDF pages with explicit content/order, geometry, font signatures and exact RGB differences before permitting later work. Context: the reference has 23 pages, and identical page count conceals material layout differences. Alternatives: first-page checks, permissive pixel thresholds or using the supplied PDF as generated output. Reasoning: each would conceal failures. Consequences: the actual LibreOffice export has 23 pages but fails every page against Word; a real one-page same-renderer baseline passes. Default strict mode requires a reference; production cannot disable it. No HTM generation is included in Stage 3. Retain raw private evidence and a redacted repository qualification summary.

## 2026-11-05 — ADR-013: Revision/PDF worker lifecycle without schema mutation

Decision: use the persisted current attempt UUID to own private accepted DOCX, PDF/evidence and atomic report; extend existing lease/version-guarded job transitions and provide explicit owned resume. Context: cancellation/expiry must invalidate rendering, and Stage 2 blocked jobs must not silently run new code. Alternatives: global filesystem outputs, unbound diagnostics or automatic replay of all blocked jobs. Reasoning: attempt isolation preserves provenance and prevents stale publication. Consequences: schema v1 remains compatible; current reports are exposed only through owned validation, not raw file downloads. A complete reference-upload UI remains later integration work; individual CLI references and authorized private reference provisioning work now.

## 2026-11-05 — ADR-014: Controlled native resource profile

Decision: set the explicit configurable renderer RSS limit to 1 GiB after the full fixture exceeded the initial 512 MiB limit and stopped safely. Context: a genuine native export was needed to qualify the free renderer. Alternatives: remove resource limits or label the interrupted output valid. Reasoning: maintain a bounded, documented profile while allowing real completion of the test. Consequences: output completed under 1 GiB and still failed strict fidelity; no source font/geometry changes or relaxed fidelity thresholds were used. OS-level network/CPU/disk/native-parser isolation remains Stage 11 work.

## 2026-11-05 ? ADR-015: Immutable typed PDF layout with explicit inference

Decision: use Pydantic schema v1 with exact native character ledgers, font resources, image placements, vectors/paint operations and separate reading/table/region candidates. Context: PDF geometry is observable while paragraph semantics, reading order and font-resource identity may be ambiguous. Alternatives: generic PDF-to-HTML output, forced source order or silently selecting fonts. Reasoning: preserve facts and uncertainty without losing disclosure. Consequences: deterministic IDs, finite geometry/reference validation and bounded private JSON; later HTM must resolve unsupported geometry and semantics. Native parser calls still require deployment isolation.

## 2026-11-05 ? ADR-016: Hash-bound layout gate and separate reference inspection

Decision: production analysis requires a complete passing strict Stage 3 report bound to the actual PDF hash; read-only inspection cannot authorize reconstruction. Context: the Word-saved fixture is useful for extraction regression although the free generated PDF fails strict comparison. Alternatives: bypass the failed gate or substitute the reference as generated output. Reasoning: inspection evidence must not be confused with conversion success. Consequences: no layout in the failed reference pipeline; successful layout stops before HTM. Record original/accepted DOCX hashes and native export provider provenance. Word Save As and LibreOffice export are both native operations but engine equivalence remains unproven; the free-only constraint remains unchanged.

## 2026-11-05 - ADR-017: Normal-flow HTM with explicit unsupported cases

Decision: reconstruct searchable character advances, whitespace-partitioned flow rows/columns, physical tables/merges and supported rules using manual-listed elements. Context: absolute positioning and arbitrary modern markup are not an approved EDGAR profile, while nested tables are expressly prohibited. Alternatives: full-page rasters, generic PDF-to-HTML, or pretending unsupported rotation/overlap is faithful. Reasoning: preserve disclosure and fail visibly when no implemented allowed geometry strategy exists. Consequences: no SPAN/TBODY/DOCTYPE, nested tables, absolute positions or disclosure rasterization; complex painting and uncertain tables fail; candidate CSS remains provisional until Stage 6.

## 2026-11-05 - ADR-018: Candidate generation is separate from downstream gates

Decision: every Stage 5 result keeps compliance, visual fidelity and strict validation false; private candidates cannot enable preview/download or final completion. Context: the manual lists STYLE for MANY but property/value scope remains unresolved, and font metrics have not been measured in Chromium. Alternatives: assume browser-renderable means SEC-compatible or claim pixel accuracy from coordinate extraction. Reasoning: each requires evidence from later dedicated gates. Consequences: versioned proposed generator profile, numeric Unicode references pending mapping review, source-bound graphic requests with no fabricated asset bytes, owned report diagnostics and awaiting_sec_validation lifecycle. Stage 6 resolves rules/assets; Stage 7 measures fidelity. The Word-reference strict PDF failure is unchanged.

## 2026-11-05 - ADR-019: Reconstruction integrity and bounded publication

Decision: validate all character identities/text exactly once, compare reparsed BODY text and proposed non-table reading order, and exclusively publish a new private candidate using an atomic hard link. Context: tables split native lines, links can cross cells and concurrent attempts must not overwrite artifacts. Alternatives: text normalization, ID-free multiset checks or replacing an existing destination. Reasoning: retain precise source accounting and fail stale/corrupt output safely. Consequences: inferred table structure and source fonts remain explicit uncertainty; association/partition/node/byte/RSS bounds and cancellation apply. Full OS sandboxing remains deployment work.

## 2026-11-05 - ADR-020: Versioned local validation with fail-closed uncertainty

Decision: ship executable v78.2 package data with manual hash, diagnostic bases and file/registry hashes while preserving v78.1 design evidence. Context: the actual manual's MANY/CSS table does not supply complete per-tag/property/value permissions, and legacy character rows conflict. Alternatives: approve arbitrary modern CSS or falsely prohibit every historical construct. Reasoning: evaluate confirmed rules, label product constraints separately and fail unresolved applicable permissions. Consequences: confirmed-subset documents can pass local checks; generated styled candidates currently fail explicitly; whole encoded submission/form context is separately required for strict local limits. Local validation never proves SEC acceptance.

## 2026-11-05 - ADR-021: Source-first checks and independent asset decoding

Decision: scan actual source tags before parser repair, then validate attributes, links/bookmarks, bounded encoding and decoded graphic manifests, with end-of-check content hashes. Context: browser/lxml repair can conceal source TBODY/duplicate/nested/ambiguous constructs, and filenames do not establish image format. Alternatives: model-only validation, naive URL prefix checks or extension-only asset checks. Reasoning: inspect what will actually be submitted without fetching any link. Consequences: no mutation or automatic repair by the validator; unresolved references, stale files and budgets fail; diagnostics exclude disclosure text. Supported PAGE/R exceptions are explicitly recognized rather than blindly applying the main tag table.

## 2026-11-05 - ADR-022: Stage 6 normalization and shared formatting runs

Decision: materialize only source-bound graphics into a new private filing directory, preserve original JPEGs, use verified exact GIF for small palettes, and record all other pixel changes. Context: Stage 5 emitted graphic requests only; SEC supplementary guidance disallows independent word formatting. Alternatives: fabricate image bytes, rasterize disclosure or preserve the per-character wrapper pattern. Reasoning: normalize real image xrefs/masks, update only IMG src attributes, preserve disclosure and coalesce equivalent typography. Consequences: generator version becomes v2; intra-run browser shaping and white-canvas alpha/compositing remain unverified until Stage 7. Styled candidates still fail permission gaps; no output is published.
