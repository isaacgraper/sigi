"""History route (SPEC-0007 §2.1).

The gestor and the auditor read the whole trail; a servidor sees an insumo's
cycle instead (AC-0007-09).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.authorization import Requires
from app.core.db import DbSession
from app.models.user import User
from app.schemas.historico import HistoricoOut, HistoricoPage, change_fields
from app.services import historico as service

router = APIRouter(prefix="/api/v1/historico", tags=["historico"])

Auditor = Annotated[User, Depends(Requires("gestor", "auditor"))]


@router.get("", response_model=HistoricoPage)
def list_history(
    actor: Auditor,
    session: DbSession,
    entidade_tipo: str | None = None,
    entidade_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    de: datetime.date | None = None,
    ate: datetime.date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> HistoricoPage:
    """The history, filtered and newest first, with what each event changed (AC-0007-08 to -10)."""
    result = service.list_history(
        session,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        usuario_id=usuario_id,
        de=de,
        ate=ate,
        page=page,
        size=size,
    )
    return HistoricoPage(
        items=[
            HistoricoOut(
                id=row.id,
                entidade_tipo=row.entidade_tipo,
                entidade_id=row.entidade_id,
                acao=row.acao,
                usuario_id=row.user_id,
                ocorrido_em=row.ocorrido_em,
                dados_anteriores=row.dados_anteriores,
                justificativa=row.justificativa,
                correlation_id=row.correlation_id,
                **change_fields(result.changes[row.id]),
            )
            for row in result.rows
        ],
        total=result.total,
        page=page,
        size=size,
    )
