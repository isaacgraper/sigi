"""Redeeming an invitation (SPEC-0001 §7 — AC-0001-11, -25, -26)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.auth import _set_cookie
from app.core.authorization import Public
from app.core.correlation import current as current_correlation_id
from app.core.db import get_session
from app.core.throttling import enforce
from app.schemas.auth import SessionOutput
from app.schemas.invite import ActivationInput, ActivationOutput
from app.services import members, sessions

router = APIRouter(prefix="/api/v1/convites", tags=["convites"], dependencies=[Depends(enforce)])

DbSession = Annotated[Session, Depends(get_session)]

# Open by definition: whoever holds the link has no account yet, which is the
# entire point. Declared rather than omitted, because AC-0001-23 refuses a write
# route with no access decision and "forgot" must not look like "decided".
OPEN = [Depends(Public())]


@router.post("/ativar", response_model=ActivationOutput, dependencies=OPEN)
def activate(
    body: ActivationInput,
    request: Request,
    response: Response,
    session: DbSession,
) -> ActivationOutput:
    """Set the password and enter (SPEC-0001 AC-0001-11, -25, -26).

    A session is issued here so that activation and first login are one step:
    sending someone to a login screen right after they chose a password is a
    place to lose them, and they have just proved they hold the credential.
    """
    now = datetime.datetime.now(datetime.UTC)
    raw = request.scope.get("state", {}).get("correlation_id")
    correlation_id = raw if isinstance(raw, uuid.UUID) else current_correlation_id()

    user = members.activate(
        session,
        token=body.token,
        password=body.password,
        at=now,
        correlation_id=correlation_id,
    )
    pair = sessions.open_session(
        session,
        user_id=user.id,
        role=user.role,
        correlation_id=correlation_id,
        mechanism="convite",
    )
    _set_cookie(response, pair.refresh_token)
    return ActivationOutput(
        session=SessionOutput(access_token=pair.access_token, expires_at=pair.expires_at)
    )
