"""Member management routes (SPEC-0001 §7 — AC-0001-10, -13, -28)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import get_session
from app.models.user import User
from app.schemas.user import (
    InviteInput,
    InviteOutput,
    MemberOutput,
    MemberPage,
    ResetTriggerOutput,
)
from app.services import members

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])

DbSession = Annotated[Session, Depends(get_session)]

# AC-0001-13: only a gestor manages members. Enforced server side on the route,
# which is the only place it counts (A01).
Gestor = Annotated[User, Depends(Requires("gestor"))]

# The member list is the one exception, and SPEC-0001 §6 states it plainly:
# "View member list — gestor ✅, servidor ❌, auditor ✅ read-only". The auditor
# exists to read the history and report on it, and a member list they cannot
# open makes the actor column of every audit row unresolvable to them.
GestorOuAuditor = Annotated[User, Depends(Requires("gestor", "auditor"))]


@router.post("", response_model=InviteOutput, status_code=status.HTTP_201_CREATED)
def invite(
    body: InviteInput,
    actor: Gestor,
    request: Request,
    session: DbSession,
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
        created_at=user.criado_em,
        activation_link=link,
    )


def _correlation(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


@router.get("", response_model=MemberPage)
def list_members(
    actor: GestorOuAuditor,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> MemberPage:
    """List members (SPEC-0001 AC-0001-15, -17).

    Open to an auditor as well as a gestor, per §6. Not AC-0001-13, which is
    about *managing* members and stays gestor only.
    """
    rows, total = members.list_members(session, page=page, size=size)
    return MemberPage(
        items=[
            MemberOutput(
                id=u.id,
                name=u.nome,
                email=u.email,
                perfil=u.role,
                status=u.status,
                created_at=u.criado_em,
                pseudonym=u.pseudonimo,
            )
            for u in rows
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post("/{user_id}/bloquear", response_model=MemberOutput)
def block(
    user_id: uuid.UUID,
    actor: Gestor,
    request: Request,
    session: DbSession,
) -> MemberOutput:
    """Block a member (SPEC-0001 AC-0001-12, -13, -29)."""
    user = members.block(
        session,
        actor=actor,
        user_id=user_id,
        at=datetime.datetime.now(datetime.UTC),
        correlation_id=_correlation(request),
    )
    return MemberOutput(
        id=user.id,
        name=user.nome,
        email=user.email,
        perfil=user.role,
        status=user.status,
        created_at=user.criado_em,
        pseudonym=user.pseudonimo,
    )


@router.post("/{user_id}/desativar", response_model=MemberOutput)
def deactivate(
    user_id: uuid.UUID,
    actor: Gestor,
    request: Request,
    session: DbSession,
) -> MemberOutput:
    """Deactivate and anonymise a member (SPEC-0001 AC-0001-13, -14, -29)."""
    user = members.deactivate(
        session,
        actor=actor,
        user_id=user_id,
        at=datetime.datetime.now(datetime.UTC),
        correlation_id=_correlation(request),
    )
    return MemberOutput(
        id=user.id,
        name=user.nome,
        email=user.email,
        perfil=user.role,
        status=user.status,
        created_at=user.criado_em,
        pseudonym=user.pseudonimo,
    )


@router.post("/{user_id}/redefinir-senha", response_model=ResetTriggerOutput)
def trigger_reset(
    user_id: uuid.UUID,
    actor: Gestor,
    request: Request,
    session: DbSession,
) -> ResetTriggerOutput:
    """Trigger a password reset for a member (SPEC-0001 AC-0001-32).

    The link comes back to the gestor, which v1.0 of the spec records as a
    deliberate loss: with no mail transport there is no channel to the member.
    The gestor cannot set the password; whoever opens the link does.
    """
    user, link = members.trigger_reset(
        session,
        actor=actor,
        user_id=user_id,
        at=datetime.datetime.now(datetime.UTC),
        correlation_id=_correlation(request),
    )
    return ResetTriggerOutput(id=user.id, reset_link=link)
