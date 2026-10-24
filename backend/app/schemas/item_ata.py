"""Request and response bodies for the items of an ATA (SPEC-0003 §3.5).

`unit_price` keeps five places and nothing else does (ADR-0016). `fornecedor`
keeps its glossary name; the rest is English (ADR-0013).
"""

from __future__ import annotations

import decimal
import uuid
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.ata import FornecedorIn, FornecedorOut

ItemQuantity = Annotated[decimal.Decimal, Field(gt=0, max_digits=15, decimal_places=3)]
UnitPrice = Annotated[decimal.Decimal, Field(gt=0, max_digits=15, decimal_places=5)]
ItemNumber = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class ItemIn(BaseModel):
    """An insumo added to an ATA (AC-0003-20, -23)."""

    insumo_id: uuid.UUID
    quantity: ItemQuantity
    unit_price: UnitPrice
    item_number: ItemNumber | None = None
    fornecedor: FornecedorIn | None = None


class ItemPatch(BaseModel):
    """A correction of an item; `fornecedor` and `item_number` sent as null clear them."""

    insumo_id: uuid.UUID | None = None
    quantity: ItemQuantity | None = None
    unit_price: UnitPrice | None = None
    item_number: ItemNumber | None = None
    fornecedor: FornecedorIn | None = None


class ItemInsumoOut(BaseModel):
    """The insumo an item holds, as the ATA's page shows it."""

    id: uuid.UUID
    sku: str
    description: str
    unit: str
    status: str


class ItemOut(BaseModel):
    """An item with what is derived from it (AC-0003-21, -22)."""

    id: uuid.UUID
    insumo: ItemInsumoOut
    item_number: str | None
    quantity: decimal.Decimal
    contracted_quantity: decimal.Decimal
    unit_price: decimal.Decimal
    total_value: decimal.Decimal
    fornecedor: FornecedorOut
    own_fornecedor: bool


class ItemsOut(BaseModel):
    """An ATA's items, their sum, and whether it differs from the ATA's valor_total."""

    items: list[ItemOut]
    items_value: decimal.Decimal
    total_value: decimal.Decimal
    items_value_differs: bool


class ItemsLineOut(BaseModel):
    """One line of the file as it is written, and what the import does to it (AC-0003-33)."""

    line: int
    sku: str
    description: str
    quantity: decimal.Decimal
    unit_price: decimal.Decimal
    item_number: str | None
    fornecedor: str | None
    action: str


class ItemsReportOut(BaseModel):
    """What an items import did, or would do (AC-0003-26, -33)."""

    lines: list[ItemsLineOut]
    added: int
    corrected: int
    unchanged: int
    ignored_columns: list[str]
    dry_run: bool
