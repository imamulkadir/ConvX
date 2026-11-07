# EDGAR repair recovery - completed November7,2026

The user-authorized post-refactor repair is complete. Stages1-10 remain complete; no Stage11 or pending stage approval. Read AGENTS.md, PROJECT_STATUS.md and .agent-checkpoint.json before new work. No Git writes were performed or are permitted.

The former partial-page clipping guard caused the reported failure. A separate source-associated rectangular CSS2 renderer reconstructs clipping, native tables/rules/images and selectable text. Its policy remains a local interpretation; legacy strict and original flow-profile defaults are unchanged. See [repair details](edgar-rectangular-layout.md), [safe evidence](edgar-clip-regression.json) and [historical diagnosis](edgar-failure-investigation.md).

Final durable results: **Python460passed in763.76s**, **Node15passed in100.90s**, **production build/Chromium UI12passed in5.0min**. All three supplied complex EDGAR regression inputs package successfully. Tests include Standard/four-path runtime, genuine unsupported curved clipping, forged reflow/erased financial text rejection, actual browser output, safe supervision failure and saved-download QA. Logs remain in ignored var/edgar-investigation/final-tests.

The configured app at http://127.0.0.1:3000 converted the previously failing DOCX. Its actual saved HTTP ZIP independently passed source-character/printed-word/assets/CRC checks:23pages,84,555characters,1,574,472bytes,exactly one HTM/fourJPG at root; source unchanged. The app was restarted only after confirming no ConvX server was running and was left running. Run `.\.venv\Scripts\python dev.py` if it is no longer running.

Vertical marginal disclosure is explicitly reflowed into horizontal lines in source-derived vacant page bands, including full originally clipped text. Forbidden external destinations become inactive while labels remain. Font/raw pixel differences remain measured. Do not claim exact fidelity, universal support, Word equivalence, legacy strict proof or SEC acceptance. Curved/unsupported clipping and other unsupported geometry fail without ZIP. No premium service or dependency was introduced.

Private job IDs/PDFs/captures/reports remain under ignored var or temporary test directories and never enter user ZIPs or tracked evidence. Final status/checkpoint/test history record completion. Future implementation requires a new user request; do not restart completed stages.

Suggested commit: `fix: preserve clipped EDGAR layouts with verified text and ZIP output`.
