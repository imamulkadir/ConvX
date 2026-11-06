# Stage 6 final handoff - 2026-11-06

Stage 6 is COMPLETED within documented supported cases. Stages1-6 complete, next7 ZIP Packaging; awaiting explicit user authorization. No test sessions remain running. No Git writes/subagents. Read AGENTS.md, PROJECT_STATUS.md, .agent-checkpoint.json, latest decisions/test history and this note on recovery. Never repeat the audit or advance automatically.

## Implementation

New packages/converter/edgar_html.py consumes and independently verifies the authoritative shared PDF model, reuses normal-flow Builder/typography/merged-table/graphic primitives, emits selectable .htm, deterministic <=32-character SEC-compatible names and local JPG/GIF. Native JPEG is preserved where possible; palette graphics use verified GIF and other graphics high-quality JPEG, with alpha/loss recorded. Standard HTML5 remains independent/default.

New sec_validation/flow_profile.py is an opt-in CSS2/HTML4 interpretation of EFM78 STYLE permission. Both manual and W3C supporting sources were actually read; exact pages, hashes, scopes and interpretation limits are in docs/edgar-renderer.md. Results include profile identity and a separate implementation/grammar/entity digest. Default legacy strict validator retains all uncertainty/errors. New-profile strict_passed and SEC acceptance are always false. No legacy Word-reference proof is synthesized or approved.

The existing standard_visual.py worker is now shared by both strategies with mode-specific selectors and actual DOM/text/page/asset/print checks. EDGAR word missing/origin errors above6points fail; raw pixels remain unsmoothed/unaligned. Private print uses source-derived inches (pt is unsupported by Playwright) and uniform dimensions. Actual PNG/overlay/diff captures and hashes bind previews. No screenshot replacement for ordinary text, scripts or external resources.

Input/runtime support exact standard/edgar modes, Standard default. Same-origin internal upload x-convx-mode saves mode to private request/meta and retains it through eligible retries. Missing-browser failures can resume after free Chromium is installed; packaging-pending cannot resume or download. Safe PNG preview rechecks source, HTML/assets and capture hashes for either mode. Final user checkbox/minimal UI remains Stage8. Current transitional UI shows Local EDGAR profile, distinguishing it from strict SEC validation.

Final review fixed a potential disclosure rewrite: CSS-property removal now edits parsed style attributes only, checks exact body text, and preserves literal CSS-looking financial/technical text. Unsupported local-validation errors retain file/element information. Clipping exception is only one rectangle within0.05pt of page bounds with all source glyphs inside; actual LO page rounding was0.028pt. More complex clipping is rejected.

## Actual tests

- Full active pytest:380passed,0failed,548.20sec. Collection preceded final CSS-looking-text regression and two extra negative cases; do not claim383full tests.
- Final renderer/SEC/actual Standard browser focused:111passed,19.30sec, includes the new disclosure regression.
- Focused renderer/SEC/independent EDGAR native/image/table after serialization fix:103passed,9reference-named cases deselected,37.17sec. Scopes overlap; not unique additional totals.
- Actual major displacement and mixed-print failure tests:2passed,8deselected,6.51sec.
- Final Node:13passed,62.35sec. Actual absent test-local browser cache produces EDGAR_BROWSER_UNAVAILABLE; restoring test env and retry succeeds with mode retained. Tampered HTM preview rejected; ZIP stays unavailable.
- Production Next/Chromium UI:6passed,2.8min. Real EDGAR DOCX27.5sec; Standard DOCX52.9sec; supplied PDF48.3sec; recovery/deletion/invalid input/light/dark/keyboard/axe. No mocked converter or separate API. Later small serializer/label/error edits have focused browser/Python and format coverage.
- Final fixture/context8/8passed,0.374sec; source fixtures and historical archive SHA unchanged; active links/JSON/profile/approval checks, Ruff, clean pip check, web Prettier and read-only diff checks passed. Only LF/CRLF notices.

Earlier syntax, print-unit, LO clip-rounding and invalid-test-retry failures and their corrections remain in docs/test-history.md. No evidence was erased/promoted. All QA-owned servers stopped automatically; do not stop unrelated user processes.

## Evidence and limitations

Actual production small independent EDGAR DOCX:1page,15characters,0assets,613-byteHTM, local-profile passed, strictfalse, zero missing printed words, max origin1.6688843pt. Screen MAE0.0623143/255, print0.0575261/255, exactpixelsfalse. docs/stage6-edgar-regression.json points to private actual evidence. Merged-table source/actual screenshot inspected, slight typography/border differences visible.

**All three supplied conversion fixtures fail EDGAR_CLIPPING_UNSUPPORTED page1 after genuine preparation.** They are unchanged; no successful EDGAR conversion for those fixtures is claimed. Standard still works. Other unsupported cases: clipping, rotations/vertical text, annotations, overlapping/interlocking paint, uncertain grids/vectors/links, mixed print dimensions. Local font/pixel differences and user browser paper settings remain limits. No OCR, broad platform/fidelity or SEC acceptance claim.

## Next stage when explicitly authorized

Stage7 must package exactly one mode-correct .html/.htm and exactly referenced local root assets, source-basename ZIP, source-derived/SEC-compatible internal document names, no reports/PDF/DOCX/captures/nested folders. Validate actual archives and securely serve only qualified current output. Keep the revised local-profile pipeline separate from historical strict Word-reference/SEC audit gates rather than weakening their proof. Final checkbox/minimal page Stage8; full four-path ZIP integration Stage9; cleanup Stage10. Stop after each stage and update records.

Suggested commit: refactor: add manual-constrained EDGAR flow rendering. User reviews/commits/pushes manually. Await Stage7 authorization.

## Environment

PowerShell D:/Tools/ConvX. Clean Python var/refactor-stage2/clean-env/Scripts/python.exe; root .venv also usable. Free LO .tools/libreoffice/program/soffice.com. Start .\.venv\Scripts\python dev.py. Fresh browser setup once: python -m playwright install chromium. Web npm commands run from apps/web; CONVX_TEST_PYTHON can select clean interpreter for UI. Read-only Git executable C:/Program Files/Git/cmd/git.exe. No Git write command or additional service.
