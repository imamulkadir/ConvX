# EDGAR Converter - Project Status

## Overall Status

Current Stage: 6 - SEC Compliance Engine

Stage Status: completed

Last Completed Stage: 6

Next Stage: 7 - Pixel-Level Visual Validation (requires explicit authorization)

Last Updated: 2026-11-05 (Asia/Dhaka)

## Project Objective

Build secure DOCX upload, revision acceptance, accepted-DOCX PDF rendering, PDF-first searchable EDGAR HTM reconstruction, explicit compliance/fidelity gates and a clean filing ZIP. Compliance and disclosure integrity take priority; unresolved strict failures prevent publication. All components must be free of charge with no premium/trial licenses or paid services.

## Completed Stages

1. Requirements Analysis and Architecture: immutable fixture inventory, manual-derived design registry, service/module contracts and persistent recovery records.
2. Backend Foundation: authenticated FastAPI, secure multipart/OOXML admission, private storage, durable SQLAlchemy jobs/events/outbox, Redis/Celery transport, cancellation/retention/lease/heartbeat lifecycle and tests.
3. DOCX Processing: supported deterministic revision acceptance, source/media preservation, actual free LibreOffice native export and all-page strict PDF validation. The Word fixture remains an unsuccessful conversion: all 23 pages fail its reference gate.
4. PDF Layout Analysis: schema-v1 layout, exact character ledger, typography/fonts/images/vectors, table/reading/region candidates, proof-bound production extraction and explicitly ineligible inspection. Final tests: 144 passed, 2 optional services skipped, 89% coverage.

5. PDF-to-HTM Reconstruction: private searchable candidate generation, physical tables/merges and explicit unsupported-layout/asset requests. Historical final result: 179 passed, 2 skipped, 90% coverage.
6. SEC Compliance Engine: executable source-first local rules, actual decoded assets, context-dependent limits and detailed fail-closed diagnostics. Stage 6 was explicitly authorized with "go for stage 6" and is now completed. Stop before Stage 7; all Git writes remain the user's responsibility.

## Current Stage and Implemented Features

Stage 6 adds `converter.sec_validation` with a packaged v78.2 local registry pinned to the supplied manual, source-first HTML scanning, tag/attribute/character/CSS checks, links/bookmarks, filenames and actual graphic decoding. Diagnostics distinguish confirmed manual rules, project policy, supplementary SEC guidance and unresolved permissions. Parser repair cannot hide raw forbidden/nested tags or duplicate attributes. PAGE/R manual exceptions are recognized explicitly.

STYLE/MANY permission scope remains unresolved and its actual use fails strict validation. Latin-1 and a narrow verified named-character repertoire pass; legacy C1 remapping and ambiguous Unicode fail without transliteration. Confirmed-subset actual files can pass local checks; strict local results also require actual form/whole MIME-encoded submission-size context. SEC acceptance and visual fidelity remain false. Combined submission component accounting remains unresolved from a total alone.

`converter.assets` materializes source-bound JPG/GIF assets in a new private filing/ directory, preserves original JPEG bytes where possible, verifies exact palette roundtrips and records all JPEG/alpha/compositing pixel differences. Only IMG src values change; disclosure remains exact. Xref/mask/source/candidate hashes, image dimensions and byte/pixel/count budgets are checked. Original candidates and fixtures remain unchanged.

Generator v2 coalesces equivalent formatting runs following supplementary SEC guidance, replacing per-character formatting wrappers. Intra-run shaping is pending Chromium measurement. Normalized filing metadata and detailed local results are exposed only through owned validation reports. Current styled candidates fail SEC_VALIDATION_FAILED on explicit permission uncertainty. A future passing local gate stops at awaiting_visual_validation; no completion, serving UI, ZIP or download is enabled.

## Reference Qualification and Evidence

The user confirmed the fixture PDF came from opening the accepted DOCX in Word and saving/exporting it as PDF. Free LibreOffice likewise opens accepted DOCX and natively exports PDF, but the rendering engines are not equivalent.

Revision acceptance removes all 31 revision markers, retains ordered content/table structure across 18 story parts and preserves all five original media parts. Four unique image bytes agree with the accepted baseline. Full DOCX format equivalence is unproven: same-renderer PDF comparison agrees on 22 pages, with page 1 differing by a 9 pt horizontal offset for 66 words and floating-table/style serialization differences.

Generated LibreOffice PDF has 23 pages but fails the strict Word-reference comparison on every page. It produces neither layout nor HTM through the normal pipeline. No source typography edits, reference substitution or relaxed fidelity gate was used. See [qualification](docs/stage3-regression.md).

