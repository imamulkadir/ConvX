# EDGAR Converter - Project Status

## Overall Status

Current Stage: 7 - Pixel-Level Visual Validation

Stage Status: completed

Last Completed Stage: 7

Next Stage: 8 - ZIP Packaging (requires explicit authorization)

Last Updated: 2026-11-05 (Asia/Dhaka)

## Project Objective

Build secure DOCX upload, revision acceptance, accepted-DOCX PDF rendering, PDF-first searchable EDGAR HTM reconstruction, explicit compliance/fidelity gates and a clean filing ZIP. Compliance and disclosure integrity take priority; unresolved strict failures prevent publication. All components must be free of charge with no premium/trial licenses or paid services.

## Completed Stages

1. Requirements Analysis and Architecture: immutable fixture inventory, manual-derived design registry, service/module contracts and persistent recovery records.
2. Backend Foundation: authenticated FastAPI, secure multipart/OOXML admission, private storage, durable SQLAlchemy jobs/events/outbox, Redis/Celery transport, cancellation/retention/lease/heartbeat lifecycle and tests.
3. DOCX Processing: supported deterministic revision acceptance, source/media preservation, actual free LibreOffice native export and all-page strict PDF validation. The Word fixture remains an unsuccessful conversion: all 23 pages fail its reference gate.
4. PDF Layout Analysis: schema-v1 layout, exact character ledger, typography/fonts/images/vectors, table/reading/region candidates, proof-bound production extraction and explicitly ineligible inspection. Final tests: 144 passed, 2 optional services skipped, 89% coverage.

5. PDF-to-HTM Reconstruction: private searchable candidate generation, physical tables/merges and explicit unsupported-layout/asset requests. Historical final result: 179 passed, 2 skipped, 90% coverage.
6. SEC Compliance Engine: executable source-first local rules, decoded assets/context limits and fail-closed diagnostics. Historical final tests: 261 passed, 2 skipped, 90% parent coverage.
7. Pixel-Level Visual Validation: isolated pinned Chromium print/screen rendering, content/geometry/resource/pixel checks, private artifacts and strict/nonqualifying gates. User explicitly authorized with "continue"; implementation is completed. A further continue during work retained Stage 7 and did not authorize Stage 8. Stop for manual user review/commit/push.

## Current Stage and Implemented Features

Stage 7 adds `converter.visual_validation`: pinned sandboxed Chromium with document JavaScript disabled, CSP and captured manifest-only resource routing; isolated child deadline/RSS/output/artifact controls; print PDF and mapped page screen captures at controlled DPI; exact disclosure, fonts, origins/bounds, images/vectors/paint and pixel comparisons.

Production comparison revalidates actual strict SEC/file evidence and binds the complete passing PDF proof. Explicit inspection remains nonqualifying even when measurements match, and its model rejects strict promotion. Missing/unsafe/stale/failed evidence never launches production comparison. No source file is modified or rasterized as disclosure.

Raw pixel differences and neutral text-edge candidates are separate. Print edge explanations require independent matching layout/content/paint/font bytes and no images. Screen candidates are never suppressed without separate proof. Per-page evidence includes source/print/screen PNGs, heatmaps/overlays, bounded geometry records and private JSON. Missing pages/resources, overflow, changed inputs/fonts and truncated evidence fail. No eligible evidence-backed source correction was found; no unapproved formatting edit was applied.

A future strict visual success stops at awaiting_packaging/PACKAGING_ENGINE_NOT_AVAILABLE. Current Word-reference PDF and generated inline-style SEC failures still stop earlier. The web UI, ZIP packaging and final downloads remain unimplemented. Browser process/network isolation is application-level plus Chromium sandbox; deployment OS qualification remains outstanding.

## Reference Qualification and Evidence

The user confirmed the fixture PDF came from opening the accepted DOCX in Word and saving/exporting it as PDF. Free LibreOffice likewise opens accepted DOCX and natively exports PDF, but the rendering engines are not equivalent.

Revision acceptance removes all 31 revision markers, retains ordered content/table structure across 18 story parts and preserves all five original media parts. Four unique image bytes agree with the accepted baseline. Full DOCX format equivalence is unproven: same-renderer PDF comparison agrees on 22 pages, with page 1 differing by a 9 pt horizontal offset for 66 words and floating-table/style serialization differences.

Generated LibreOffice PDF has 23 pages but fails the strict Word-reference comparison on every page. It produces neither layout nor HTM through the normal pipeline. No source typography edits, reference substitution or relaxed fidelity gate was used. See [qualification](docs/stage3-regression.md).

Read-only reference inspection retained 85,798 characters, 1,263 lines, 13 font resources, four image assets in five placements, 4,847 vector paths and eight ruled-table candidates. It remains reconstruction-ineligible. See [extraction evidence](docs/stage4-extraction-regression.json).

