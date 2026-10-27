"""Request and response bodies for NEs (SPEC-0004 §7) and saldo (SPEC-0006 §3.1).

English names, except those built around a glossary noun, which keep the whole
Portuguese expression (ADR-0013): `processo_sei`, `numero_pre_empenho`,
`saldo_disponivel`, `valor_reservado`. Money and quantities are decimal strings.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.ata import Justification
from app.schemas.item_ata import ItemQuantity

Stage = Literal[
    "demanda", "validacao_saldo", "pre_empenho", "envio_fornecedor", "ne_emitida", "cancelada"
]
Numero = Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)]


class LineIn(BaseModel):
    """One insumo of the NE: the item of the ATA and how much of it (AC-0004-01)."""

    item_ata_id: uuid.UUID
    quantity: ItemQuantity


class NotaEmpenhoIn(BaseModel):
    """The body of an NE opening; an empty list is a missing field (AC-0004-02)."""

    ata_id: uuid.UUID
    processo_sei: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    items: Annotated[list[LineIn], Field(min_length=1)]


class ItemsIn(BaseModel):
    """The whole new list of itens; an empty one is refused as NE_SEM_ITENS (AC-0004-19)."""

    items: list[LineIn]


class AdvanceIn(BaseModel):
    """Advance one stage; `to`, when sent, must be that stage (AC-0004-05)."""

    to: Stage | None = None
    numero_pre_empenho: Numero | None = None
    number: Numero | None = None


class ReverseIn(BaseModel):
    """Reverse one stage, with the justification RN03 asks for."""

    to: Stage | None = None
    justification: Justification


class CancelNeIn(BaseModel):
    """Cancel, with the justification RN03 asks for."""

    justification: Justification


class LineOut(BaseModel):
    """One line as stored: the price was fixed when the NE was opened (I5)."""

    id: uuid.UUID
    item_ata_id: uuid.UUID
    insumo_id: uuid.UUID
    sku: str
    description: str
    unit: str
    quantity: decimal.Decimal
    unit_price: decimal.Decimal
    value: decimal.Decimal


class NotaEmpenhoOut(BaseModel):
    """An NE with its lines and its derived value."""

    id: uuid.UUID
    number: str | None
    numero_pre_empenho: str | None
    processo_sei: str
    status: Stage
    ata_id: uuid.UUID
    ata_number: str
    value: decimal.Decimal
    items: list[LineOut]
    issued_on: datetime.date | None
    owner_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime


class NotaEmpenhoPage(BaseModel):
    """A page of NEs, in the envelope `api-conventions.md` fixes."""

    items: list[NotaEmpenhoOut]
    total: int
    page: int
    size: int


class IndicatorsOut(BaseModel):
    """The stage counters (AC-0004-18)."""

    emitidas: int
    em_andamento: int
    total: int


class SaldoOut(BaseModel):
    """The value saldo of an ATA (SPEC-0006 AC-0006-01 to -04, -09)."""

    valor_contratado: decimal.Decimal
    valor_reservado: decimal.Decimal
    valor_empenhado: decimal.Decimal
    saldo_disponivel: decimal.Decimal
    comprometimento_percentual: decimal.Decimal
    alto_consumo: bool
    calculado_em: datetime.datetime


class SaldoItemOut(BaseModel):
    """The quantity saldo of one item (AC-0006-10, -11, -13)."""

    item_ata_id: uuid.UUID
    insumo_id: uuid.UUID
    sku: str
    description: str
    unit: str
    quantidade_contratada: decimal.Decimal
    quantidade_reservada: decimal.Decimal
    quantidade_empenhada: decimal.Decimal
    quantidade_disponivel: decimal.Decimal
    esgotado: bool


class SaldoItensOut(BaseModel):
    """Every item's saldo, with the instant it was summed."""

    items: list[SaldoItemOut]
    calculado_em: datetime.datetime
