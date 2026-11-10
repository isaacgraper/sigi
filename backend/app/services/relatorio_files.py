"""A report rendered as a file (SPEC-0009 AC-0009-01, -02, -06)."""

from __future__ import annotations

import csv
import io
import re

from fpdf import FPDF

from app.constants import LOCAL_TIMEZONE
from app.constants.relatorios import (
    CSV_BOM,
    CSV_FORMULA_GUARD,
    CSV_FORMULA_PREFIXES,
    CSV_LINE_END,
    CSV_SEPARATOR,
    FORMAT_PDF,
    HEADER_FILTERS,
    HEADER_GENERATED,
    HEADER_ID,
    HEADER_PERIOD,
    HEADER_REFERENCE,
    HEADER_REPORT,
    HEADER_USER,
    INSTANT_FORMAT,
    NO_FILTER,
    PDF_ENCODING,
    PDF_FONT,
    PDF_LINE_HEIGHT,
    PDF_ORIENTATION,
    PDF_TEXT_SIZE,
    PDF_TITLE_SIZE,
    PERIOD_BETWEEN,
    PERIOD_UNTIL,
)
from app.services.relatorios import Export

# A figure as `money` writes it: the one cell allowed to start with a minus.
_FIGURE = re.compile(r"^-?\d+(,\d+)?$")


def render(export: Export) -> bytes:
    """The file of an export, in the format it was asked in."""
    return to_pdf(export) if export.formato == FORMAT_PDF else to_csv(export)


def provenance(export: Export) -> list[tuple[str, str]]:
    """What every export opens with (AC-0009-02)."""
    reference = export.referencia.astimezone(LOCAL_TIMEZONE).strftime(INSTANT_FORMAT)
    period = (
        PERIOD_BETWEEN.format(
            start=export.inicio.astimezone(LOCAL_TIMEZONE).strftime(INSTANT_FORMAT), end=reference
        )
        if export.inicio is not None
        else PERIOD_UNTIL
    )
    filtros = "; ".join(f"{name}: {value}" for name, value in export.filtros) or NO_FILTER
    return [
        (HEADER_REPORT, export.title),
        (HEADER_ID, str(export.id)),
        (HEADER_GENERATED, export.gerado_em.astimezone(LOCAL_TIMEZONE).strftime(INSTANT_FORMAT)),
        (HEADER_USER, export.usuario),
        (HEADER_REFERENCE, reference),
        (HEADER_PERIOD, period),
        (HEADER_FILTERS, filtros),
    ]


def to_csv(export: Export) -> bytes:
    """UTF-8 with BOM and `;`, so Excel in pt-BR needs no wizard (AC-0009-06)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=CSV_SEPARATOR, lineterminator=CSV_LINE_END)
    for name, value in provenance(export):
        writer.writerow([name, safe(value)])
    writer.writerow([])
    writer.writerow(export.columns)
    for row in export.rows:
        writer.writerow([safe(cell) for cell in row])
    return (CSV_BOM + buffer.getvalue()).encode("utf-8")


def safe(cell: str) -> str:
    """Keep a spreadsheet from running a text cell as a formula."""
    if cell.startswith(CSV_FORMULA_PREFIXES) and not _FIGURE.match(cell):
        return CSV_FORMULA_GUARD + cell
    return cell


def to_pdf(export: Export) -> bytes:
    """The same provenance and table, on A4 pages on their side."""
    pdf = FPDF(orientation=PDF_ORIENTATION, format="A4")
    pdf.set_creation_date(export.gerado_em)
    pdf.set_title(_latin(export.title))
    pdf.add_page()
    pdf.set_font(PDF_FONT, style="B", size=PDF_TITLE_SIZE)
    pdf.cell(0, PDF_LINE_HEIGHT * 2, _latin(export.title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(PDF_FONT, size=PDF_TEXT_SIZE)
    for name, value in provenance(export)[1:]:
        pdf.cell(0, PDF_LINE_HEIGHT, _latin(f"{name}: {value}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(PDF_LINE_HEIGHT)
    with pdf.table(line_height=PDF_LINE_HEIGHT) as table:
        heading = table.row()
        for column in export.columns:
            heading.cell(_latin(column))
        for cells in export.rows:
            row = table.row()
            for cell in cells:
                row.cell(_latin(cell))
    return bytes(pdf.output())


def _latin(text: str) -> str:
    """The core PDF fonts hold this charset only; anything else becomes `?`."""
    return text.encode(PDF_ENCODING, "replace").decode(PDF_ENCODING)
