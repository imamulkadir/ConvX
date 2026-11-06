# Shared PDF layout analysis - revised Stage 4

The generated accepted-DOCX PDF or exact uploaded PDF is the common visual source. Both paths call analyze_authoritative_pdf and use the same DocumentLayout, verifier and private image-resource extractor. No mode-specific PDF parser, paid service or page screenshot is introduced. Actual HTML rendering is Stage 5/6; current prepared jobs still stop at MODE_RENDERER_PENDING.

## Model and coordinates

The existing typed, immutable layout retains pages; media/crop/display geometry and rotation matrices; character IDs, exact Unicode/whitespace, baselines, quads and font/color/size/weight data; line/paragraph candidates; native and spatial reading orders; tables/cells/merged spans and character membership; image placements/transforms; vector primitives/paint order; links, annotations and repeated margin/page-number candidates. Coordinates are unrotated crop-relative PDF points, with explicit display transforms. Both mode renderers must consume this model rather than parse PDF separately.

Stage 4 adds optional typed per-page native verification and per-asset original/mask resource records. Additive defaults retain schema-1 legacy layout compatibility; the authoritative_pdf mode remains distinct from inspection_only and validated_generated_pdf. No external Word-validation hash or legacy reconstruction permission is fabricated. A model still has reconstruction_eligible=false under this new authority contract; that historical flag does not prevent source analysis and must not be relabeled as a successful rendering check.

## Independent source checks

Authoritative provenance must name direct_uploaded_pdf or accepted_docx_local_export, bind the actual PDF SHA-256 and original source hash, carry visual_authority=true and word_equivalence_verified=false, and include an accepted-DOCX hash when applicable. Direct PDF source and reference digests must match. Stale/missing/inconsistent provenance fails before extraction.

After extraction, a second native-page pass checks exact native text SHA-256/count/order, glyph origins/bounds, span font identity/size/flags/color, font resource membership, image resource association/dimensions/transforms, page dimensions/rotation, and native image/vector counts. The model is revalidated to catch missing references or changed character/table ledgers. Source hashes are checked before/after. A mismatch fails with a specific layout/source/font/position/image diagnostic; no partial verified result is returned. The same processing deadline continues through extraction and verification.

These are source-to-model consistency checks, not PDF-to-HTML visual equivalence. They do not independently prove semantic table/header/footnote inference, every vector paint parameter, font licensing, OCR accuracy or SEC acceptance. Table candidates retain confidence and unresolved cells; bidirectional order, annotations, clipping and unsupported structures keep explicit diagnostics.

## Private image resources

The pipeline creates a new private resources directory inside each attempt. Every supported placed image xref is extracted once per shared asset. Deterministic image0001.ext and mask0001.ext records bind actual payload bytes, format, dimensions and SHA-256. Repeated placements share the same asset. Native JPEG bytes are preserved without recompression; other formats use MuPDF's native extraction representation. Soft masks stay separate, without silent white-background composition or alpha loss. Native encodings may need browser/EDGAR normalization later.

Resource filenames are plain basenames relative to the trusted resources directory, never arbitrary paths. New files are exclusive, have bounded payload sizes and are not downloadable as final assets. On a failed attempt, partial private resources may remain until normal retention cleanup; no completed layout/ZIP is claimed. Stage 5/6 must validate captured resource bytes and perform mode-appropriate normalization. Stage 7 includes only actual final references at ZIP root, never this private analysis directory.

Inline images without reliable xref/payload association produce INLINE_IMAGE_RESOURCE_UNRESOLVED and no fabricated file. Shading paint omitted by native vector-path extraction produces PDF_SHADING_UNRESOLVED. Font metadata is retained; font files are not automatically exported/embedded without a licensing decision. Image-only pages retain the Stage 3 OCR warning; no OCR engine or page raster replacement is added.

Default resource budgets are 32 MiB per extracted payload and 128 MiB total, in addition to existing page/image/pixel/character/model budgets and the bounded runtime process. Source fixtures and uploaded originals remain unchanged. See [runtime and limits](simplified-runtime.md), [decisions](decisions.md), [test history](test-history.md) and [stage evidence](stage4-layout-regression.json).
