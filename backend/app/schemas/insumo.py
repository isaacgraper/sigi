"""Request and response bodies for the catalogue, its grupos and its imports (SPEC-0003).

Payload fields are English, except those built around a glossary noun, which keep
the whole Portuguese expression (ADR-0013): `codigo_doms`, `grupo_id`. `unit` is
the dispensing unit (`UN`, `CX`), not the health facility the glossary calls
unidade.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.ata import Justification

Quantity = Annotated[decimal.Decimal, Field(ge=0, max_digits=15, decimal_places=3)]

Text20 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Text40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Text120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Text300 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class InsumoIn(BaseModel):
    """The body of an insumo registration (AC-0003-01)."""

    sku: Text40
    description: Text300
    unit: Text20
    grupo_id: uuid.UUID
    codigo_doms: Annotated[str | None, StringConstraints(max_length=20)] = None
    external_code: Annotated[str | None, StringConstraints(max_length=40)] = None
    reference_quantity: Quantity | None = None


class InsumoPatch(BaseModel):
    """The body of a correction; the SKU changes only by its own route (AC-0003-11)."""

    model_config = ConfigDict(extra="forbid")

    description: Text300 | None = None
    unit: Text20 | None = None
    grupo_id: uuid.UUID | None = None
    codigo_doms: Annotated[str | None, StringConstraints(max_length=20)] = None
    external_code: Annotated[str | None, StringConstraints(max_length=40)] = None
    reference_quantity: Quantity | None = None


class SkuChangeIn(BaseModel):
    """A new SKU and why (AC-0003-04)."""

    sku: Text40
    justification: Justification


class JustificationIn(BaseModel):
    """Discontinuing and reactivating ask for a justification (AC-0003-14, -16)."""

    justification: Justification


class SubstituteIn(BaseModel):
    """The insumo that replaces this one, and why (AC-0003-15)."""

    substitute_id: uuid.UUID
    justification: Justification


class GrupoIn(BaseModel):
    """A grupo and, below level 1, its parent (AC-0003-09)."""

    name: Text120
    parent_id: uuid.UUID | None = None


class GrupoPatch(BaseModel):
    """A new name for a grupo (AC-0003-13)."""

    name: Text120


class UserGruposIn(BaseModel):
    """The grupos a servidor owns, replacing what it had (AC-0003-30)."""

    grupo_ids: list[uuid.UUID]


class GrupoRef(BaseModel):
    """A grupo as a path element."""

    id: uuid.UUID
    name: str
    level: int


class GrupoNodeOut(GrupoRef):
    """A grupo of the tree, with its children."""

    parent_id: uuid.UUID | None
    children: list[GrupoNodeOut]


class SubstituteOut(BaseModel):
    """The insumo that replaces another."""

    id: uuid.UUID
    sku: str
    description: str


class InsumoOut(BaseModel):
    """An insumo with its grupo path and its derived situação."""

    id: uuid.UUID
    sku: str
    codigo_doms: str | None
    external_code: str | None
    description: str
    unit: str
    grupo_id: uuid.UUID
    grupo_path: list[GrupoRef]
    reference_quantity: decimal.Decimal | None
    status: str
    discontinued_on: datetime.date | None
    substitute: SubstituteOut | None
    created_at: datetime.datetime


class InsumoAtaOut(BaseModel):
    """One ATA an insumo is an item of (AC-0003-12)."""

    ata_id: uuid.UUID
    ata_number: str
    ata_status: str
    item_id: uuid.UUID
    quantity: decimal.Decimal
    unit_price: decimal.Decimal


class InsumoDetailOut(InsumoOut):
    """An insumo with the ATAs it is an item of."""

    atas: list[InsumoAtaOut]


class InsumoPage(BaseModel):
    """A page of insumos, in the envelope `api-conventions.md` fixes."""

    items: list[InsumoOut]
    total: int
    page: int
    size: int


class UserGruposOut(BaseModel):
    """The grupos a servidor now owns."""

    user_id: uuid.UUID
    grupo_ids: list[uuid.UUID]


class CatalogueReportOut(BaseModel):
    """What a catalogue import did, or would do (AC-0003-06 to -08)."""

    created: int
    updated: int
    unchanged: int
    corrected_descriptions: int
    ignored_columns: list[str]
    notes: list[str]
    dry_run: bool
