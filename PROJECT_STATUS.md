# ConvX - Simplification Refactor Status

Current Stage: 8 - Simplify Frontend

Stage Status: completed

Last Completed Stage: 8

Next Stage: 9 - Full Integration Testing (explicit authorization required)

Last Updated: 2026-11-06 (Asia/Dhaka)

## Completed Work

Revised stages1-8 complete within documented supported cases. The application now has its requested focused single-document interface over the actual local conversion/ZIP pipeline. Start `.\.venv\Scripts\python dev.py` and use the printed URL; restart after updating app code. No token, separate backend, broker/database, paid license or external conversion service. See [interface guide](docs/simple-interface.md), [Stage8 recovery](docs/stage8-resume.md) and current checkpoint. Do not automatically start Stage9.

## Stage8 Implemented

Replaced dashboard/sidebar/table/filter/help-tab workflows with a responsive React JSX form using existing Tailwind/DaisyUI. Exact title/subtitle, drag/drop/file choose, one DOCX/PDF, filename/size/limit/clear, default-unchecked SEC EDGAR Compliance checkbox and specified descriptions. Actual selected mode reaches the existing runtime. Convert to HTM locks appropriately; real upload/engine progress, cancel, errors, source-basename ZIP filename and audited Download ZIP are present. Convert another document clears that temporary conversion and resets mode.

The single-job hook recovers current ID from tab storage, migrates newest dashboard ID, retries network interruption without losing the capability, and tolerates optional storage failures. Optional notes report font/LibreOffice/appearance/OCR limits. Collapsed preview preserves actual PDF/HTM/side/overlay/diff review, fixes missing capture DPI and clarifies labels. EDGAR success explicitly does not confirm SEC filing acceptance. Light/dark/system preference, theme persistence, keyboard/skip/focus/live messages/reduced motion are supported. No engine/gate/server/dependency change.

## Files Changed

New converter.jsx replacing removed workspace.jsx; simplified globals.css and single-job hook; page/layout metadata, mode header, progress/error-copy helpers and optional preview. Shared genuine PDF test helper and rewritten UI/updated Node tests. Updated AGENTS/README/interface/runtime/renderer/ZIP docs, decisions/test history/evidence/recovery and progress records. No Python, reference fixture, user .env/data or Git metadata change; no Git writes.

## Actual Verification

Production build passed. Final Node16passed,0failed,83.42seconds. Final production Next/Chromium browser11passed,0failed,3.1minutes: actual PDF/DOCX through both checkbox modes and ZIP saves; reference PDF23page download/canvas/capture; unsupported EDGAR failure without download; invalid/empty/oversize/multiple selection, clearing, active cancellation, reload/reset, real offline-network recovery, drag/drop, keyboard and mobile/desktop light/dark axe/screenshots. No mocked conversion/download. Initial UI10run6passed/4failed from unscoped Next route alerts, second11run9passed/2failed from expected Unicode script encoding and selecting before reset re-enabled the input; fixes and failures remain in test history.

Four390/1440light/dark captures retained with SHA in [evidence](docs/stage8-interface-regression.json), visually inspected desktop light/mobile dark. Light-theme DaisyUI token override corrected. Scope is Stage8 UI verification, not Stage9 broader qualification. No full Python rerun: no Python code changed; prior Stage7 full431passed remains historical backend evidence, while current browser tests execute the actual engine.

## Known Limits and Next Steps

All supplied complex conversion fixtures still fail EDGAR_CLIPPING_UNSUPPORTED page1; their Standard output remains supported. Local EDGAR interpretation is not SEC acceptance; font/pixel, unsupported geometry/mixed EDGAR print, OCR/platform and single Node limits remain. Optional preview is an aid, not exact equivalence proof. Stage9 broader integration and Stage10 cleanup/optimization remain. Current status/checkpoint/decisions/test history are synchronized; all test sessions finished. Review/commit/push manually and explicitly authorize Stage9. No Git write operations by agents.

Suggested Commit Message: refactor: simplify converter UI with optional EDGAR mode
