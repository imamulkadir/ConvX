# Stage8 final recovery - 2026-11-06

Stage8 COMPLETED. Stages1-8 complete, next9 Full Integration Testing, awaiting explicit user authorization. All named test sessions finished; no QA server/session remains to collect. No Git writes/subagents. Read AGENTS.md, PROJECT_STATUS.md, .agent-checkpoint.json, latest decisions/test history and this note. Never automatically advance or repeat completed audits.

## Implementation

New components/converter.jsx replaces removed875-line workspace dashboard. Single DOCX/PDF drop/choose/file-size/type/empty/multiple validation and clear selection, exact requested title/subtitle, default-off SEC EDGAR Compliance checkbox/descriptions, Convert to HTM, actual upload/engine messages, cancel, clear failures, output ZIP filename/download and Convert another document. Selected mode is sent through existing real upload header, persisted/recovered and verified end-to-end for both file types/modes.

Existing hook now tracks one current job/report, migrates newest legacy dashboard ID, stores convx-current-job (no document contents), tolerates optional browser storage, retries status/network interruptions without losing current capability, and deletes only the current temporary conversion on explicit reset. Form locks during active/retained conversion; new-document reset clears mode. No token/API setup. No Python/runtime/gate/dependency changes.

Dashboard/sidebar/table/filter/help tabs/CSS removed. Existing Tailwind/DaisyUI responsive light/dark themes, system preference, persistent toggle, skip link/focus/native checkbox, live statuses/errors, reduced motion. DaisyUI light default overrode green until explicit root theme variables restored. Optional conversion notes explain local fonts/LibreOffice/pixel/OCR limits; EDGAR success explicitly does not confirm SEC acceptance.

Optional collapsed Preview and compare retains real PDF canvas/HTM PNG/side/overlay/diff, page/zoom controls. Fixed capture DPI previously passed to PdfPage instead of Capture, clarified labels/alt/missing-preview copy. Active uploaded/generated HTML is not served. Existing source-bound browser and secure ZIP pipeline remains unchanged.

## Actual verification

Production build passed. Final Node16passed0failed83.42sec (actual runtime/ZIP/security/retry/Windows lock plus progress-copy helper). Final production Next/Chromium11passed0failed3.1min: validation/clear/keyboard, both modes via form for actual PDF and native DOCX with real ZIP saves/internal mode-correct names, reload/reset, supplied23-page Standard PDF/download/canvas/capture, honest EDGAR clipping failure/no ZIP, actual invalid source/cancel, drag/drop/multiple selection, real network-offline interruption and recovery,390/1440 light/dark axe/screenshots. No mock conversion/download. No full Python rerun: Python unchanged; prior Stage7 full431pass stays historical, while current browser tests execute real Python.

Initial UI10run6passed4failed3.1min from unscoped getByRole(alert) matching Next route announcer. Second UI11run9passed2failed3.4min from expected em-dash converted to question mark by Windows script encoding and test setting file before reset enabled input. Fixed scoped selectors, Unicode via UTF8 patch and waiting for enabled input; failures retained in history. Initial light theme override and missing preview DPI fixed; final green desktop/mobile screenshots inspected. Final capture paths/SHA in docs/stage8-interface-regression.json, private copies var/refactor-stage8/final. First captures retained var/refactor-stage8/first-pass.

Final fixture/context8of8passed0.110sec; archived history hashes/active links/checkpoint verified; Prettier/pip/read-only whitespace checks passed, only LF/CRLF notices. Sources/user.env/Git metadata preserved. All named test sessions completed and QA-owned servers stopped automatically.

## Known limits and next stage

All supplied complex DOCX/PDF fixtures still fail EDGAR_CLIPPING_UNSUPPORTED page1, no successful EDGAR package for them. Standard remains available. Local EDGAR interpretation is not SEC acceptance or legacy strict proof; font/pixel/unsupported geometry/mixed print/OCR/platform/single Node limits unchanged. No universal exact-fidelity claim. Optional previews aid review only.

Stage9 requires fresh explicit authorization: broaden integration/regression through the now-completed interface, actual archives and supplied/independent sources, and fix discovered defects without inventing EDGAR success. Stage10 cleanup/optimization follows its own gate. Current four-flow UI smoke does not mark Stage9 done. Suggested commit refactor: simplify converter UI with optional EDGAR mode. User reviews/commits/pushes manually; no agent Git writes.

## Run and environment

Restart `.\.venv\Scripts\python dev.py` after updates and use printed URL. Choose/drop file, optional EDGAR checkbox, Convert to HTM, Download ZIP. Existing .venv, Node22.19+ and free LO .tools/libreoffice/program/soffice.com; no separate API/account/token. Clean Python var/refactor-stage2/clean-env/Scripts/python.exe used by browser tests. Web npm commands in apps/web; CONVX_TEST_PYTHON can select clean interpreter. Free Chromium installed once with python -m playwright install chromium. Read-only Git C:/Program Files/Git/cmd/git.exe.
