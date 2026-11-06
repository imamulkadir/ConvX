# Active conversion pipeline

1. Validate the filename/type and streamed upload size. Store bytes under a new opaque private job directory.
2. DOCX: inspect safe OOXML/ZIP, detect and accept tracked changes in a separate copy, export to PDF using free local LibreOffice. Never modify the original. PDF: admit the uploaded PDF directly; never convert it into DOCX.
3. Validate PDF signatures/structure/pages/geometry/active content, then analyze the authoritative PDF once into shared source-bound text/font/page/table/image/vector records.
4. Retain native images/masks with deterministic private names and hashes. Report image-only/OCR and unsupported extraction limitations without fabricated text.
5. Standard: generate `.html` with embedded CSS/selectable native SVG paint and required local assets. EDGAR: generate filename-compatible `.htm`, permitted flow markup and JPG/GIF under the documented local profile.
6. Validate actual markup/assets and source content; render with bounded pinned Chromium and compare actual DOM/print text, page geometry and raw screen/print pixels. Keep measured differences visible; no exact-fidelity claim unless verified.
7. Package one mode-correct document and exactly referenced assets at ZIP root. Validate names, bytes, CRC, headers, references and proof. No PDFs/DOCX/reports/CSS/JS/directories or unused assets enter the ZIP.
8. At download, revalidate current source, attempt, mode, generated document/assets, browser evidence and ZIP. Serve only the verified bytes with the uploaded basename.zip.

All steps are local server-side processing behind one Next application. Conversion has a whole-process budget and cooperative cancellation, child RSS/output/disk monitoring and descendant termination. Private intermediates expire and recognized completed/cancelled jobs are cleaned safely. No queue service/database is required.

Both inputs/modes have real independent runtime and browser regressions. Supplied complex fixtures succeed in Standard against their authoritative PDFs but fail EDGAR_CLIPPING_UNSUPPORTED on page1; no archive is published for those failures. LibreOffice/Word equivalence, all possible document layouts and SEC acceptance are not claimed. See [integration checks](integration-testing.md), [limitations](limitations.md) and [historical pipeline](history/pre-stage10-conversion-pipeline.md.txt).