Read-only reference inspection retained 85,798 characters, 1,263 lines, 13 font resources, four image assets in five placements, 4,847 vector paths and eight ruled-table candidates. It remains reconstruction-ineligible. See [extraction evidence](docs/stage4-extraction-regression.json).

Stage 5 positive/negative tests use genuine PDFs; synthetic PDF self-comparison isolates generator mechanics and is not Word/DOCX qualification. The actual one-page LibreOffice pipeline reaches HTM, normalizes assets and correctly fails unresolved CSS permissions in Stage 6. Redacted candidate examples are in [reconstruction evidence](docs/stage5-reconstruction-regression.json); full private artifacts stay ignored under var/.

## Files Created or Modified

Added packaged `sec_validation` rules/models/source scanner/validator/CLI, source-bound `assets` normalization, actual-source and image tests, runtime registry evidence and Stage 6 documentation. Updated shared-run generator v2, pipeline/CLI/worker/API stages and budget configuration, manual/profile research records, .env.example, package data/version 0.6.0, build-directory ignore and persistent context. No original reference files or Git state changed.

## Tests Executed

Windows/PowerShell, Python 3.12.10, pinned PyMuPDF 1.26.7, actual LibreOffice and free local dependencies. Recovery: 34 generator tests passed. Focused final source/asset/generator checks: 115 passed. First full Stage 6 suite: 256 passed, 2 skipped, 89% coverage. Final combined suite: **261 passed, 0 failed, 2 skipped**, 90% reported coverage, one existing Starlette/httpx warning, 155.62 seconds.

Ruff passed; 81 Python files formatted; pip check clean. Editable converter install and isolated wheel build passed; registry and final source/data were compared in the wheel, then imported from the wheel in isolated Python for real confirmed-subset validation. Documentation links, registry copies and read-only diff checks passed. Completed-record historical fixture/context checks passed 8/8.

The two skips are unconfigured real Redis/PostgreSQL services. No real-service pass was simulated. No Chromium visual qualification, SEC Doc Validation/test submission, full ZIP pipeline, UI or production Linux sandbox/prefork qualification was performed. Actual accepted-final Word-reference processing still fails all 23 pages at the PDF gate. Detailed actual commands/failures/fixes are in [test history](docs/test-history.md).

## Known Bugs and Technical Limitations

Word-reference PDF fidelity still fails all 23 pages. Unsupported revisions fail safely. Table/paragraph/reading order/font-resource associations retain explicit inference. Stage 5 intentionally rejects unsupported overlap/rotation/vector painting and unresolved table semantics. Font availability/baselines, wrapping, borders/page breaks still require Chromium measurement; no pixel-perfect claim is made.

An executable confirmed-subset profile is implemented, but STYLE property/value permissions, MANY scope and further character mappings remain unresolved. Candidate vocabulary is documented separately without changing the historical design registry. Graphics are normalized and actual files are validated; no source text is rasterized. Link output is a conservative subset, not a claim that every other manual construct is illegal. Candidate success does not imply compliance or strict fidelity.

Live Redis/PostgreSQL, Linux prefork, global CPU/disk/network/ACL enforcement and native-parser sandboxing remain unverified deployment responsibilities. Persistent schema v1 is unchanged; no migration framework was added. Browser reference attachment, frontend, final package and downloads remain future stages.

## Architectural Decisions

Independent API/worker/frontend and PDF-first gates remain. Free-only native export and conservative revision acceptance are ADR-011 through ADR-014; layout/inspection gates are ADR-015 and ADR-016; normal-flow candidate reconstruction and integrity controls are ADR-017 through ADR-019; fail-closed local rules, actual-file checks and shared-run/asset choices are ADR-020 through ADR-022 in [decisions](docs/decisions.md).

## Pending Tasks and Next Actions

Stage 6 implementation and relevant tests are complete. Stop for user review/manual commit/push and explicit Stage 7 authorization. Stage 7 implements controlled Chromium visual comparison; it must preserve the earlier PDF/SEC gates and label any diagnostic inspection separately. CSS/MANY/character evidence gaps still require resolution; no current styled candidate is SEC-ready. No automatic packaging/UI/deployment stage is authorized.

## Suggested Commit Message

`feat: add versioned SEC file validation and source-bound graphic normalization`

## Resume Instructions

Read AGENTS, status, checkpoint, decisions, test history and [SEC validation engine](docs/sec-validation-engine.md). Inspect actual files/read-only Git, verify relevant tests and immutable fixture hashes. Resume only the authorized stage. Never initialize/stage/commit/push or otherwise modify Git state. Do not treat candidate generation or a negative regression test passing as successful Word-reference conversion or SEC-ready output.
