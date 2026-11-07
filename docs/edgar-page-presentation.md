# Page dividers and readable HTM

The user requested a visible divider like the supplied filed HTM and properly indented source. Current EDGAR conversions now implement both. This is an authorized follow-up after the completed refactor, not a new stage. Standard HTML/SVG generation remains unchanged.

## Divider

Both current EDGAR strategies add a gray frame with a darker horizontal center between source pages. Where the bottom margin is large enough, the visual dimensions match the reference's 13px gray borders and 6px dark center. Shorter margins receive a thinner frame. The algorithm measures actual horizontal text, images, nonwhite graphics and any source-derived marginal-note/header translation. A one-point gap separates source content from the decorative band. A full-bleed page without safe space receives a clear note rather than covered content.

Dividers stay inside unused bottom margins. They do not increase source page dimensions, move footers or introduce blank print pages. A transparent zero-height content wrapper keeps both the normal-flow and layered strategies anchored to the original page origin. The output uses ordinary DIV elements and existing literal CSS2 border/background/box rules; it does not copy the reference's calc(), relative positioning, box-sizing or CSS3 break-before declarations. No new style-profile permission is introduced.

## Indentation and disclosure

`html_presentation.py` adds two-space structural indentation and the explicit `convx-html-format=structural-indent-v1` metadata marker. Text-bearing P/FONT/B/I and other inline runs are kept intact, including original spaces, nonbreaking spaces and literal text newlines. Generated formatting whitespace is not disclosure text.

The generator verifies unchanged disclosure before publishing. Browser and saved-ZIP verification use the same narrowly defined structural-whitespace semantics; the browser also accounts for automatically inserted TBODY containers. Only the exact generated newline/two-space pattern inside recognized structural containers is ignored. Inline text is never trimmed or normalized. Documents without the marker retain their original raw-text verification behavior. Actual browser print/word/geometry, local markup, source, asset, ZIP and CRC checks remain required.

## Actual verification

The running localhost3000 app converted the supplied DOCX and served a saved HTTP ZIP that passed fresh source, actual printed-word, asset and CRC checks. It retains 23 printed pages and 84,555 disclosure characters, with 22 visible separators and no insufficient-margin notes. The HTM has 2,877 lines and 896,629 bytes; the ZIP has 1,333,755 bytes and exactly one HTM plus four JPGs at the root. Source bytes remain unchanged. The page-boundary screenshot was visually inspected after confirming the viewed HTM bytes equal the actual downloaded member.

Final targeted Python checks:39 passed,3 supplied-reference cases deselected,155.17seconds. Coverage includes both EDGAR strategies, actual divider pixels, indentation/text preservation, old unmarked HTML, full-bleed safety, real tables/images, forgery rejection, all four bounded runtime paths and Standard renderer regressions. Production build and selected actual UI conversions/downloads:3 passed,2.6minutes,including the supplied complex DOCX and Standard/EDGAR independent PDFs. The current default test collection includes473cases; a new full473run is not claimed. The previous full-suite evidence remains historical in test history.

See [safe presentation evidence](edgar-page-presentation-regression.json), [current recovery](edgar-fix-resume.md) and [test history](test-history.md). Local EDGAR validation remains an interpretation, not SEC acceptance. Source pixel differences include the intentional decorative bands; no pixel-equivalence claim is made. No new dependency, premium service, source/config modification or Git write was introduced.
