from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

Number = Annotated[float, Field(allow_inf_nan=False)]
Point = tuple[Number, Number]
Box = tuple[Number, Number, Number, Number]
Matrix = tuple[Number, Number, Number, Number, Number, Number]
Quad = tuple[Point, Point, Point, Point]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    @field_validator(
        "bbox",
        "media_box",
        "crop_box",
        "unrotated_bounds",
        "display_bounds",
        "observed_text_bounds",
        "header_bbox",
        "scissor",
        "rect",
        check_fields=False,
    )
    @classmethod
    def ordered_box(cls, value):
        if value is not None and (value[0] > value[2] or value[1] > value[3]):
            raise ValueError("Rectangle corners must be ordered")
        return value


class LayoutDiagnostic(Record):
    code: str
    severity: Literal["warning", "error"]
    page: int | None = None
    object_id: str | None = None
    description: str
    remediation: str
    occurrences: int = Field(default=1, ge=1)


class Character(Record):
    id: str
    text: str = Field(min_length=1)
    origin: Point
    bbox: Box
    quad: Quad
    synthetic: bool
    glyph_ids: tuple[int, ...] = ()


class TextSpan(Record):
    id: str
    source_index: int
    bbox: Box
    origin: Point
    text: str
    font_name: str
    font_ids: tuple[str, ...]
    font_size_pt: Number
    font_flags: int
    character_flags: int | None
    bold_hint: bool
    italic_hint: bool
    underline_hint: bool | None
    underline_evidence: tuple[str, ...] = ()
    script_hint: Literal["normal", "superscript", "subscript"] = "normal"
    script_evidence: Literal["native_flag", "relative_baseline", "none"] = "none"
    color_rgb: int
    opacity: int
    ascender: Number
    descender: Number
    bidi_level: int = 0
    render_modes: tuple[int, ...] = ()
    paint_sequences: tuple[int, ...] = ()
    crop_visibility: Literal["inside", "partial", "outside"]
    characters: tuple[Character, ...]

    @model_validator(mode="after")
    def exact_text(self):
        if self.text != "".join(c.text for c in self.characters):
            raise ValueError("Span text differs from character ledger")
        return self


class TextLine(Record):
    id: str
    source_index: int
    bbox: Box
    direction: Point
    writing_mode: int
    spans: tuple[TextSpan, ...]
    observed_bbox_height_pt: Number
    baseline_origins: tuple[Point, ...]
    advance_to_next_line_pt: Number | None = None


class ParagraphCandidate(Record):
    id: str
    bbox: Box
    line_ids: tuple[str, ...]
    method: Literal["native_pdf_block"] = "native_pdf_block"
    confidence: Number = 0.5
    alignment_hint: Literal["left", "right", "center", "unknown"] = "unknown"
    spacing_before_pt: Number | None = None
    spacing_after_pt: Number | None = None


class TextBlock(Record):
    id: str
    native_number: int
    bbox: Box
    lines: tuple[TextLine, ...]
    paragraphs: tuple[ParagraphCandidate, ...]


class FontDefinition(Record):
    id: str
    xref: int
    base_font: str
    resource_names: tuple[str, ...]
    font_type: str
    file_extension: str
    encoding: str
    referring_xrefs: tuple[int, ...]


class ImageAsset(Record):
    id: str
    xref: int
    soft_mask_xref: int | None
    width_px: int
    height_px: int
    bits_per_component: int
    color_space: str
    decoded_pixel_digest: str | None
    digest_algorithm: Literal["mupdf-md5-nonsecurity-identity", "not_available"]
    inline: bool


class ImagePlacement(Record):
    id: str
    asset_id: str
    native_number: int
    bbox: Box
    transform: Matrix
    quad: Quad
    paint_sequences: tuple[int, ...]
    clipping: Literal["page_bounds_only", "association_unresolved"]


class VectorPrimitive(Record):
    command: Literal["l", "c", "re", "qu"]
    points: tuple[Point, ...] = ()
    rect: Box | None = None
    orientation: int | None = None


class VectorPath(Record):
    id: str
    kind: Literal["s", "f", "fs", "clip", "group"]
    bbox: Box | None
    scissor: Box | None
    level: int
    paint_sequence: int | None
    items: tuple[VectorPrimitive, ...]
    stroke_color: tuple[Number, ...] | None
    fill_color: tuple[Number, ...] | None
    stroke_width_pt: Number | None
    properties: dict[str, JsonValue]


