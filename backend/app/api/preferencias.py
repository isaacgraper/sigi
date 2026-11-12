"""Each member's own settings (SPEC-0008 §5): the e-mail summary they receive.

Every perfil sets its own; nobody reads or writes another's (AC-0008-07).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import DbSession
from app.models.user import User
from app.schemas.notificacoes import PreferenciaEmailIn, PreferenciaEmailOut
from app.services import resumo as service

router = APIRouter(prefix="/api/v1/preferencias", tags=["preferencias"])

Member = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


@router.get("/email", response_model=PreferenciaEmailOut)
def get_email(actor: Member, session: DbSession) -> PreferenciaEmailOut:
    """The member's choice, or weekly on Mondays when they never chose."""
    choice = service.preference_of(session, actor)
    return PreferenciaEmailOut(frequencia=choice.frequencia, dia_semana=choice.dia_semana)


@router.put("/email", response_model=PreferenciaEmailOut)
def put_email(
    body: PreferenciaEmailIn, actor: Member, request: Request, session: DbSession
) -> PreferenciaEmailOut:
    """Save the member's choice, effective from the next run."""
    raw = request.scope.get("state", {}).get("correlation_id")
    choice = service.set_preference(
        session,
        actor=actor,
        frequencia=body.frequencia,
        dia_semana=body.dia_semana,
        at=clock.now(),
        correlation_id=raw if isinstance(raw, uuid.UUID) else current_correlation_id(),
    )
    return PreferenciaEmailOut(frequencia=choice.frequencia, dia_semana=choice.dia_semana)
