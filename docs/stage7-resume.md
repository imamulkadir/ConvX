# Stage 7 final recovery - 2026-11-06

Stage7 COMPLETED. Stages1-7 complete, next8 Simplify Frontend, awaiting explicit user authorization. All named test sessions finished; no QA server/session remains to collect. No Git writes/subagents. Read AGENTS.md, PROJECT_STATUS.md, .agent-checkpoint.json, decisions/latest test history and this note; do not repeat completed work or advance automatically.

## Actual implementation

New packaging/current.py defines typed source-verified-mode-zip-v1 packaging, separate from unchanged historical strict Word/SEC gates. Standard has source-basename .html and exact local assets, EDGAR has deterministic SEC-compatible .htm plus JPG/GIF, external ZIP keeps original basename with UTF8/spaces/apostrophes. Only archive entry name changes; document bytes and fragments/assets are unchanged and revalidated under final name. Canonical ZIP_STORED writer reused with fixed metadata, UTF8 member support and bounded headers/count/CRC/hash/reference audit. No PDF/DOCX/JSON/CSS/JS/reports/captures/nested/unused members.

artifacts.audit_download dispatches by explicit new-package method, verifies current request mode/name/attempt, unchanged original source and authoritative PDF, generation/browser report hashes, persisted comparison/captures, current HTML/assets, manifest and actual ZIP bytes/CRC. Legacy audit stays separate. Pipeline now reports packaged/final_conversion_complete and runtime exits0 only on real success; failure/source integrity clears completion. Next serves completed downloads with fresh audit/state/version/cancellation/expiry checks, proper UTF8 RFC5987 names and missing/unsafe/oversize archive409 errors. No new service/dependency/license.

Final Node testing found a job whose failed-input result was complete but meta remained running after the child exited. The original exception was swallowed, so no exact OS error is known. Added bounded one-second Windows-only rename retry for EACCES/EPERM/EBUSY and explicit JOB_STATE_PUBLICATION_FAILED fallback instead of silent running abandonment. Native CreateFileW reader lock held until result publication then released; actual completion/download passes. Permanent filesystem failure is not converted into a false success.

## Actual completed verification

- Full active Python431passed,0failed,559.47sec; all final Python code covered. Final later Node-only publication change covered below.
- Targeted current+legacy package/gates101passed,21.32sec; current actual package/offline/tamper48passed,9.21sec. Scopes overlap full total.
- Final Node15passed,80.12sec, includes source/HTML/missing archive, Unicode/apostrophe, EDGAR retry, actual Windows lock, cancellation/restart/expiry. Focused lock/cancellation2passed,6.93sec.
- Final production Next/Chromium6passed,2.4min after publication fix: real EDGAR DOCX ZIP28.6sec, Standard DOCX ZIP52.5sec, reference PDF ZIP48.6sec, recovery/deletion/invalid-input/light/dark/keyboard/axe. Download events save actual ZIP names/bytes; no mock or separate API. First full UI6passed3.5min.
- Earlier Node14 run13passed/1failed494.28sec (stranded state, cancellation case417.60sec) is retained in test history; process finished naturally, no unobserved exception invented. Initial compressed test-line Ruff warnings were fixed with formatter; final Ruff passes.
- Final fixture/context8of8passed0.459sec; historical hashes and active links/checkpoint consistency verified. Ruff/pip/Prettier/read-only diff passed; LF/CRLF notices only. Fixture/user.env/Git metadata untouched.

## Evidence and limits

Actual Standard reference ZIP2,311,996bytes: one2,188,398-byte source-basename HTML plus four images at root,23pages/85,798characters. Independent EDGAR DOCX ZIP741bytes contains only independent.htm613bytes. Exact member names/bytes/CRCs/SHA and source unchanged checked. Offline extracted renamed Standard and EDGAR documents open with source text and image pixels. See docs/stage7-zip-regression.json and docs/zip-packaging.md.

All supplied complex fixtures STILL FAIL EDGAR_CLIPPING_UNSUPPORTED page1 and receive no successful EDGAR ZIP. Their Standard packages pass. Local EDGAR profile is a documented interpretation, strict_passed=false and SEC acceptancefalse. Pixel/font differences, unsupported geometry/mixed EDGAR print, OCR and platform limits remain; packaging never waives renderer errors. Stored ZIPs trade size for simple bounded mechanics; fresh audit adds local-process latency. Single Node instance only.

## Continue only when authorized

Stage8 is the final focused single-file upload interface, default-unchecked EDGAR checkbox, progress and download filename/control. Preserve current real conversion/download path while removing dashboard clutter. Stage9 broader four-path integration follows that interface; Stage10 cleanup/optimization. Stop after each approved stage and update records. Old packaging-pending jobs are not promoted; re-upload to create a new qualified conversion.

Suggested commit: refactor: package verified Standard and EDGAR ZIP downloads. User reviews/commits/pushes manually. Await explicit Stage8 authorization.

## Environment

PowerShell D:/Tools/ConvX. Clean Python var/refactor-stage2/clean-env/Scripts/python.exe; .venv also usable. Free LO .tools/libreoffice/program/soffice.com. Start .\.venv\Scripts\python dev.py (one Next server, no tokens/API). Fresh browser once: python -m playwright install chromium. Web commands in apps/web; CONVX_TEST_PYTHON can select clean interpreter. Read-only Git C:/Program Files/Git/cmd/git.exe. No Git writes.
