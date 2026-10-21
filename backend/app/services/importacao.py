"""Reading a CSV file as the entity writes it (SPEC-0003 AC-0003-07, -18, -19).

Shared by the catalogue import and the items import. This module reads; what a
row means is the caller's. A file is refused whole or written whole, so every
invalid cell is collected first and reported together, with the line numbered as
a spreadsheet numbers it: the header is line 1.
"""

from __future__ import annotations

import csv
import decimal
import io
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from app.constants.insumos import IMPORT_ENCODINGS, IMPORT_MESSAGES
from app.core.config import get_settings
from app.services.errors import ImportRejected, InvalidFile

# A number once `R$`, the thousands mark and the decimal comma are dealt with.
_PLAIN_NUMBER: Final = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass(frozen=True)
class Sheet:
    """A file read into lines of named cells, every cell already trimmed."""

    separator: str
    lines: Sequence[tuple[int, dict[str, str]]]
    unknown_columns: tuple[str, ...]


class CellError(ValueError):
    """One cell that cannot be read; its message is pt-BR, for the import report."""


@dataclass
class Report:
    """The invalid cells of a file, every one of them, not only the first."""

    rows: list[dict[str, object]] = field(default_factory=list)

    def error(self, line: int, column: str, message: str) -> None:
        """Record one invalid cell."""
        self.rows.append({"line": line, "field": column, "message": message})

    def raise_if_any(self) -> None:
        """Refuse the whole file when any cell was invalid (AC-0003-07)."""
        if self.rows:
            self.rows.sort(key=lambda row: (int(str(row["line"])), str(row["field"])))
            raise ImportRejected(self.rows)


def read(content: bytes, *, required: Sequence[str], optional: Sequence[str]) -> Sheet:
    """Decode, split and name the cells of a CSV file (AC-0003-18).

    The separator of the header decides how numbers read: `;` is what a
    Brazilian Excel writes, with `,` for decimals and `.` for thousands; `,` is
    the plain format. Guessing per cell would read one column two ways.
    """
    settings = get_settings()
    if len(content) > settings.import_max_bytes:
        raise InvalidFile("O arquivo passa de 5 MB.")
    text = _decode(content)
    first_line = text.split("\n", 1)[0]
    separator = ";" if ";" in first_line else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=separator)

    try:
        header = [name.strip().lower() for name in next(reader)]
    except StopIteration:
        raise InvalidFile("O arquivo está vazio.") from None
    missing = [name for name in required if name not in header]
    if missing:
        raise InvalidFile(f"Faltam as colunas: {', '.join(missing)}.")
    known = set(required) | set(optional)
    unknown = tuple(name for name in header if name and name not in known)

    lines: list[tuple[int, dict[str, str]]] = []
    try:
        for cells in reader:
            if not any(cell.strip() for cell in cells):
                continue
            # Every cell is trimmed before anything is checked: supplier names
            # arrive as " RAZAO SOCIAL LTDA" (data-sources.md §12, AC-0003-19).
            named = {
                name: (cells[index].strip() if index < len(cells) else "")
                for index, name in enumerate(header)
                if name
            }
            lines.append((reader.line_num, named))
            if len(lines) > settings.import_max_lines:
                raise InvalidFile(f"O arquivo passa de {settings.import_max_lines} linhas.")
    except csv.Error as exc:
        raise InvalidFile("O arquivo tem aspas sem fechamento.") from exc
    return Sheet(separator=separator, lines=lines, unknown_columns=unknown)


def number(text: str, *, separator: str, places: int, positive: bool = True) -> decimal.Decimal:
    """Read a number written in the file's format, refusing rather than rounding.

    `R$ 4.892,88000` reads as 4892.88 in a `;` file. Trailing zeros are not
    places: they change nothing, so `4.892,88000` passes a two-place check.
    """
    raw = text.strip()
    if raw.upper().startswith("R$"):
        raw = raw[2:].strip()
    if separator == ";":
        raw = raw.replace(".", "").replace(",", ".")
    if not _PLAIN_NUMBER.fullmatch(raw):
        raise CellError(IMPORT_MESSAGES["number"])
    value = decimal.Decimal(raw)
    if positive and value <= 0:
        raise CellError(IMPORT_MESSAGES["positive"])
    if not positive and value < 0:
        raise CellError(IMPORT_MESSAGES["not_negative"])
    exponent = value.normalize().as_tuple().exponent
    if isinstance(exponent, int) and -exponent > places:
        raise CellError(IMPORT_MESSAGES["places"].format(places=places))
    return value


def _decode(content: bytes) -> str:
    """UTF-8 with or without a BOM, else Windows-1252; anything else is refused."""
    if b"\x00" in content:
        raise InvalidFile("O arquivo não é um CSV de texto.")
    for encoding in IMPORT_ENCODINGS:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InvalidFile("Salve o arquivo em UTF-8.")
