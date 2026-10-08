"""Authentication routes (SPEC-0001 §7 — AC-0001-01 to -09 and -24).

Thin by construction: `CLAUDE.md` puts the rules in `app/services/` and leaves
HTTP concerns here. What genuinely belongs here is the cookie — which header
flags a refresh token carries is an HTTP fact, and AC-0001-01 states it as a
criterion rather than an implementation note.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.authorization import CurrentUser, Public
from app.core.config import get_settings
from app.core.correlation import current
from app.core.db import get_session
from app.core.throttling import enforce
from app.models.user import User
from app.repositories import user as repo_usuario
from app.schemas.auth import LoginInput, SessionOutput, UserOutput
from app.schemas.user import ResetConfirmInput
from app.services import sessions
from app.services.authentication import authenticate_local
from app.services.errors import InactiveUser, InvalidRefresh

router = APIRouter(prefix="/api/v1/auth", tags=["auth"], dependencies=[Depends(enforce)])

# These three are open by definition: the caller has no session yet, or is
# handing back the one they have. Declared rather than omitted, because
# AC-0001-23 refuses a write route with no decision and "they forgot" must
# never look like "they decided".
OPEN = [Depends(Public())]

# The cookie is scoped to the routes that consume it. A refresh token sent on
# every request to every path is a refresh token exposed by every request; only
# `/refresh` and `/logout` ever read it.
COOKIE_PATH = "/api/v1/auth"

DbSession = Annotated[Session, Depends(get_session)]


def _correlation_id(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current()


def _set_cookie(response: Response, value: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        cfg.cookie_refresh_name,
        value,
        max_age=cfg.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        path=COOKIE_PATH,
    )


def _read_cookie(request: Request) -> str:
    value = request.cookies.get(get_settings().cookie_refresh_name)
    if not value:
        raise InvalidRefresh()
    return value


@router.post("/login", response_model=SessionOutput, dependencies=OPEN)
def login(
    body: LoginInput, request: Request, response: Response, session: DbSession
) -> SessionOutput:
    """Local login, returning an access token and setting the refresh cookie.

    [SPEC-0001 AC-0001-01, -02, -04, -05, -24]
    """
    correlation_id = _correlation_id(request)
    user = authenticate_local(
        session, email=str(body.email), password=body.password, correlation_id=correlation_id
    )
    pair = sessions.open_session(
        session,
        user_id=user.id,
        role=user.role,
        correlation_id=correlation_id,
        mechanism="local",
    )
    _set_cookie(response, pair.refresh_token)
    return SessionOutput(access_token=pair.access_token, expires_at=pair.expires_at)


@router.post("/refresh", response_model=SessionOutput, dependencies=OPEN)
def refresh(request: Request, response: Response, session: DbSession) -> SessionOutput:
    """Rotate the token pair without asking for credentials.

    [SPEC-0001 AC-0001-06, -07]
    """
    pair = sessions.rotate(
        session,
        refresh_token=_read_cookie(request),
        role_of=_RoleOfRecord(session),
        correlation_id=_correlation_id(request),
    )
    _set_cookie(response, pair.refresh_token)
    return SessionOutput(access_token=pair.access_token, expires_at=pair.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=OPEN)
def logout(request: Request, response: Response, session: DbSession) -> None:
    """Invalidate the whole refresh family.

    [SPEC-0001 AC-0001-07]
    """
    sessions.close(
        session,
        refresh_token=request.cookies.get(get_settings().cookie_refresh_name) or "",
        correlation_id=_correlation_id(request),
    )
    # Cleared even when nothing was revoked: a caller who asked to leave should
    # not keep a cookie that still looks like a session.
    response.delete_cookie(get_settings().cookie_refresh_name, path=COOKIE_PATH)


@router.get("/me", response_model=UserOutput)
def me(user: CurrentUser) -> UserOutput:
    """Report the caller's identity.

    [SPEC-0001 AC-0001-08, -22]

    The response model is explicit rather than derived from the ORM object, so
    `senha_hash` cannot arrive here by someone adding a column (AC-0001-05).
    """
    return UserOutput(
        id=user.id,
        name=user.nome,
        email=user.email,
        perfil=user.role,
        status=user.status,
    )


class _RoleOfRecord(sessions.RoleResolver):
    """Answers "what role does this user have *now*", and refuses the dead.

    A refresh is a fresh authorisation decision, so AC-0001-08 applies to it as
    much as to any other request: renewing the access token of an account that
    was deactivated five minutes ago would hand out a further fifteen minutes of
    exactly the access the deactivation removed.
    """

    def __init__(self, session: Session) -> None:
        self.sessao = session

    def __call__(self, user_id: uuid.UUID) -> str:
        user: User | None = repo_usuario.by_id(self.sessao, user_id)
        if user is None or not user.ativo:
            raise InactiveUser()
        return user.role


@router.post("/redefinicoes/confirmar", status_code=status.HTTP_204_NO_CONTENT, dependencies=OPEN)
def confirm_reset(
    body: ResetConfirmInput,
    request: Request,
    session: DbSession,
) -> None:
    """Redeem a reset link and replace the credential (SPEC-0001 AC-0001-31).

    Open by definition: whoever holds the link cannot log in, which is why they
    are here. 204 rather than a session, deliberately — unlike activation, a
    reset may have been triggered by someone who is not the account owner, so
    handing back a session would hand it to whoever redeemed the link.
    """
    from app.services import members

    members.redeem_reset(
        session,
        token=body.token,
        password=body.password,
        at=datetime.datetime.now(datetime.UTC),
        correlation_id=_correlation_id(request),
    )
