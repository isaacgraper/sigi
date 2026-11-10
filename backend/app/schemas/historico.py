"""History and cycle payloads (SPEC-0007 §2.1)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel


class HistoricoOut(BaseModel):
    """One row of the audit trail, as stored."""

    id: uuid.UUID
    entidade_tipo: str
    entidade_id: uuid.UUID
    acao: str
    usuario_id: uuid.UUID | None
    ocorrido_em: datetime.datetime
    dados_anteriores: dict[str, Any] | None
    justificativa: str | None
    correlation_id: uuid.UUID


class HistoricoPage(BaseModel):
    """A page of history rows, in the envelope `api-conventions.md` fixes."""

    items: list[HistoricoOut]
    total: int
    page: int
    size: int


class EventoOut(BaseModel):
    """One event of an insumo's cycle and the stage it belongs to."""

    etapa: str
    entidade_tipo: str
    entidade_id: uuid.UUID
    acao: str
    usuario_id: uuid.UUID | None
    ocorrido_em: datetime.datetime
    dados_anteriores: dict[str, Any] | None
    justificativa: str | None


class CicloOut(BaseModel):
    """The cycle of an insumo, oldest first (AC-0007-07)."""

    insumo_id: uuid.UUID
    sku: str
    eventos: list[EventoOut]
