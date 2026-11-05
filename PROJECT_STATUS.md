# EDGAR Converter - Project Status

## Overall Status

Current Stage: 5 - PDF-to-HTM Reconstruction

Stage Status: completed

Last Completed Stage: 5

Next Stage: 6 - SEC Compliance Engine (requires explicit authorization)

Last Updated: 2026-11-05 (Asia/Dhaka)

## Project Objective

Build secure DOCX upload, revision acceptance, accepted-DOCX PDF rendering, PDF-first searchable EDGAR HTM reconstruction, explicit compliance/fidelity gates and a clean filing ZIP. Compliance and disclosure integrity take priority; unresolved strict failures prevent publication. All components must be free of charge with no premium/trial licenses or paid services.

## Completed Stages

1. Requirements Analysis and Architecture: immutable fixture inventory, manual-derived design registry, service/module contracts and persistent recovery records.
2. Backend Foundation: authenticated FastAPI, secure multipart/OOXML admission, private storage, durable SQLAlchemy jobs/events/outbox, Redis/Celery transport, cancellation/retention/lease/heartbeat lifecycle and tests.
3. DOCX Processing: supported deterministic revision acceptance, source/media preservation, actual free LibreOffice native export and all-page strict PDF validation. The Word fixture remains an unsuccessful conversion: all 23 pages fail its reference gate.
4. PDF Layout Analysis: schema-v1 layout, exact character ledger, typography/fonts/images/vectors, table/reading/region candidates, proof-bound production extraction and explicitly ineligible inspection. Final tests: 144 passed, 2 optional services skipped, 89% coverage.

Stage 5 implementation is completed and verified; stop before Stage 6. Stage 5 was explicitly authorized by the user's "pushed, continue". Initial read-only Git state was clean. No Git write operation is authorized.

## Current Stage and Implemented Features

Stage 5 adds `converter.html_generator`: proposed manual-constrained normal-flow HTM reconstruction with whitespace-partitioned rows/columns, exact selectable text, source character advances, font size/color/emphasis/underline/script hints, measured spacing/page geometry, physical tables with merged cells and source borders, simple rules/rectangles, conservative links/bookmarks and deterministic graphic requests.

The generator requires an eligible revalidated model, unchanged PDF and the exact complete passing strict PDF proof. Inspection or stale/failed sources cannot generate HTM. Character identities/text must occur exactly once; reparsed BODY text must agree exactly. Non-table reading order must agree with the proposed layout graph. Unsupported rotations, overlapping/interlocking geometry, uncertain tables, complex painting and unsupported links produce explicit incompatibilities with no partial candidate.

Output is private `candidate.htm` plus metadata in the current owned processing report. JPG requests retain source xrefs/masks/placement IDs; actual asset normalization is pending. Successful generation stops at blocked/awaiting_sec_validation with SEC_ENGINE_NOT_AVAILABLE. Candidate compliance, visual fidelity and strict validation are always false until their later gates supply evidence. No final completion, frontend, preview serving, ZIP or download path is enabled.

Resource policy bounds characters, items, association/partition work, nodes, bytes and sampled RSS. Cancellation/deadlines apply; exclusive atomic publication preserves an existing/concurrently created output. Native-parser/DOM allocation limits are cooperative rather than complete OS isolation.

## Reference Qualification and Evidence

The user confirmed the fixture PDF came from opening the accepted DOCX in Word and saving/exporting it as PDF. Free LibreOffice likewise opens accepted DOCX and natively exports PDF, but the rendering engines are not equivalent.

Revision acceptance removes all 31 revision markers, retains ordered content/table structure across 18 story parts and preserves all five original media parts. Four unique image bytes agree with the accepted baseline. Full DOCX format equivalence is unproven: same-renderer PDF comparison agrees on 22 pages, with page 1 differing by a 9 pt horizontal offset for 66 words and floating-table/style serialization differences.

Generated LibreOffice PDF has 23 pages but fails the strict Word-reference comparison on every page. It produces neither layout nor HTM through the normal pipeline. No source typography edits, reference substitution or relaxed fidelity gate was used. See [qualification](docs/stage3-regression.md).

Read-only reference inspection retained 85,798 characters, 1,263 lines, 13 font resources, four image assets in five placements, 4,847 vector paths and eight ruled-table candidates. It remains reconstruction-ineligible. See [extraction evidence](docs/stage4-extraction-regression.json).

