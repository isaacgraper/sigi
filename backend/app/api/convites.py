"""Redeeming an invitation (SPEC-0001 §7 — AC-0001-11, -25, -26)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.auth import CAMINHO_COOKIE, definir_cookie
from app.core.autorizacao import Publica
from app.core.correlacao import atual
from app.core.db import get_sessao
from app.schemas.auth import SessaoSaida
from app.schemas.convite import AtivacaoEntrada, AtivacaoSaida
from app.services import membros, sessoes

router = APIRouter(prefix="/api/v1/convites", tags=["convites"])

SessaoDb = Annotated[Session, Depends(get_sessao)]

# Open by definition: whoever holds the link has no account yet, which is the
# entire point. Declared rather than omitted — AC-0001-23 refuses a write route
# with no access decision, and "forgot" must not look like "decided".
ABERTA = [Depends(Publica())]


@router.post("/{token}/ativar", response_model=AtivacaoSaida, dependencies=ABERTA)
def ativar(
    token: str,
    body: AtivacaoEntrada,
    request: Request,
    response: Response,
    sessao: SessaoDb,
) -> AtivacaoSaida:
    """Set the password and enter. [SPEC-0001 AC-0001-11, -25, -26]

    A session is issued here so that activation and first login are one step:
    sending someone to a login screen right after they chose a password is a
    place to lose them, and they have just proved they hold the credential.
    """
    now = datetime.datetime.now(datetime.UTC)
    bruto = request.scope.get("state", {}).get("correlation_id")
    correlation_id = bruto if isinstance(bruto, uuid.UUID) else atual()

    usuario = membros.ativar(
        sessao, token=token, senha=body.senha, now=now, correlation_id=correlation_id
    )
    par = sessoes.abrir(
        sessao,
        usuario_id=usuario.id,
        perfil=usuario.perfil,
        correlation_id=correlation_id,
        mecanismo="convite",
    )
    definir_cookie(response, par.refresh_token)
    return AtivacaoSaida(sessao=SessaoSaida(access_token=par.access_token, expira_em=par.expira_em))


__all__ = ["CAMINHO_COOKIE", "router"]
