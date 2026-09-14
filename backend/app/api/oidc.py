"""Institutional OIDC routes (SPEC-0001 §7 — AC-0001-19 to -22)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth import definir_cookie
from app.core.autorizacao import Publica
from app.core.config import get_settings
from app.core.correlacao import atual
from app.core.db import obter_sessao
from app.repositories import usuario as repo_usuario
from app.schemas.auth import SessaoSaida
from app.services import oidc, sessoes
from app.services.auditoria import Evento, registrar, registrar_avulso
from app.services.erros import RotaIndisponivel, UsuarioNaoProvisionado

router = APIRouter(prefix="/api/v1/auth/oidc", tags=["auth"])

SessaoDb = Annotated[Session, Depends(obter_sessao)]
ABERTA = [Depends(Publica())]

COOKIE_ESTADO = "sigi_oidc_estado"


def _correlation_id(request: Request) -> uuid.UUID:
    bruto = request.scope.get("state", {}).get("correlation_id")
    return bruto if isinstance(bruto, uuid.UUID) else atual()


def _exigir_oidc() -> None:
    if not get_settings().oidc_enabled:
        raise RotaIndisponivel()


@router.get("/authorize", dependencies=ABERTA)
def authorize(response: Response) -> RedirectResponse:
    """Start institutional login. [SPEC-0001 AC-0001-19]"""
    _exigir_oidc()
    cfg = get_settings()
    pedido = oidc.iniciar(agora=datetime.datetime.now(datetime.UTC))

    redirecionamento = RedirectResponse(pedido.url, status_code=302)
    # The state travels in an httpOnly cookie, which is what binds it to this
    # caller: a state lifted from a URL is useless without it.
    redirecionamento.set_cookie(
        COOKIE_ESTADO,
        pedido.estado_assinado,
        max_age=cfg.oidc_estado_ttl_minutos * 60,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        path="/api/v1/auth/oidc",
    )
    return redirecionamento


@router.get("/callback", response_model=SessaoSaida, dependencies=ABERTA)
def callback(
    code: str, state: str, request: Request, response: Response, sessao: SessaoDb
) -> SessaoSaida:
    """Complete institutional login. [SPEC-0001 AC-0001-19, -20, -21, -22]"""
    _exigir_oidc()
    agora = datetime.datetime.now(datetime.UTC)
    correlation_id = _correlation_id(request)

    try:
        assercao = oidc.concluir(
            codigo=code,
            estado_recebido=state,
            estado_assinado=request.cookies.get(COOKIE_ESTADO),
            agora=agora,
        )
    except Exception as exc:
        _auditar_recusa(motivo=type(exc).__name__, email=None, correlation_id=correlation_id)
        raise

    usuario = repo_usuario.por_oidc_subject(sessao, assercao.subject)
    if usuario is None and assercao.email:
        usuario = repo_usuario.por_email(sessao, assercao.email)

    if usuario is None or not usuario.ativo:
        # No just-in-time provisioning: an account exists because a gestor
        # invited it, and nothing else (AC-0001-21, I3).
        _auditar_recusa(
            motivo="sem_conta" if usuario is None else f"status_{usuario.status}",
            email=assercao.email,
            correlation_id=correlation_id,
        )
        raise UsuarioNaoProvisionado()

    # First successful OIDC login binds the provider's stable subject, so later
    # logins no longer depend on the e-mail matching.
    if usuario.oidc_subject is None:
        usuario.oidc_subject = assercao.subject

    par = sessoes.abrir(
        sessao,
        usuario_id=usuario.id,
        # From the usuario record. The asserted group claim is recorded below
        # and consulted by nothing (AC-0001-22, I2).
        perfil=usuario.perfil,
        correlation_id=correlation_id,
        mecanismo="oidc",
    )
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            acao="auth.oidc_claim",
            usuario_id=usuario.id,
            dados_anteriores={
                "claim_asserido": assercao.grupo_asserido,
                "perfil_aplicado": usuario.perfil,
            },
        ),
        correlation_id=correlation_id,
        momento=agora,
    )

    definir_cookie(response, par.refresh_token)
    response.delete_cookie(COOKIE_ESTADO, path="/api/v1/auth/oidc")
    return SessaoSaida(access_token=par.access_token, expira_em=par.expira_em)


def _auditar_recusa(*, motivo: str, email: str | None, correlation_id: uuid.UUID) -> None:
    """Record the refusal in its own committed transaction.

    The request is about to raise and its session will roll back, so a row
    written there would vanish with the refusal it records.
    """
    _, _, dominio = (email or "").rpartition("@")
    registrar_avulso(
        Evento(
            entidade_tipo="usuario",
            entidade_id=oidc.uuid_nulo(),
            acao="auth.oidc_recusada",
            usuario_id=None,
            dados_anteriores={
                "motivo": motivo,
                "email_hmac": oidc.digerir_para_auditoria(email),
                "dominio": dominio or None,
            },
        ),
        correlation_id=correlation_id,
    )