Stage 5 positive/negative tests use genuine PDFs; synthetic PDF self-comparison isolates generator mechanics and is not Word/DOCX qualification. The actual one-page LibreOffice pipeline now reaches HTM. Redacted candidate examples are in [reconstruction evidence](docs/stage5-reconstruction-regression.json); full private artifacts stay ignored under var/.

## Files Created or Modified

Added `packages/converter/html_generator` (typed policy/results, flow partitioning, typography, table/border rendering and gated generation), `tests/unit/test_html_generator.py`, candidate profile documentation and redacted regression metrics. Updated pipeline/CLI/version, worker configuration, job stage/resume lifecycle, native pipeline integration tests, .env.example, architecture/interfaces/pipeline/limitations/SEC documentation and all persistent progress records. No original fixtures changed.

## Tests Executed

Environment: Windows PowerShell, Python 3.12.10, pinned PyMuPDF 1.26.7, actual local LibreOffice, editable API/converter packages. Converter 0.5.0 editable installation succeeded; no new premium or external rendering dependency.

Stage 4 recovery checks: 31 layout unit tests passed. Stage 5 focused generator suite: 34 passed, including text/Unicode, table/merge/order, font/script/link/graphic metadata, failed/stale gate rejection, unsupported features, limits, cancellation and publication races. Native one-page positive current pipeline passed. First full Stage 5 suite: 173 passed, 2 skipped, 89% line coverage, one existing warning, 135.20 seconds. Final expanded combined suite: **179 passed, 0 failed, 2 skipped**, 90% line coverage, one existing warning, 132.01 seconds. Ruff lint passed; 71 Python files formatted; pip check clean; documentation links/JSON and read-only diff checks passed.

Two optional skips are unconfigured real Redis/PostgreSQL services; neither is simulated as a service pass. Existing Starlette/httpx deprecation warning remains. Chromium visual validation, real SEC Doc Validation/test submissions, Linux production prefork and OS sandbox qualification have not been executed. See append-only [test history](docs/test-history.md).

## Known Bugs and Technical Limitations

Word-reference PDF fidelity still fails all 23 pages. Unsupported revisions fail safely. Table/paragraph/reading order/font-resource associations retain explicit inference. Stage 5 intentionally rejects unsupported overlap/rotation/vector painting and unresolved table semantics. Font availability/baselines, wrapping, borders/page breaks still require Chromium measurement; no pixel-perfect claim is made.

STYLE property/value permissions, MANY scope and character mappings are not an approved SEC profile. Candidate vocabulary is documented separately without changing the historical design registry. Assets are requests until normalization/actual-file checks; no source text is rasterized. Link output is a conservative subset, not a claim that every other manual construct is illegal. Candidate success does not imply compliance or strict fidelity.

Live Redis/PostgreSQL, Linux prefork, global CPU/disk/network/ACL enforcement and native-parser sandboxing remain unverified deployment responsibilities. Persistent schema v1 is unchanged; no migration framework was added. Browser reference attachment, frontend, final package and downloads remain future stages.

## Architectural Decisions

Independent API/worker/frontend and PDF-first gates remain. Free-only native export and conservative revision acceptance are ADR-011 through ADR-014; layout/inspection gates are ADR-015 and ADR-016; normal-flow candidate reconstruction, pending downstream gates and integrity/publication controls are ADR-017 through ADR-019 in [decisions](docs/decisions.md).

## Pending Tasks and Next Actions

Stage 5 implementation and final verification are complete. Stop for user review/manual commit/push. Stage 6 requires explicit authorization and must implement the versioned manual-derived actual-file SEC validator, resolve required CSS/MANY/character uncertainties and materialize/validate requested graphics before declaring any package eligible. Stage 7 must measure browser-vs-PDF fidelity. The unsuccessful Word reference may not bypass its PDF gate. No automatic next-stage work is authorized.

## Suggested Commit Message

`feat: add gated searchable HTM reconstruction and conversion tests`

## Resume Instructions

Read AGENTS, status, checkpoint, decisions, test history and [HTM reconstruction](docs/htm-reconstruction.md). Inspect actual files/read-only Git, verify relevant tests and immutable fixture hashes. Resume only the authorized stage. Never initialize/stage/commit/push or otherwise modify Git state. Do not treat candidate generation or a negative regression test passing as successful Word-reference conversion or SEC-ready output.
