"""History and cycle payloads (SPEC-0007 §2.1)."""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.services.history_changes import EventChanges


class AlteracaoOut(BaseModel):
    """A field an event changed; `antes` or `depois` is null on a creation or a removal."""

    campo: str
    rotulo: str
    tipo: str
    antes: Any
    depois: Any


class DetalheOut(BaseModel):
    """A recorded key that is not a change, with its pt-BR label."""

    campo: str
    rotulo: str
    valor: Any


class ChangesOut(BaseModel):
    """What an event changed and what else it recorded (AC-0007-10)."""

    acao_rotulo: str
    alteracoes: list[AlteracaoOut]
    detalhes: list[DetalheOut]


def change_fields(changes: EventChanges) -> dict[str, Any]:
    """The three fields of `ChangesOut`, to pass into an event's payload."""
    return {
        "acao_rotulo": changes.acao_rotulo,
        "alteracoes": [
            AlteracaoOut(
                campo=c.campo, rotulo=c.rotulo, tipo=c.tipo, antes=c.antes, depois=c.depois
            )
            for c in changes.alteracoes
        ],
        "detalhes": [
            DetalheOut(campo=d.campo, rotulo=d.rotulo, valor=d.valor) for d in changes.detalhes
        ],
    }


class HistoricoOut(ChangesOut):
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


class EventoOut(ChangesOut):
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
