"""Member management routes (SPEC-0001 §7 — AC-0001-10, -13, -28)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import get_sessao
from app.models.user import User
from app.schemas.user import InviteInput, InviteOutput
from app.services import members

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])

SessaoDb = Annotated[Session, Depends(get_sessao)]

# AC-0001-13: only a gestor manages members. Enforced server side on the route,
# which is the only place it counts (A01).
Gestor = Annotated[User, Depends(Requires("gestor"))]


@router.post("", response_model=InviteOutput, status_code=status.HTTP_201_CREATED)
def invite(
    body: InviteInput,
    actor: Gestor,
    request: Request,
    session: SessaoDb,
) -> InviteOutput:
    """Invite a member (SPEC-0001 AC-0001-10, -13, -28).

    The activation link comes back in this response and nowhere else. The gestor
    delivers it through whatever channel the entity already trusts, because
    there is no mail transport in this project and every account in the system
    is born from an invitation.
    """
    now = datetime.datetime.now(datetime.UTC)
    raw = request.scope.get("state", {}).get("correlation_id")
    correlation_id = raw if isinstance(raw, uuid.UUID) else current_correlation_id()

    user, link = members.invite(
        session,
        actor=actor,
        email=str(body.email),
        role=body.perfil,
        at=now,
        correlation_id=correlation_id,
    )
    return InviteOutput(
        id=user.id,
        email=user.email or "",
        perfil=user.role,
        status=user.status,
        criado_em=user.criado_em,
        link_ativacao=link,
    )
