# ConvX - Current Project Status

Current Stage: 10 - Final Cleanup and Optimization

Stage Status: completed

Last Completed Stage: 10

Next Stage: None - ten-stage refactor complete; user-authorized filed-reference improvement also complete

Last Updated: 2026-11-07 (Asia/Dhaka)

## Current authorized result

The user requested adapting differences between the supplied filed HTM and ConvX output. Implementation is complete and the actual configured running-app DOCX conversion/download is verified. Final broad Python and production-browser results passed; no new development stage or approval gate is inferred.

Opening marginal disclosure now appears in a source-derived header when the whole page can fit, with independently verified body translation. Paragraph groups replace separate P elements for every PDF line. Tables and text follow source-derived spatial/column reading order; complete unambiguous borderless field rows become tables. Ordinary SEC HTTP links use HTTPS with unchanged labels. White paper is centered on gray gutters. Numeric markup and new JPEG entropy coding are smaller; source disclosure, actual image geometry and original JPEG passthrough remain intact.

## Measured comparison

For the actual supplied document, compared with the user's saved ConvX output:

| Measure | Before | After |
| --- | ---: | ---: |
| Paragraphs | 1,203 | 657 |
| Tables | 8 | 9 |
| DIV elements | 3,151 | 822 |
| Total elements | 6,398 | 5,960 |
| HTM bytes | 995,271 | 841,379 |
| Clickable SEC reference URLs | 0 | 3 |

All23 page non-whitespace character inventories match the supplied filed reference after the documented bullet/asterisk normalization. This is not proof of identical authorial paragraph semantics, wording sequence or exact pixels. Actual served ZIP:1,278,505bytes,oneHTM/fourJPG at root,23pages/84,555characters,original unchanged. Saved HTTP download independently passed source,printed-word,asset,ZIP/CRC and fresh audit checks. See [safe evidence](docs/edgar-filed-reference-regression.json) and [implementation](docs/edgar-filed-reference.md).

## Verification

- Focused final renderer/semantics/word checks:18passed,3deselected,64.07seconds.
- Final new semantic integrations:5passed,21.60seconds.
- Node server suite:15passed,135.388seconds.
- Production build/real Chromium UI:12passed,6.9minutes,including supplied complex DOCX EDGAR and saved-ZIP QA.
- Full Python suite:463passed,0failed,938.61seconds. The5new integrations separately passed after registering their path; unique verified coverage is468tests. Default collection now includes all468. This is not a claimed single-session468result.
- Final fixture/context verifier:8/8passed0.117seconds; fixture/history hashes,original strict/flow policy bytes,current links,safe evidence,untouched comparison inputs,savedZIP hash,Ruff check/format10files and read-only diff whitespace passed. App remains on127.0.0.1:3000.

Initial failures and corrections are preserved in [test history](docs/test-history.md):split trademark fragments, a translated container overflowing onto a blank print page and new test discovery registration. None was treated as a successful final conversion or bypassed by weakening the6pt position detector.

## Runtime and files

Run `.\.venv\Scripts\python dev.py` and open its printed URL. The configured app remains running at http://127.0.0.1:3000. No restart,token,separate API,Redis/Celery/database or premium license is required for new conversions. One Next server invokes bounded local Python.

Changed current layered renderer/reflow/word verification, optional typography line tag, layer-only centering grammar, optional JPEG entropy optimization, new source paragraph/field module and regressions/test discovery. Persistent docs/status/checkpoint record this authorized follow-up. Standard renderer, original strict/flow profile defaults, dependency locks, source fixtures and user configuration remain unchanged. No Git writes occurred.

## Remaining limits and pending work

Physical PDF print size, actual logo geometry and verified Unicode mappings are retained. Font/spacing differences from the filed reference remain; paragraph groups still retain bounded source line positions rather than full responsive reflow or authoritative DOCX semantics. Marginal-note/header/body movement deliberately changes source pixels and remains explicitly warned/measured. Unsupported geometry and insufficient room fail meaningfully. Local EFM78/CSS2 validation is not SEC acceptance or legacy strict proof; no exact target/pixel equivalence is claimed. OCR/public-hosting/complete OS sandbox qualifications remain unchanged.

No pending implementation or next stage. Final fixture/hash/format/link/diff results are recorded in test history. See [current recovery](docs/edgar-fix-resume.md) and [decisions](docs/decisions.md). No Stage11 is scheduled.

Suggested commit message: `feat: improve EDGAR reading order and filed-reference layout`
