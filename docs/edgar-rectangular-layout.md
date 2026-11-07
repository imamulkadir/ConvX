# EDGAR rectangular-layout repair

Status: completed and verified: full Python460, Node15, production browser12, all three supplied complex EDGAR inputs and actual live HTTP download. This is an authorized post-refactor repair, not an extra development stage. See [current repair recovery](edgar-fix-resume.md) and [original diagnosis](edgar-failure-investigation.md).

## Cause and reconstruction

The former renderer rejected every partial-page clipping scope. Its general flow partitioner also could not represent this document's overlapping layout, vertical marginal disclosure, source image associations and table work efficiently. Removing the first guard would only expose subsequent failures.

The new `efm78-layered-css2-v1` strategy consumes the same verified authoritative PDF model as both original modes. Native SVG is used only to inspect actual rectangular paint-scope associations. Its full character sequence and glyph origins are checked against the shared model, native image placement is verified, and source vector ordering supplies rectangle/rule scopes. No SVG enters EDGAR output. Each original rectangle is retained as a literal clipped HTML4 block; actual source table cells/rowspans and source rectangles/rules/local graphic assets are reconstructed. No ordinary text becomes an image and no page screenshots enter the archive.

Only the current renderer resolves CLIP_ASSOCIATION_UNRESOLVED through this separate native association check; all other extraction errors remain blockers. Curved/compound clipping, unsupported graphic paint and genuinely unsupported angles still fail with diagnostics. A cosine90 residue below1e-7 is treated only as native matrix roundoff, not arbitrary rotation support. There are no issuer/filename/page-coordinate conditions.

## Local profile and typography

The separate `edgar_layers_v1` validation policy retains the original flow-v1/legacy defaults and hashes unchanged. It adds literal CSS2 overflow hidden/visible and literal word/letter spacing under its own implementation/mapping digest. The manual's STYLE/MANY interpretation remains explicitly local; passing it does not mean SEC acceptance or legacy strict qualification. The supplied manual Chapter5 remains authority; [renderer research](edgar-renderer.md) identifies the original sections.

Rectangular clipping uses [CSS2 overflow](https://www.w3.org/TR/CSS2/visufx.html#overflow-clipping), without absolute positioning, transforms or modern elements. Local pinned Chromium measures unchanged formatting runs; bounded least-squares fitting supplies literal CSS2 letter/word spacing from native glyph advances. No per-word/character formatting fragmentation or runtime document JavaScript is added. Fonts are locally available aliases, not redistributed programs. Raw measured pixel differences remain visible and nonzero.

Legacy font PUA codes are decoded only with matching source font names and verified mappings: Symbol F0B7 to U+2022 and F02A to U+2217 from the [Unicode-hosted Adobe Symbol mapping](https://www.unicode.org/Public/MAPPINGS/VENDORS/ADOBE/symbol.txt); Wingdings F0A7 to U+25AA from [Unicode WG2 N4143, Wingdings1167/page27](https://www.unicode.org/wg2/docs/n4143.pdf). U+25AA/U+25CF use explicit numeric references; [HTML4 numeric references](https://www.w3.org/TR/html4/charset.html#h-5.3.1) identify code points independently of named-entity tables. Other unknown PUA mappings stay unsupported. No letters/numbers are guessed or replaced with question marks. Exact canonical source character counts and actual printed words/financial figures are checked.

Forbidden external link destinations become inert with warnings while every label remains intact. Internal bookmarks and supported SEC archive links remain local/source-associated. No external resource is fetched by conversion.

## Explicit layout differences

Vertical sidebar text cannot retain its rotation in this CSS2 strategy. Complete source-verified raw text is reflowed as horizontal notes at its original font size into genuinely vacant source-derived page bands, preferring the footer where possible. The planner includes source text/graphics/images when finding space; it fails if no safe band fits. Clipped vertical source content is retained fully and this visibility change is separately warned. The UI prominently identifies sidebar reflow before download. Exact original orientation/appearance is not claimed.

The browser independently derives that plan from source PDF bytes. All non-reflow words retain the existing6pt origin defect bound; reflow words are checked against their independently derived planned coordinates, with raw source displacement reported separately. Native word extraction can fragment clipped vertical text, so complete verified raw character sequences supply its word ledger. Exact adjacent formatting fragments can be reassembled only at the expected source location, within2pt gaps and a common baseline; no word or digit is omitted or normalized away.

## Proof and ZIP

Actual browser-printed PDF bytes are hash-bound private evidence for the new strategy, alongside original screen/overlay/difference captures. Packaging, each fresh download and saved-ZIP QA reopen that print and source, independently recompute the word/geometry/reflow checks and reject missing/changed figures or forged target coordinates. Complete per-page source/archived-character counts remain mandatory after the explicit symbol decoding. This replaces an unsuitable paragraph-boundary token heuristic only for the new strategy; original profile checks remain unchanged.

The ZIP contains exactly one SEC-compatible HTM plus its required root JPG/GIF assets. Private printed PDFs, source documents, reports, screenshots and JSON never enter it. The real localhost3000 retry downloaded1,574,472bytes containing one HTM/four JPGs for the23-page DOCX, with84,555source characters verified and originals unchanged. Safe final evidence and test results are recorded separately after final checks.

Native process limits are unchanged. A post-publication supervisor failure now safely revokes the completion sentinel and preserves a diagnostic instead of leaving a failed UI with only warning diagnostics. A negative unit test verifies this does not grant success; actual native runtime and HTTP conversions supply the positive evidence. No premium dependency, infrastructure service, Git write or source/user-config modification is introduced.
