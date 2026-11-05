# Stage 3 reference qualification — 2026-11-05

**Result: revision content regression passes; generated PDF reference fidelity fails. The reference conversion is unsuccessful and cannot proceed to HTM generation under strict mode.** This finding is separate from whether the automated tests correctly exercise the failure gate.

## Inputs and immutable evidence

Fixture hashes remain those in [inventory](fixture-inventory.json). The original DOCX has 17 insertions/14 deletions, including an inserted paragraph mark. Deterministic acceptance leaves zero detected revisions and disables future tracking in the output. Source SHA-256 stays `9a9c22ddb0c496bde3dda78f70f0e267e30efd4b8cb410807d2846fbcdda666a`; accepted output SHA-256 is `f217bef7d63262a3d5b1ef1f7563e841e352cac60ecc0639f83d4c9927a6d78a` for the current engine. No original fixture was edited.

Ordered paragraph text and table/row/cell structure agree with the supplied accepted fixture in all 18 story parts. This is a content/structure check, **not proof of complete DOCX formatting equivalence**. All five source media parts retain their original bytes. The expected accepted fixture's nine media parts have only four unique hashes, identical to the source's four unique image hashes; additional names are duplicates rather than additional graphic content.

## Real native export and all-page comparison

Free LibreOffice `26.8.2.2 9dea406ab7695df6325b11b0e19fdca8db4b7276` was extracted locally from the vendor-hash-verified Windows MSI. Executable SHA-256: `4f133aba4d8db66122ec34bc17eeaa8b274cfa5ded03feb384953f6ae357d4cf`. Windows system font environment fingerprint: `033374e27f16642b6b43c6dd1af9287a4df4a0aacd299bed4d0740ebfb022083`.

Actual execution: `python -m converter.cli <original-docx> var/stage3-libreoffice-1g --libreoffice .tools/libreoffice/program/soffice.com --reference-pdf <reference-pdf> --expected-accepted-docx <accepted-fixture>`. The prior 512 MiB renderer attempt failed with `RENDERER_MEMORY_LIMIT`; the documented 1 GiB profile produced the complete PDF. The first attempted executable path had an extra `LibreOffice` directory and correctly reported unavailable; the verified extraction's actual path was then used.

Generated and reference PDF both have **23 US Letter pages**. All pages were compared at 96 DPI; every page fails exact raster comparison, with font-size/style-signature, word-position and/or extracted reading-order/content differences. Source default 10 pt text exported as 10 pt by LibreOffice appears at 9.96 pt in the Word PDF; source 8 pt similarly appears at 8.04 pt in the Word PDF. This observed metric difference contributes to reflow/position discrepancies; it is not evidence that a font family was missing. The code does not rewrite source font sizes to force a result.

Page 1 evidence was visually inspected: floating header/logo positioning and table/vertical spacing differ visibly. The failures are not merely a chosen pixel threshold. Pixel-difference fractions range from approximately 1.23% to 30.74% across pages. Exact percentages, per-page diagnostics and hashes are in the [redacted machine-readable summary](stage3-regression.json). Full accepted DOCX/PDFs/page images/reports remain in private ignored `var/` workspaces and are absent from any final ZIP.

## Additional diagnosis: accepted-baseline rendering

The supplied accepted DOCX was separately rendered through the same LibreOffice provider. Comparing this PDF with the independently accepted source's LibreOffice PDF gives **22 identical pages and one differing page**. On page 1, 66 extracted words shift horizontally by 9 pt. OOXML inspection identified differences in floating-table anchor properties and style serialization between the two supplied DOCX versions; the expected accepted file includes a direct table-position definition absent from the source's first table. This is additional baseline/renderer ambiguity, not proof of format equivalence after acceptance. No fixture-specific anchor correction was added.

The same-renderer diagnostic comparison does not substitute either PDF for the mandatory Word reference or make the failed reference conversion successful. The source-preserving revision engine deliberately avoids importing undocumented layout edits from the accepted fixture into a general-purpose converter.

## Acceptance interpretation

A separate genuine one-page LibreOffice export compared against an independently generated baseline from that same renderer passes content/geometry/fonts/pixels. The supplied 23-page Word reference fails and is retained as a negative renderer-qualification regression. Self-comparing the original PDF passes all 23 pages, and changing page 23 alone is detected. These distinguish functioning processing/validation from a claim that the fixture is pixel-perfect.

Next-stage development may use separately validated test documents, but this reference document must remain stopped at the strict PDF gate until its discrepancies are resolved by a free, evidence-supported implementation. No paid renderer, evaluation output, full-page-image substitution or permissive threshold is authorized as a workaround.
