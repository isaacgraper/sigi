"""Request and response bodies for ATAs (SPEC-0002 §3, §7).

Payload fields are English, except those built around a glossary noun, which keep
the whole Portuguese expression (ADR-0013): `vigencia_inicio`, `situacao_vigencia`,
`data_reajuste`, `processo_sei`, `nova_vigencia_fim`.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Trimmed = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Money = Annotated[decimal.Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
Justification = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class FornecedorIn(BaseModel):
    """The fornecedor as typed: found by its CNPJ, or created (AC-0002-25)."""

    cnpj: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
    legal_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]


class AtaIn(BaseModel):
    """The body of an ATA registration (AC-0002-01)."""

    number: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    subject: Trimmed
    organ: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    fornecedor: FornecedorIn
    issued_on: datetime.date | None = None
    vigencia_inicio: datetime.date
    vigencia_fim: datetime.date
    total_value: Money
    budget_date: datetime.date


class AtaPatch(BaseModel):
    """The body of an edit: only what is sent is changed (AC-0002-24)."""

    number: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)
    ] = None
    subject: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = None
    organ: Annotated[
        str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] = None
    fornecedor: FornecedorIn | None = None
    issued_on: datetime.date | None = None
    vigencia_inicio: datetime.date | None = None
    vigencia_fim: datetime.date | None = None
    total_value: Money | None = None
    budget_date: datetime.date | None = None
    owner_id: uuid.UUID | None = None


class CancelIn(BaseModel):
    """Cancelling is the one move that asks for a justification (AC-0002-22)."""

    justification: Justification


class AditivoIn(BaseModel):
    """The body of an aditivo (AC-0002-13)."""

    kind: Literal["valor", "prazo"]
    valor_acrescimo: Money | None = None
    nova_vigencia_fim: datetime.date | None = None
    justification: Justification


class ReajusteIn(BaseModel):
    """The body of a reajuste request (AC-0002-19)."""

    processo_sei: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
    ]
    requested_on: datetime.date


class FornecedorOut(BaseModel):
    """A fornecedor, as an ATA shows it."""

    id: uuid.UUID
    cnpj: str
    legal_name: str


class AditivoOut(BaseModel):
    """An aditivo, with its justification."""

    id: uuid.UUID
    kind: str
    valor_acrescimo: decimal.Decimal | None
    nova_vigencia_fim: datetime.date | None
    justification: str
    created_at: datetime.datetime


class ReajusteOut(BaseModel):
    """A reajuste request: that it was filed, and under which process."""

    id: uuid.UUID
    processo_sei: str
    requested_on: datetime.date
    created_at: datetime.datetime


class AtaOut(BaseModel):
    """An ATA and what is derived from it."""

    id: uuid.UUID
    number: str
    subject: str
    organ: str
    fornecedor: FornecedorOut
    issued_on: datetime.date | None
    vigencia_inicio: datetime.date
    vigencia_fim: datetime.date
    total_value: decimal.Decimal
    valor_contratado: decimal.Decimal
    budget_date: datetime.date
    status: str
    situacao_vigencia: str
    data_reajuste: datetime.date
    owner_id: uuid.UUID
    created_at: datetime.datetime


class AtaDetailOut(AtaOut):
    """An ATA with its aditivos and reajuste requests."""

    aditivos: list[AditivoOut]
    reajustes: list[ReajusteOut]


class AtaPage(BaseModel):
    """A page of ATAs, in the envelope `api-conventions.md` fixes."""

    items: list[AtaOut]
    total: int
    page: int
    size: int


class AlertOut(BaseModel):
    """One row of an alert, ordered by days remaining ascending."""

    ata: AtaOut
    days_remaining: int
