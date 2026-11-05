from __future__ import annotations

import io
import re
import threading
from collections import defaultdict
from contextlib import redirect_stderr, redirect_stdout

from converter.errors import fail
from converter.layout.models import TableCandidate, TableCell
from converter.pdf_analysis.geometry import box, center

_NATIVE_TABLE_LOCK = threading.Lock()


class _DiscardNativeOutput(io.TextIOBase):
    def write(self, value):
        # The upstream table implementation may print diagnostics. Never log document text.
        return len(value)


def _cluster(values, tolerance):
    groups = []
    for value in sorted(set(values)):
        if groups and value - groups[-1][-1] <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [sum(group) / len(group) for group in groups]


def _edge_index(value, edges, tolerance):
    matches = [i for i, e in enumerate(edges) if abs(value - e) <= tolerance]
    return matches[0] if len(matches) == 1 else None


def _borders(bbox, paths, tolerance):
    result = []
    for path in paths:
        if path.kind not in {"s", "fs"} or path.bbox is None:
            continue
        for item in path.items:
            segments = []
            if item.command == "l":
                segments.append(item.points)
            elif item.command == "re":
                x0, y0, x1, y1 = item.rect
                segments.extend(
                    [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
                )
            for a, b in segments:
                horizontal = (
                    abs(a[1] - b[1]) < 0.1
                    and any(abs(a[1] - y) <= tolerance for y in (bbox[1], bbox[3]))
                    and min(max(a[0], b[0]), bbox[2]) > max(min(a[0], b[0]), bbox[0])
                )
                vertical = (
                    abs(a[0] - b[0]) < 0.1
                    and any(abs(a[0] - x) <= tolerance for x in (bbox[0], bbox[2]))
                    and min(max(a[1], b[1]), bbox[3]) > max(min(a[1], b[1]), bbox[1])
                )
                if horizontal or vertical:
                    result.append(path.id)
    return tuple(sorted(set(result)))


def _plausible_borderless(table):
    # Native alignment alone often turns prose into dozens of spurious columns.
    # Keep only stable numeric columns or compact text matrices, and still label them uncertain.
    values = table.extract()
    numeric = re.compile(r"^[\s($€£¥+\-]*\d[\d\s,.()%\-]*$")
    for column in range(table.col_count):
        cells = [
            str(row[column]).strip()
            for row in values
            if column < len(row) and row[column] and str(row[column]).strip()
        ]
        if len(cells) >= 3 and sum(bool(numeric.fullmatch(cell)) for cell in cells) / len(cells) >= 0.65:
            return True
    nonempty = [str(cell).strip() for row in values for cell in row if cell and str(cell).strip()]
    return bool(
        table.col_count <= 4
        and len(nonempty) >= 6
        and all(
            len(cell) <= 60 and len(cell.split()) <= 6 and not cell.endswith((".", "!", "?", ";"))
            for cell in nonempty
        )
    )


def extract_tables(page, prefix, blocks, vector_paths, raw_paths, policy, guard, diagnostic):
    chars_by_bucket = defaultdict(list)
    for block in blocks:
        for line in block.lines:
            for span in line.spans:
                for char in span.characters:
                    xy = center(char.bbox)
                    chars_by_bucket[(int(xy[0] // 32), int(xy[1] // 32))].append((char.id, xy))
    results, checks, cell_count = [], 0, 0
    # Copy native table objects while their owning page and table finder remain alive.
    with _NATIVE_TABLE_LOCK, redirect_stdout(_DiscardNativeOutput()), redirect_stderr(_DiscardNativeOutput()):
        guard.check()
        paths = [p for p in raw_paths if p["type"] in {"s", "f", "fs"}]
        finder = page.find_tables(
            strategy="lines_strict", snap_tolerance=policy.table_snap_tolerance_pt, paths=paths
        )
        candidates = [(table, "native_lines_strict") for table in finder.tables]
        if not candidates and policy.detect_borderless_candidates and blocks:
            text_finder = page.find_tables(strategy="text", min_words_vertical=3, min_words_horizontal=2)
            candidates = [
                (table, "native_text_alignment")
                for table in text_finder.tables
                if table.row_count >= 3 and table.col_count >= 2 and _plausible_borderless(table)
            ]
        for ti, (table, method) in enumerate(candidates):
            guard.check()
            rows, columns = table.row_count, table.col_count
            if rows * columns > policy.max_cells_per_page:
                raise fail(
                    "PDF_ANALYSIS_LIMIT",
                    "analyzing_pdf",
                    "Table cell count limit exceeded",
                    "Review table complexity and extraction policy",
                )
            raw_rows = tuple(
                tuple(box(cell) if cell is not None else None for cell in row.cells) for row in table.rows
            )
            rects = list(dict.fromkeys(cell for row in raw_rows for cell in row if cell is not None))
            cell_count += len(rects)
            if cell_count > policy.max_cells_per_page:
                raise fail(
                    "PDF_ANALYSIS_LIMIT",
                    "analyzing_pdf",
                    "Per-page cell count limit exceeded",
                    "Review extraction policy",
                )
            tolerance = min(policy.table_snap_tolerance_pt, 1.0)
            xs = _cluster([x for rect in rects for x in (rect[0], rect[2])], tolerance)
            ys = _cluster([y for rect in rects for y in (rect[1], rect[3])], tolerance)
            resolved = len(xs) == columns + 1 and len(ys) == rows + 1
            grid = [[None] * columns for _ in range(rows)]
            cells = []
            identifier = f"{prefix}-t{ti:04d}"
            for ci, rect in enumerate(rects):
                guard.check()
                x0, x1 = _edge_index(rect[0], xs, tolerance), _edge_index(rect[2], xs, tolerance)
                y0, y1 = _edge_index(rect[1], ys, tolerance), _edge_index(rect[3], ys, tolerance)
                span_known = resolved and None not in (x0, x1, y0, y1) and x1 > x0 and y1 > y0
                anchor = next(
                    (
                        (r, c)
                        for r, row in enumerate(raw_rows)
                        for c, value in enumerate(row)
                        if value == rect
                    ),
                    (0, 0),
                )
                row, column = (y0, x0) if span_known else anchor
                row_span, column_span = (y1 - y0, x1 - x0) if span_known else (None, None)
                cell_id = f"{identifier}-c{ci:05d}"
                membership = []
                for bx in range(int(rect[0] // 32), int(rect[2] // 32) + 1):
                    for by in range(int(rect[1] // 32), int(rect[3] // 32) + 1):
                        for char_id, xy in chars_by_bucket.get((bx, by), []):
                            checks += 1
                            if checks > policy.max_membership_checks:
                                raise fail(
                                    "PDF_ANALYSIS_LIMIT",
                                    "analyzing_pdf",
                                    "Cell membership work budget exceeded",
                                    "Review complex overlapping tables",
                                )
                            # Half-open geometry prevents assigning a boundary character twice.
                            if rect[0] <= xy[0] < rect[2] and rect[1] <= xy[1] < rect[3]:
                                membership.append(char_id)
                if span_known:
                    for r in range(y0, y1):
                        for c in range(x0, x1):
                            if grid[r][c] is not None:
                                resolved = False
                            grid[r][c] = cell_id
                else:
                    resolved = False
                    if row < rows and column < columns:
                        grid[row][column] = cell_id
                cells.append(
                    TableCell(
                        id=cell_id,
                        bbox=rect,
                        row=row,
                        column=column,
                        row_span=row_span,
                        column_span=column_span,
                        character_ids=tuple(sorted(set(membership))),
                        border_path_ids=_borders(rect, vector_paths, tolerance),
                    )
                )
            if any(cell is None for row in grid for cell in row):
                resolved = False
            if not resolved:
                diagnostic(
                    "TABLE_GRID_UNRESOLVED",
                    "error",
                    identifier,
                    "Detected table grid/merged-cell relationships are ambiguous",
                    "Resolve table relationships before reconstruction; raw cell geometry is preserved",
                )
            if method == "native_text_alignment":
                diagnostic(
                    "BORDERLESS_TABLE_CANDIDATE",
                    "warning",
                    identifier,
                    "Aligned text suggests a borderless table but semantics are inferred",
                    "Confirm against accepted OOXML or visual geometry before table generation",
                )
            header = table.header
            results.append(
                TableCandidate(
                    id=identifier,
                    bbox=box(table.bbox),
                    rows=rows,
                    columns=columns,
                    cells=tuple(cells),
                    grid=tuple(tuple(row) for row in grid),
                    raw_cell_boxes=raw_rows,
                    method=method,
                    confidence=0.85 if method == "native_lines_strict" else 0.45,
                    header_names=tuple(str(n or "") for n in header.names),
                    header_external=bool(header.external),
                    header_bbox=box(header.bbox) if header.bbox is not None else None,
                    grid_resolved=resolved,
                )
            )
    return tuple(results)
