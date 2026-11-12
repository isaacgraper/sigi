"""Notice payloads (SPEC-0008 §5)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel


class AvisoOut(BaseModel):
    """One notice as the signed-in member reads it."""

    id: uuid.UUID
    ata_id: uuid.UUID
    ata_number: str
    motivo: str
    motivo_rotulo: str
    dados: dict[str, Any]
    criada_em: datetime.datetime
    lida: bool


class AvisoPageOut(BaseModel):
    """A page of notices, in the envelope `api-conventions.md` fixes, with the unread count."""

    items: list[AvisoOut]
    total: int
    page: int
    size: int
    nao_lidas: int


class PreferenciaEmailIn(BaseModel):
    """A member's e-mail choice (AC-0008-07): `diario`, `semanal` or `nenhum`, an ISO weekday."""

    frequencia: str
    dia_semana: int = 1


class PreferenciaEmailOut(BaseModel):
    """A member's e-mail choice as stored, or the default."""

    frequencia: str
    dia_semana: int
