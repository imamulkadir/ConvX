# EDGAR renderer - revised Stage 6

The EDGAR path consumes the same verified authoritative PDF layout as Standard mode. It emits selectable normal-flow HTM, local JPG/GIF assets, inline literal formatting and source-bound local validation. It never serializes Standard SVG into EDGAR output. No premium dependency, hosted converter or public Python service is used.

Stage 7 provides [validated ZIPs/fresh downloads](zip-packaging.md); Stage 8 now provides the [minimal form and default-off EDGAR checkbox](simple-interface.md). Supported EDGAR conversions package `.htm` plus exactly referenced JPG/GIF, without granting legacy strict proof or SEC acceptance. Standard remains default with `.html` and unrestricted modern rendering. Unsupported EDGAR sources fail before packaging.

## Manual and interpretation

Read the supplied [Volume II version 78](../tests/fixtures/edgarfm-vol2-v78.pdf), dated September 14, 2026, SHA-256 `816bbe2b5d2677ddc94e6199b446a8a856a54596704021a7b9ff592c0bc26cf3`. Relevant one-based PDF pages: 144 (5.1/5.1.1), 157-169 (5.2.2), 169-171 (5.2.3). The internal reference PDF is not submitted or included in output assets.

The manual explicitly lists permitted tags and attributes, prohibits nested tables/active content and restricts graphics to local JPG/GIF. It lists STYLE for MANY elements without enumerating every CSS property. This implementation makes a narrow **local interpretation**, `efm78-flow-css2-v1`, rather than asserting an exhaustive SEC-approved CSS list.

The interpretation combines the manual's STYLE permission with the [W3C HTML4 Transitional DTD](https://www.w3.org/TR/html4/loose.dtd) common attributes on body, div, p, font, a, b, i, u, sup, sub, table, tr, td, th and img. Other MANY attributes retain unresolved diagnostics. The [CSS2 property index](https://www.w3.org/TR/CSS2/propidx.html) provides the formatting vocabulary. Only literal dimensions, margins/padding, display block/inline/inline-block, vertical alignment, whitespace, line height, local font family/size, colors, decoration, page breaks and table/border properties pass the existing bounded grammar. No positioning, transforms, grid/flex, SVG, box-sizing, external resources, URLs/functions, expressions, comments/escapes, hidden display or transparent text.

Source provenance inspected on 2026-11-06: W3C DTD 45,434 bytes, SHA-256 `1b46c62c9586e9519ed6e5357e56b32f7e1cc7d797b053cff0784b17eac5c008`; CSS2 index 56,077 bytes, SHA-256 `503a73555ead89289b7e75269da56b88c9b02cb9aa918f7e92e4b002c088f777`. These are supporting standards, not SEC acceptance evidence. The manual takes precedence where it excludes otherwise valid HTML4 tags/attributes.

All output bytes are ASCII. Latin-1 and [W3C HTML4 named character mappings](https://www.w3.org/TR/html4/sgml/entities.html) are preserved using character references. The HTML4 mapping beyond the manual's partial examples is explicitly part of the local interpretation. Unknown Unicode/control/C1 legacy remappings fail; no transliteration or replacement is performed. Standard retains its independent UTF-8 handling.

The [SEC formatting guidance](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/observe-data-process-filing-limits) requires avoiding independent per-word formatting and Base64 graphics. Existing renderer coalescing and source-byte checks enforce these constraints; identical source resources reuse image references.

## Implementation and evidence boundary

`packages/converter/edgar_html.py` provides a new authoritative entry point. It revalidates the shared model against native source data and reuses existing normal-flow partitioning, typography, merged-table and graphic normalization primitives. It does not call the legacy eligible-layout generator or forge its Word-reference proof. Legacy generation/validation tests and default strict uncertainty behavior remain intact.

Filename generation retains an already-valid source basename where possible and deterministically sanitizes/shortens to at most 32 ASCII characters including `.htm`, beginning with an alphanumeric. Changed/long basenames receive an eight-hex source-name hash. Asset names are local deterministic root files. Byte-preserved native JPEG is preferred; palette graphics use verified GIF, other graphics use high-quality JPEG. Alpha graphics are composited on white and this is recorded. Lossy graphic normalization is never labeled exact.

Local results carry `html_profile=edgar_flow_v1`, the supplied-manual and registry hashes, and a separate formatting-profile digest binding its properties, element scopes, HTML4 mappings and implementation/grammar bytes. Local `passed` can be true, while `strict_passed` and `sec_acceptance_confirmed` remain false. Whole-form/MIME submission accounting and authorized EDGAR validation are separate. The revised profile cannot authorize the legacy strict packaging gate.

The existing isolated, bounded Chromium verifier is shared by both renderers with separate page/text selectors. It verifies actual HTM DOM text, page dimensions, referenced assets and actual printed output. It saves screen/overlay/diff captures, raw pixel metrics and hashes. For EDGAR it also compares independently extracted printed words against source words: missing words or origin differences above six points fail with `EDGAR_LAYOUT_INCOMPATIBLE`. This six-point bound is a product defect detector, not a pixel-perfect tolerance or SEC rule. Raw pixel differences are always retained without shift/blur/correction.

The browser print check supplies source dimensions through its private print invocation; the document itself has no external stylesheet or modern named-page rules. End-user browser paper settings can affect printing. Mixed source print sizes currently fail explicitly. No universal print fidelity is claimed.

## Supported and rejected cases

Verified independent cases include simple text, normal-flow typography, a real merged-cell table, repeated JPEG/palette images, and a native LibreOffice-generated DOCX. Actual screenshots of the merged-table source and output were inspected; slight typography/border differences remain visible and measured.

Clipping, rotated/vertical text, unsupported annotations, overlapping/interlocking paint, uncertain table grids, arbitrary vector curves/compositing and unsupported hyperlinks produce meaningful failures. The only clipping exception is a single rectangular page-edge clip within 0.05 points of the page bounds with all extracted text inside it; this handles actual LibreOffice rounding without discarding clipped disclosure. There is no screenshot fallback for ordinary text. Source-page image content can remain an image; OCR is not fabricated.

**All three supplied conversion fixtures currently fail EDGAR mode at page 1 with `EDGAR_CLIPPING_UNSUPPORTED`.** Their preparation and source integrity are tested; successful EDGAR output for these documents is not claimed. Their Standard mode rendering is unaffected. Supporting their visual complexity within permitted markup remains a known limitation.

## Internal runtime contract

Python `process_input(..., mode="edgar")` and the private runtime request accept exactly `standard` or `edgar`. Existing same-origin upload route accepts `x-convx-mode: edgar`; omission selects Standard. Mode is saved and retained through eligible retries. This is internal plumbing for Stage 8, not an external API service or token requirement.

EDGAR browser captures use the existing safe PNG preview route. It rechecks source, HTM, asset and capture hashes before serving; active uploaded/generated HTML is not served by that route. Missing-browser jobs can be retried after the free local browser becomes available. Packaging-pending jobs remain ineligible for retries or downloads.

See [test history](test-history.md), [decisions](decisions.md) and [current project status](../PROJECT_STATUS.md) for actual completion and final verification results.
