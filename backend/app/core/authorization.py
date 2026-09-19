"""Who is calling, and whether they still may.

AC-0001-08 is the whole point of this module: `user.ativo` is checked on
**every** request, not only at login. That costs one indexed lookup per
authenticated call, and it is the difference between a deactivation that takes
effect now and one that takes effect in up to fifteen minutes — which is not a
deactivation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_sessao
from app.core.security import TokenInvalido, verify_access_token
from app.models.user import User
from app.repositories import user as repo
from app.services.errors import UsuarioInativo

ESQUEMA = "bearer"


def _token_from_header(request: Request) -> str:
    cabecalho = request.headers.get("authorization", "")
    tipo, _, value = cabecalho.partition(" ")
    if tipo.lower() != ESQUEMA or not value.strip():
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.")
    return value.strip()


def current_usuario(request: Request, session: Annotated[Session, Depends(get_sessao)]) -> User:
    """Resolve the bearer token to a user, and refuse one that is not ativo.

    The active check runs here, on every request, rather than only at login.
    Otherwise a deactivation would take up to fifteen minutes to bite, which is
    the life of the access token (AC-0001-08).
    """
    claims = verify_access_token(_token_from_header(request))
    user = repo.by_id(session, claims.usuario_id)
    if user is None or not user.ativo:
        # Same response whether the account was deleted, blocked or deactivated:
        # the caller holds a valid signature, so they already know the account
        # existed, but they learn nothing further about its state.
        raise UsuarioInativo()
    return user


UsuarioAtual = Annotated[User, Depends(current_usuario)]
