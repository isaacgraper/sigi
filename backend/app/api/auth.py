"""Authentication routes (SPEC-0001 §7 — AC-0001-01 to -09 and -24).

Thin by construction: `CLAUDE.md` puts the rules in `app/services/` and leaves
HTTP concerns here. What genuinely belongs here is the cookie — which header
flags a refresh token carries is an HTTP fact, and AC-0001-01 states it as a
criterion rather than an implementation note.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.authorization import Public, UsuarioAtual
from app.core.config import get_settings
from app.core.correlation import current
from app.core.db import get_sessao
from app.models.user import User
from app.repositories import user as repo_usuario
from app.schemas.auth import LoginInput, SessionOutput, UserOutput
from app.services import sessions
from app.services.authentication import authenticate_local
from app.services.errors import InactiveUser, InvalidRefresh

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# These three are open by definition: the caller has no session yet, or is
# handing back the one they have. Declared rather than omitted, because
# AC-0001-23 refuses a write route with no decision and "they forgot" must
# never look like "they decided".
OPEN = [Depends(Public())]

# The cookie is scoped to the routes that consume it. A refresh token sent on
# every request to every path is a refresh token exposed by every request; only
# `/refresh` and `/logout` ever read it.
CAMINHO_COOKIE = "/api/v1/auth"

SessaoDb = Annotated[Session, Depends(get_sessao)]


def _correlation_id(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current()


def _set_cookie(response: Response, value: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        cfg.cookie_refresh_nome,
        value,
        max_age=cfg.refresh_token_ttl_dias * 24 * 60 * 60,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        path=CAMINHO_COOKIE,
    )


def _read_cookie(request: Request) -> str:
    value = request.cookies.get(get_settings().cookie_refresh_nome)
    if not value:
        raise InvalidRefresh()
    return value


@router.post("/login", response_model=SessionOutput, dependencies=OPEN)
def login(
    body: LoginInput, request: Request, response: Response, session: SessaoDb
) -> SessionOutput:
    """Local login, returning an access token and setting the refresh cookie.

    [SPEC-0001 AC-0001-01, -02, -04, -05, -24]
    """
    correlation_id = _correlation_id(request)
    user = authenticate_local(
        session, email=str(body.email), password=body.password, correlation_id=correlation_id
    )
    par = sessions.open_session(
        session,
        usuario_id=user.id,
        role=user.role,
        correlation_id=correlation_id,
        mecanismo="local",
    )
    _set_cookie(response, par.refresh_token)
    return SessionOutput(access_token=par.access_token, expires_at=par.expira_em)


@router.post("/refresh", response_model=SessionOutput, dependencies=OPEN)
def refresh(request: Request, response: Response, session: SessaoDb) -> SessionOutput:
    """Rotate the token pair without asking for credentials.

    [SPEC-0001 AC-0001-06, -07]
    """
    par = sessions.rotate(
        session,
        refresh_token=_read_cookie(request),
        perfil_de=_RoleOfRecord(session),
        correlation_id=_correlation_id(request),
    )
    _set_cookie(response, par.refresh_token)
    return SessionOutput(access_token=par.access_token, expires_at=par.expira_em)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=OPEN)
def logout(request: Request, response: Response, session: SessaoDb) -> None:
    """Invalidate the whole refresh family.

    [SPEC-0001 AC-0001-07]
    """
    sessions.close(
        session,
        refresh_token=request.cookies.get(get_settings().cookie_refresh_nome) or "",
        correlation_id=_correlation_id(request),
    )
    # Cleared even when nothing was revoked: a caller who asked to leave should
    # not keep a cookie that still looks like a session.
    response.delete_cookie(get_settings().cookie_refresh_nome, path=CAMINHO_COOKIE)


@router.get("/me", response_model=UserOutput)
def me(user: UsuarioAtual) -> UserOutput:
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

    def __call__(self, usuario_id: uuid.UUID) -> str:
        user: User | None = repo_usuario.by_id(self.sessao, usuario_id)
        if user is None or not user.ativo:
            raise InactiveUser()
        return user.role
