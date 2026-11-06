# Standard HTML renderer - revised Stage 5

The active pipeline renders DOCX's accepted, locally generated PDF or an uploaded PDF through the same verified shared model. Output is actual HTML5 with embedded CSS, page-sized sections, selectable SVG text, native vector/clip paint and local image files. No page screenshots, JavaScript, external CSS or redistributed font files are used in the document. SEC restrictions do not apply to this renderer. Stage 7 now provides [validated ZIP downloads](zip-packaging.md); EDGAR remains a separate renderer.

## Source and paint fidelity

The shared model binds source SHA-256, exact text, geometry and asset metadata. MuPDF's native SVG paint serialization (text_as_path=False) supplies clipping scopes beyond the model's scope associations; manual reconstruction had no reliable mapping for thousands of clips. The renderer checks this serialization against the model's exact character ledger and page dimensions before producing output. IDs and all fragment references are scoped per page to avoid cross-page clip/mask collisions.

Authoritative extraction retains clipped source paint text with an explicit preserve_clipped_text policy. Legacy inspection/strict analysis defaults remain unchanged. Native clip geometry still hides that paint visually; HTML can retain searchable clipped text. The converter is not a redaction tool. Synthetic TJ-gap spaces are inserted only when marked synthetic by the source model, at source-derived coordinates, without moving real glyphs. Unmatched nonspace characters fail rather than being invented or dropped.

Native JPEG/PNG image data is preserved where possible, with transparency/masks retained through native SVG. Embedded data URIs become bounded local files, deduplicated by SHA-256. The private Standard folder contains document.html and exactly its referenced assets. This private name remains unchanged; Stage 7 maps the ZIP entry to the source basename while preserving the qualified bytes. No PDF/DOCX/JSON/screenshots are included in this folder.

Fonts use common PostScript-family aliases and locally available fonts. No embedding permission is assumed. Browser substitution, font hinting and rasterization can differ from the source; these limitations are reported. Mathematical/special characters remain source text when reliably mapped. Annotation appearances and exotic native SVG/text mappings can fail explicitly. Native hyperlink metadata remains in the shared model; clickable navigation is not reconstructed yet. Table geometry, merged borders and text are painted faithfully, without claiming semantic HTML table inference.

## Actual browser verification

Pinned Chromium renders captured local bytes with document scripts disabled and network routes restricted to the captured resources. A bounded control.json separates worker status from terminal/editor stdout notices. Document text and page dimensions are checked in the browser; named print page sizes support mixed dimensions/rotation. Real screen PNGs, a print PDF, overlays and actual print-difference PNGs remain private diagnostics.

Raw per-page pixel differences retain every changed pixel and channel error. No blur/translation/tolerance is used to manufacture equivalence. A real 23-page reference test preserved 85,798 characters and four assets, with maximum per-page screen channel MAE 9.3705/255 and print MAE 0.9458/255. Exact equivalence is false. Visual inspection confirms retained layout/table geometry, with noticeable screen font/rasterization differences. A geometricPrecision CSS experiment worsened screen error and was rejected. These are measured results, not universal fidelity or SEC acceptance.

Preview requests validate current HTML/assets/source hashes and actual capture hashes, and serve PNG only. The application does not serve active uploaded HTML. Successful Standard rendering now proceeds to Stage 7 root-only ZIP packaging and fresh audited downloads. Valid packaging does not assert exact pixel equivalence.

## Limits and setup

Default HTML limit 32 MiB, individual image limit 32 MiB/16 million pixels, total emitted assets 128 MiB; browser capture input 160 MiB, DOM 200,000 nodes, total page pixels 64 million, and bounded browser/process time/memory/storage. Existing upload/PDF/model limits remain. Glyph objects are released after persistent layout/output generation, before starting Chromium. Windows report publication retries transient sharing-denied atomic rename for at most one second while retaining the previous complete JSON.

For a fresh environment install the existing Python requirements and the free pinned browser once:

```powershell
.\.venv\Scripts\python -m playwright install chromium
```

The app still starts with `.\.venv\Scripts\python dev.py`. Free local LibreOffice is required only for DOCX export. No token, paid renderer, conversion API or separate backend is required. See [runtime](simplified-runtime.md), [shared layout](shared-layout.md), [test history](test-history.md), [status](../PROJECT_STATUS.md) and [recovery notes](stage5-resume.md).
