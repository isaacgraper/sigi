"""Request and response bodies for NFs (SPEC-0005 §7).

The request keeps the names §7 fixes, which are built around the document's own
fields (`numero`, `data_emissao`, `valor`, `fornecedor_cnpj`), and the response
answers with the same ones so the screen reads back what it sent (ADR-0013).
Money and quantities are decimal strings.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.ata import Justification, Money
from app.schemas.base import RequestBody
from app.schemas.item_ata import ItemQuantity

NfStatus = Literal["aguardando", "em_conferencia", "aprovada", "devolvida"]
# Blank and malformed values are the service's to name, with the other checks.
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)]


class NfLineIn(RequestBody):
    """How much of one NE line the NF delivers (AC-0005-12)."""

    item_nota_empenho_id: uuid.UUID
    quantidade: ItemQuantity


class NfCorrectionIn(RequestBody):
    """The header and lines of an NF; the NE is not among them (AC-0005-14)."""

    numero: Text
    data_emissao: datetime.date
    valor: Money
    fornecedor_cnpj: Text
    itens: list[NfLineIn]
    confirmar_data_anterior: bool = False


class NotaFiscalIn(NfCorrectionIn):
    """An NF registration, bound to an NE and never to an ATA (AC-0005-01, -02)."""

    nota_empenho_id: uuid.UUID


class ReturnIn(RequestBody):
    """A devolução, with the justificativa AC-0005-08 asks for."""

    justificativa: Justification


class QuarantineIn(RequestBody):
    """A quarantine, with its motivo (AC-0005-13)."""

    motivo: Justification


class NfLineOut(BaseModel):
    """One line of an NF, with the insumo it delivers."""

    id: uuid.UUID
    item_nota_empenho_id: uuid.UUID
    item_ata_id: uuid.UUID
    insumo_id: uuid.UUID
    sku: str
    description: str
    unit: str
    quantidade: decimal.Decimal


class NotaFiscalOut(BaseModel):
    """An NF with its lines and the NE it belongs to."""

    id: uuid.UUID
    numero: str
    data_emissao: datetime.date
    valor: decimal.Decimal
    nota_empenho_id: uuid.UUID
    nota_empenho_number: str | None
    ata_id: uuid.UUID
    fornecedor_id: uuid.UUID
    owner_id: uuid.UUID
    status: NfStatus
    justificativa_devolucao: str | None
    quarentena: bool
    motivo_quarentena: str | None
    itens: list[NfLineOut]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class NotaFiscalPage(BaseModel):
    """A page of NFs, in the envelope `api-conventions.md` fixes."""

    items: list[NotaFiscalOut]
    total: int
    page: int
    size: int