class PaintOperation(Record):
    sequence: int
    kind: str
    bbox: Box
    layer: str


class TextPaint(Record):
    sequence: int
    render_mode: int
    font_name: str
    font_size_pt: Number
    bbox: Box
    direction: Point
    opacity: Number
    color_space_components: int
    color: tuple[Number, ...]
    stroke_width_pt: Number
    layer: str
    character_ids: tuple[str, ...]


class TableCell(Record):
    id: str
    bbox: Box
    row: int
    column: int
    row_span: int | None
    column_span: int | None
    character_ids: tuple[str, ...]
    border_path_ids: tuple[str, ...]


class TableCandidate(Record):
    id: str
    bbox: Box
    rows: int = Field(ge=1)
    columns: int = Field(ge=1)
    cells: tuple[TableCell, ...]
    grid: tuple[tuple[str | None, ...], ...]
    raw_cell_boxes: tuple[tuple[Box | None, ...], ...]
    method: Literal["native_lines_strict", "native_text_alignment"]
    confidence: Number
    header_names: tuple[str, ...]
    header_external: bool
    header_bbox: Box | None
    grid_resolved: bool


class ReadingOrder(Record):
    native_block_ids: tuple[str, ...]
    candidate_block_ids: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    native_line_ids: tuple[str, ...]
    candidate_line_ids: tuple[str, ...]
    line_edges: tuple[tuple[str, str], ...]
    method: Literal["recursive_whitespace_xy_cut"] = "recursive_whitespace_xy_cut"
    confidence: Number
    ambiguous: bool


class RegionCandidate(Record):
    kind: Literal["header", "footer", "page_number"]
    block_id: str
    bbox: Box
    method: Literal["repeated_margin_text", "margin_page_number_pattern"]
    confidence: Number


class LinkRecord(Record):
    id: str
    bbox: Box
    kind: int
    uri: str | None
    destination_page: int | None
    destination_point: Point | None
    named_destination: str | None
    file_target: str | None = None
    xref: int | None = None


class AnnotationRecord(Record):
    id: str
    xref: int
    kind: str
    bbox: Box
    properties: dict[str, JsonValue]


class PageGeometry(Record):
    media_box: Box
    crop_box: Box
    crop_offset: Point
    unrotated_bounds: Box
    display_bounds: Box
    rotation_degrees: Literal[0, 90, 180, 270]
    pdf_to_page_matrix: Matrix
    page_to_display_matrix: Matrix
    display_to_page_matrix: Matrix


class PageLayout(Record):
    id: str
    page_number: int
    geometry: PageGeometry
    text_blocks: tuple[TextBlock, ...]
    images: tuple[ImagePlacement, ...]
    vectors: tuple[VectorPath, ...]
    paint_order: tuple[PaintOperation, ...]
    text_paints: tuple[TextPaint, ...]
    tables: tuple[TableCandidate, ...]
    links: tuple[LinkRecord, ...]
    annotations: tuple[AnnotationRecord, ...] = ()
    regions: tuple[RegionCandidate, ...] = ()
    reading_order: ReadingOrder
    observed_text_bounds: Box | None
    character_count: int
    character_sha256: Digest
    diagnostics: tuple[LayoutDiagnostic, ...]


