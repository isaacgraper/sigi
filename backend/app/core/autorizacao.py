"""Who is calling, and whether they still may.

AC-0001-08 is the whole point of this module: `usuario.ativo` is checked on
**every** request, not only at login. That costs one indexed lookup per
authenticated call, and it is the difference between a deactivation that takes
effect now and one that takes effect in up to fifteen minutes — which is not a
deactivation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.seguranca import TokenInvalido, verificar_access_token
from app.models.usuario import Usuario
from app.repositories import usuario as repo
from app.services.erros import UsuarioInativo

ESQUEMA = "bearer"


def _token_do_cabecalho(request: Request) -> str:
    cabecalho = request.headers.get("authorization", "")
    tipo, _, valor = cabecalho.partition(" ")
    if tipo.lower() != ESQUEMA or not valor.strip():
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.")
    return valor.strip()


def usuario_atual(request: Request, sessao: Annotated[Session, Depends(obter_sessao)]) -> Usuario:
    claims = verificar_access_token(_token_do_cabecalho(request))
    usuario = repo.por_id(sessao, claims.usuario_id)
    if usuario is None or not usuario.ativo:
        # Same response whether the account was deleted, blocked or deactivated:
        # the caller holds a valid signature, so they already know the account
        # existed, but they learn nothing further about its state.
        raise UsuarioInativo()
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]
