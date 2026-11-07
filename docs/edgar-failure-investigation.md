# Running-instance EDGAR failure investigation

Historical diagnosis, resolved on2026-11-07 by the [rectangular-layout repair](edgar-rectangular-layout.md). The failure below describes the pre-repair renderer; current evidence is in [regression results](edgar-clip-regression.json).

2026-11-06: user reported EDGAR failure while Standard succeeded. Inspected the existing successful Standard job and resubmitted the exact same uploaded DOCX bytes to the running loopback Next application on port3000 with EDGAR enabled. The earlier failed job had been cleared; this is a fresh live reproduction, not a claim to have retrieved that deleted record. Private IDs/reports remain under ignored var/edgar-investigation.

Actual retry failed during generating_htm with EDGAR_CLIPPING_UNSUPPORTED on page1. DOCX admission, tracked-change acceptance, free PDF export and shared23-page analysis completed; source bytes remained unchanged and matched the successful Standard upload. No EDGAR ZIP was created.

Page1 has51native PDF clipping scopes. The first rejected scope p0001-v00008 is a narrow horizontal region near the top: [0,19.84998,611.95001,38.25]points in a612x792point page. Current edgar_html.py accepts only near-full-page rectangular clipping containing all extracted text; this partial region necessarily fails that guard. It does not analyze whether a partial scope is harmless or reconstructable using flow markup. This is a conservative current-renderer implementation limitation, not an SEC rejection or evidence that the original document is invalid.

Standard succeeds through its separate native SVG/CSS paint renderer, which preserves clipping. EDGAR uses restricted normal-flow reconstruction and currently stops instead of silently discarding clip semantics or replacing ordinary text with screenshots. Supporting this document requires source-bound clip/content association and appropriate permitted text/table/header reconstruction, then actual disclosure/browser/geometry/asset validation. Simply removing the guard does not establish correctness or compliance.

Investigation only: no renderer, gate, settings or running-server restart change. Existing stage10 terminal checkpoint remains; no Stage11 is created. The supplied complex-document limitation remains unresolved. Actual current-instance retry and same-source verification are the tests; no unnecessary full-suite rerun claimed.