Stage 5 positive/negative tests use genuine PDFs; synthetic PDF self-comparison isolates generator mechanics and is not Word/DOCX qualification. The actual one-page LibreOffice pipeline reaches HTM, normalizes assets and correctly fails unresolved CSS permissions in Stage 6. Redacted candidate examples are in [reconstruction evidence](docs/stage5-reconstruction-regression.json); full private artifacts stay ignored under var/. Stage 7 also checks all 23 reference pages against a deliberately empty 23-page document solely for negative inspection coverage: all 85,798 characters are accounted for and all pages report missing disclosure. This is not a prospectus conversion result.

## Files Created or Modified

Added visual-validation policy/results, isolated browser/control worker, geometry/pixel comparison and inspection CLI; genuine browser/unit/all-page regression tests; pinned Playwright/NumPy/transitive dependencies and browser setup; visual regression metrics/docs. Updated pipeline/worker/job/API/configuration, transient native-file size-monitor handling, converter 0.7.0 packaging, environment examples and all persistent records. No original fixtures or Git state changed.

## Tests Executed

Windows/PowerShell, Python 3.12.10, actual LibreOffice and Playwright 1.64.1 / Chromium 156.0.8078.4 revision 1248. Recovery: 115 tests passed. Intermediate focused visual/all-page suite: 23 passed. Strengthened valid-PDF SEC/stale-gate and inspection-promotion checks: 4 passed. Final full suite: **286 passed, 0 failed, 2 skipped**, 87% parent-reported coverage, one existing warning, 261.06 seconds. Browser/renderer child and manual command coverage is not collected by parent coverage.

Pinned dependencies and Chromium installation succeeded. Editable 0.7.0 install and wheel build passed; wheel source bytes matched and isolated wheel parent/child comparison ran actual Chromium. Ruff passed; 92 Python files formatted; pip check clean. Completed-record fixture/context checks passed 8/8; documentation links/evidence JSON and read-only diff checks passed. Two optional skips remain real Redis/PostgreSQL with no configured services.

Actual smoke comparison: identical print PDF/content/geometry and zero print pixel changes, but 1,169 unresolved screen pixels; strict visual failure was retained. Production source/SEC gate failure tests never reached Chromium. Current native one-page DOCX test correctly stops at SEC permission uncertainty; Word-reference conversion stops at its 23 failed PDF pages. All-page visual negative inspection passed its assertions without claiming conversion success. No SEC test submission, final ZIP/full filing E2E, web UI or Linux production qualification occurred. See [test history](docs/test-history.md) and [visual metrics](docs/stage7-visual-regression.json).

## Known Bugs and Technical Limitations

Word-reference PDF fidelity still fails all 23 pages. Unsupported revisions fail safely. Table/paragraph/reading order/font-resource associations retain explicit inference. Stage 5 intentionally rejects unsupported overlap/rotation/vector painting and unresolved table semantics. Chromium comparison now measures font/content/geometry and raw pixels, but unresolved screen differences and prior gates prevent faithful-output qualification; no pixel-perfect claim is made.

An executable confirmed-subset profile is implemented, but STYLE property/value permissions, MANY scope and further character mappings remain unresolved. Candidate vocabulary is documented separately without changing the historical design registry. Graphics are normalized and actual files are validated; no source text is rasterized. Link output is a conservative subset, not a claim that every other manual construct is illegal. Candidate success does not imply compliance or strict fidelity.

Live Redis/PostgreSQL, Linux prefork, global CPU/disk/network/ACL enforcement and native-parser sandboxing remain unverified deployment responsibilities. Persistent schema v1 is unchanged; no migration framework was added. Browser reference attachment, frontend, final package and downloads remain future stages.

## Architectural Decisions

Independent API/worker/frontend and PDF-first gates remain. Free-only native export and conservative revision acceptance are ADR-011 through ADR-014; layout/inspection gates are ADR-015 and ADR-016; normal-flow candidate reconstruction and integrity controls are ADR-017 through ADR-019; fail-closed local rules and asset choices are ADR-020 through ADR-022; visual gate/inspection isolation, browser profiles and conservative raster/correction decisions are ADR-023 through ADR-025 in [decisions](docs/decisions.md).

## Pending Tasks and Next Actions

Stage 7 implementation and relevant verification are complete. Stop for user review/manual commit/push and explicit Stage 8 authorization. Stage 8 must implement deterministic clean ZIP packaging only from current passing evidence; it must not bypass PDF/SEC/visual failures. Resolve earlier reference/permission and screen discrepancies before claiming filing-ready output. Stage 9 UI remains separate; no automatic later-stage work is authorized.

## Suggested Commit Message

`feat: add isolated Chromium visual regression and strict fidelity gates`

## Resume Instructions

Read AGENTS, status, checkpoint, decisions, test history and [visual validation](docs/visual-validation.md). Inspect actual files/read-only Git, verify relevant tests and immutable fixture hashes. Resume only the authorized stage. Never initialize/stage/commit/push or otherwise modify Git state. Do not treat candidate generation or a negative regression test passing as successful Word-reference conversion or SEC-ready output.
