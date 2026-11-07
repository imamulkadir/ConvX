# Latest recovery - page-divider and indentation follow-up complete

The latest user request is complete:both current EDGAR strategies draw visible margin-aware page separators and generate readable two-space structural indentation. See [presentation implementation](edgar-page-presentation.md), [safe current evidence](edgar-page-presentation-regression.json), PROJECT_STATUS.md and .agent-checkpoint.json.latest_presentation. Stages1-10 remain complete;no Stage11 or pending implementation. No Git writes.

Current final tests:39targeted Python passed155.17s;selected production build/browser/download3passed2.6min. Default discovery473confirmed;full473notclaimed. Actual configured liveHTTP DOCX produced23pages/22dividers/2877HTMlines/84555disclosurecharacters/1333755ZIPbytes,with fresh source/actualprint/assets/CRC QA passed and original unchanged. Actual viewedHTM bytes matched savedZIP;boundary screenshot visually checked. Current artifacts are in ignored var/page-presentation;app remains running127.0.0.1:3000.

Source page/print dimensions are unchanged. Divider thickness uses vacant bottom margin;full-bleed/no-space pages get an explicit note instead of covered content. Formatting marker structural-indent-v1 distinguishes generated indentation. Use html_presentation.disclosure_text for marked EDGAR ledgers;never strip inline FONT/P whitespace. Browser canonicalization includes auto-created TBODY. Unmarked old output retains raw text semantics. Original strict/flow/layer style-profile files and defaults remain unchanged. Standard HTML/SVG generation is unchanged.

Read permanent AGENTS instructions before any further changes. No new dependency,paid service,source/config mutation or Git writes. Final context/hash/format results are recorded in test history. Suggested commit:`fix: add page dividers and readable EDGAR output`.

---

Earlier filed-reference follow-up snapshot (historical):

# Current recovery - filed-reference improvements complete

The authorized comparison follow-up is complete. Stages1-10 remain terminal; no Stage11, pending implementation or new approval gate. Read AGENTS.md, PROJECT_STATUS.md and .agent-checkpoint.json before future changes. No Git writes were performed or are permitted.

See [implementation and limits](edgar-filed-reference.md), [safe current evidence](edgar-filed-reference-regression.json), [original clipping repair](edgar-rectangular-layout.md) and [test history](test-history.md). Do not restart completed stages or repeat the audit. Further implementation requires a new user request.

Implemented source-derived marginal header/body translation, paragraph groups/spatial column order, conservative complete borderless fields, SEC HTTP->HTTPS references, centered white pages/gray gutters, six-decimal CSS lengths and lossless-in-effect JPEG entropy optimization at unchanged quality. Standard and original strict/flow defaults remain unchanged. No new dependency or premium service.

Actual configured localhost3000 DOCX conversion completed; its saved HTTP ZIP was freshly and independently verified:23pages,84,555characters,1,278,505bytes,oneHTM/fourJPG at root,source unchanged,source/printed-word/assets/CRC passed. Artifact is under ignored var/compare-docs/improved-conversion.zip; final actual desktop/page1 previews and private job data remain there. No private IDs/PDFs/captures/reports enter userZIPs or tracked evidence. App was left running, without a restart during this follow-up; use `.\.venv\Scripts\python dev.py` if it later stops.

Measured before/after:userHTM995271->841379bytes,P1203->657,TABLE8->9,DIV3151->822,nodes6398->5960,threeSECURLs clickable. All23 page non-whitespace character inventories match the supplied target after documented bullet/asterisk normalization. Opening disclosure is topmost; source physical page/logo geometry and verified Unicode choices remain. Full responsive/authorial DOCX semantics, exact target typography/pixels, SEC acceptance and universal-layout support are not claimed. Marginal/header/body movement intentionally increases raw source pixel differences; these remain reported.

Final tests:full Python **463passed938.61s**;new semantic integrations **5passed21.60s**;Node **15passed135.388s**;production build/Chromium UI **12passed6.9min**. New integration file was registered in explicit testpaths after the broad run had collected463; collect-only confirms468 now. Unique tested coverage468, not a fabricated single-session468result. Allthree supplied complex EDGAR inputs passed actual source/print/ZIP gates. Durable logs are in ignored var/compare-docs/final-tests. Initial failed/interrupted runs are retained in test history; no failed result was promoted.

Final context/fixture/history/profile-byte/link/format checks are recorded in test history and checkpoint. Suggested commit: `feat: improve EDGAR reading order and filed-reference layout`.
