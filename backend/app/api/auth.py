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

from app.core.autorizacao import Publica, UsuarioAtual
from app.core.config import get_settings
from app.core.correlacao import atual
from app.core.db import obter_sessao
from app.models.usuario import Usuario
from app.repositories import usuario as repo_usuario
from app.schemas.auth import LoginEntrada, SessaoSaida, UsuarioSaida
from app.services import sessoes
from app.services.autenticacao import autenticar_local
from app.services.erros import RefreshInvalido, UsuarioInativo

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# The cookie is scoped to the routes that consume it. A refresh token sent on
# every request to every path is a refresh token exposed by every request; only
# `/refresh` and `/logout` ever read it.
CAMINHO_COOKIE = "/api/v1/auth"

SessaoDb = Annotated[Session, Depends(obter_sessao)]

# Estas três são abertas por definição — quem chama ainda não tem sessão, ou
# está devolvendo a que tem. Declarado, e não omitido: o AC-0001-23 recusa uma
# rota de escrita sem decisão, e "esqueceram" não pode parecer "decidiram".
ABERTA = [Depends(Publica())]


def _correlation_id(request: Request) -> uuid.UUID:
    bruto = request.scope.get("state", {}).get("correlation_id")
    return bruto if isinstance(bruto, uuid.UUID) else atual()


def definir_cookie(response: Response, valor: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        cfg.cookie_refresh_nome,
        valor,
        max_age=cfg.refresh_token_ttl_dias * 24 * 60 * 60,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        path=CAMINHO_COOKIE,
    )


def _ler_cookie(request: Request) -> str:
    valor = request.cookies.get(get_settings().cookie_refresh_nome)
    if not valor:
        raise RefreshInvalido()
    return valor


@router.post("/login", response_model=SessaoSaida, dependencies=ABERTA)
def login(
    corpo: LoginEntrada, request: Request, response: Response, sessao: SessaoDb
) -> SessaoSaida:
    """Local login. [SPEC-0001 AC-0001-01, -02, -04, -05, -24]"""
    correlation_id = _correlation_id(request)
    usuario = autenticar_local(
        sessao, email=str(corpo.email), senha=corpo.senha, correlation_id=correlation_id
    )
    par = sessoes.abrir(
        sessao,
        usuario_id=usuario.id,
        perfil=usuario.perfil,
        correlation_id=correlation_id,
        mecanismo="local",
    )
    definir_cookie(response, par.refresh_token)
    return SessaoSaida(access_token=par.access_token, expira_em=par.expira_em)


@router.post("/refresh", response_model=SessaoSaida, dependencies=ABERTA)
def refresh(request: Request, response: Response, sessao: SessaoDb) -> SessaoSaida:
    """Rotate the pair without asking for credentials. [SPEC-0001 AC-0001-06, -07]"""
    par = sessoes.rotacionar(
        sessao,
        refresh_token=_ler_cookie(request),
        perfil_de=_PerfilDoRegistro(sessao),
        correlation_id=_correlation_id(request),
    )
    definir_cookie(response, par.refresh_token)
    return SessaoSaida(access_token=par.access_token, expira_em=par.expira_em)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=ABERTA)
def logout(request: Request, response: Response, sessao: SessaoDb) -> None:
    """Invalidate the whole refresh family. [SPEC-0001 AC-0001-07]"""
    sessoes.encerrar(
        sessao,
        refresh_token=request.cookies.get(get_settings().cookie_refresh_nome) or "",
        correlation_id=_correlation_id(request),
    )
    # Cleared even when nothing was revoked: a caller who asked to leave should
    # not keep a cookie that still looks like a session.
    response.delete_cookie(get_settings().cookie_refresh_nome, path=CAMINHO_COOKIE)


@router.get("/me", response_model=UsuarioSaida)
def me(usuario: UsuarioAtual) -> UsuarioSaida:
    """The caller's identity. [SPEC-0001 AC-0001-08, -22]

    The response model is explicit rather than derived from the ORM object, so
    `senha_hash` cannot arrive here by someone adding a column (AC-0001-05).
    """
    return UsuarioSaida(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=usuario.perfil,
        status=usuario.status,
    )


class _PerfilDoRegistro(sessoes.PerfilResolver):
    """Answers "what perfil does this usuario have *now*", and refuses the dead.

    A refresh is a fresh authorisation decision, so AC-0001-08 applies to it as
    much as to any other request: renewing the access token of an account that
    was deactivated five minutes ago would hand out a further fifteen minutes of
    exactly the access the deactivation removed.
    """

    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def __call__(self, usuario_id: uuid.UUID) -> str:
        usuario: Usuario | None = repo_usuario.por_id(self.sessao, usuario_id)
        if usuario is None or not usuario.ativo:
            raise UsuarioInativo()
        return usuario.perfil
