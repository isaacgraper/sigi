"""Notice routes (SPEC-0008 §5).

Every perfil reads the same notices and marks them read for itself (AC-0008-03,
-05). The daily check is a command, never a route.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.constants.notificacoes import PAGE_SIZE_MAX
from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import DbSession
from app.models.user import User
from app.schemas.notificacoes import AvisoOut, AvisoPageOut
from app.services import notificacoes as service

router = APIRouter(prefix="/api/v1/notificacoes", tags=["notificacoes"])

Member = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


def _correlation(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


@router.get("", response_model=AvisoPageOut)
def list_notices(
    actor: Member,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = 20,
) -> AvisoPageOut:
    """The notices newest first, and how many this member has not read (AC-0008-04)."""
    result = service.page(session, actor=actor, page=page, size=size)
    return AvisoPageOut(
        items=[
            AvisoOut(
                id=aviso.notificacao.id,
                ata_id=aviso.ata.id,
                ata_number=aviso.ata.number,
                motivo=aviso.notificacao.motivo,
                motivo_rotulo=aviso.rotulo,
                dados=aviso.notificacao.dados or {},
                criada_em=aviso.notificacao.criada_em,
                lida=aviso.lida,
            )
            for aviso in result.items
        ],
        total=result.total,
        page=page,
        size=size,
        nao_lidas=result.nao_lidas,
    )


@router.post("/lidas", status_code=204)
def mark_all_read(actor: Member, request: Request, session: DbSession) -> Response:
    """This member read every notice (AC-0008-05)."""
    service.mark_all_read(
        session, actor=actor, at=clock.now(), correlation_id=_correlation(request)
    )
    return Response(status_code=204)


@router.post("/{notificacao_id}/lida", status_code=204)
def mark_read(
    notificacao_id: uuid.UUID, actor: Member, request: Request, session: DbSession
) -> Response:
    """This member read one notice (AC-0008-05)."""
    service.mark_read(
        session,
        actor=actor,
        notificacao_id=notificacao_id,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return Response(status_code=204)