class DocumentLayout(Record):
    schema_version: Literal[1] = 1
    extractor: Literal["convx-pdf-layout-v1"] = "convx-pdf-layout-v1"
    pymupdf_version: str
    units: Literal["pdf_points"] = "pdf_points"
    coordinates: Literal["unrotated_crop_top_left"] = "unrotated_crop_top_left"
    source_pdf_sha256: Digest
    mode: Literal["validated_generated_pdf", "inspection_only"]
    validation_report_sha256: Digest | None
    source_metadata: dict[str, str | None]
    rendering_provenance: dict[str, JsonValue]
    policy: dict[str, JsonValue]
    pages: tuple[PageLayout, ...]
    fonts: tuple[FontDefinition, ...]
    assets: tuple[ImageAsset, ...]
    extraction_complete: bool
    reconstruction_eligible: bool
    diagnostics: tuple[LayoutDiagnostic, ...]

    @model_validator(mode="after")
    def references_and_ledger(self):
        import hashlib

        identifiers: set[str] = set()

        def register(identifier):
            if identifier in identifiers:
                raise ValueError("Duplicate layout object ID")
            identifiers.add(identifier)

        for item in (*self.fonts, *self.assets):
            register(item.id)
        font_ids = {f.id for f in self.fonts}
        asset_ids = {a.id for a in self.assets}
        for number, page in enumerate(self.pages, 1):
            register(page.id)
            if number != page.page_number:
                raise ValueError("Pages must be complete and ordered")
            page_chars = set()
            page_text = []
            block_ids = {b.id for b in page.text_blocks}
            vector_ids = {v.id for v in page.vectors}
            for block in page.text_blocks:
                register(block.id)
                line_ids = {line.id for line in block.lines}
                for paragraph in block.paragraphs:
                    register(paragraph.id)
                    if not set(paragraph.line_ids) <= line_ids:
                        raise ValueError("Unknown paragraph line")
                for line in block.lines:
                    register(line.id)
                    for span in line.spans:
                        register(span.id)
                        if (
                            not set(span.font_ids) <= font_ids
                            or not set(span.underline_evidence) <= vector_ids
                        ):
                            raise ValueError("Unknown font or decoration evidence")
                        for char in span.characters:
                            register(char.id)
                            page_chars.add(char.id)
                            page_text.append(char.text)
            if (
                len(page_chars) != page.character_count
                or hashlib.sha256("".join(page_text).encode()).hexdigest() != page.character_sha256
            ):
                raise ValueError("Character ledger changed or omitted text")
            order = page.reading_order
            all_line_ids = {line.id for block in page.text_blocks for line in block.lines}
            for candidate in (order.native_line_ids, order.candidate_line_ids):
                if len(candidate) != len(all_line_ids) or set(candidate) != all_line_ids:
                    raise ValueError("Reading order must cover every text line exactly once")
            for edge in order.line_edges:
                if not set(edge) <= all_line_ids:
                    raise ValueError("Unknown line reading-order edge")
            for candidate in (order.native_block_ids, order.candidate_block_ids):
                if len(candidate) != len(block_ids) or set(candidate) != block_ids:
                    raise ValueError("Reading order must cover every text block exactly once")
            for edge in order.edges:
                if not set(edge) <= block_ids:
                    raise ValueError("Unknown reading-order edge")
            for item in (*page.images, *page.vectors, *page.tables, *page.links, *page.annotations):
                register(item.id)
            for placement in page.images:
                if placement.asset_id not in asset_ids:
                    raise ValueError("Unknown image asset")
            for table in page.tables:
                cell_ids = {cell.id for cell in table.cells}
                if len(table.grid) != table.rows or any(len(row) != table.columns for row in table.grid):
                    raise ValueError("Table grid dimensions differ")
                for row in table.grid:
                    if not {c for c in row if c is not None} <= cell_ids:
                        raise ValueError("Unknown table cell")
                for cell in table.cells:
                    register(cell.id)
                    if (
                        not set(cell.character_ids) <= page_chars
                        or not set(cell.border_path_ids) <= vector_ids
                    ):
                        raise ValueError("Unknown table character or border")
                    if not 0 <= cell.row < table.rows or not 0 <= cell.column < table.columns:
                        raise ValueError("Table cell anchor out of bounds")
                    if cell.row_span is not None and (
                        cell.row_span < 1 or cell.row + cell.row_span > table.rows
                    ):
                        raise ValueError("Invalid merged cell row span")
                    if cell.column_span is not None and (
                        cell.column_span < 1 or cell.column + cell.column_span > table.columns
                    ):
                        raise ValueError("Invalid merged cell column span")
                if table.grid_resolved and (
                    any(value is None for row in table.grid for value in row)
                    or any(cell.row_span is None or cell.column_span is None for cell in table.cells)
                ):
                    raise ValueError("Resolved table has missing cells or spans")
            if any(region.block_id not in block_ids for region in page.regions):
                raise ValueError("Unknown region text block")
            if any(not set(paint.character_ids) <= page_chars for paint in page.text_paints):
                raise ValueError("Unknown text paint character")
        blocking = any(d.severity == "error" for d in self.diagnostics) or any(
            d.severity == "error" for p in self.pages for d in p.diagnostics
        )
        if self.reconstruction_eligible and (
            self.mode != "validated_generated_pdf"
            or not self.validation_report_sha256
            or not self.extraction_complete
            or blocking
        ):
            raise ValueError("Ineligible or unresolved layout cannot authorize reconstruction")
        return self
