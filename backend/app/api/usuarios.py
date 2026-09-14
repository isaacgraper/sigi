"""Member management routes (SPEC-0001 §7 — AC-0001-10, -12, -13, -14, -28, -29)."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.autorizacao import Exige
from app.core.correlacao import atual
from app.core.db import obter_sessao
from app.models.usuario import Usuario
from app.schemas.auth import UsuarioSaida
from app.schemas.usuario import ConviteEntrada, ConviteSaida, MembroSaida, PaginaDeMembros
from app.services import membros

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])

SessaoDb = Annotated[Session, Depends(obter_sessao)]

# The matrix, stated on the routes themselves so that AC-0001-23's check can
# see it. The auditor reads and never writes — that is why they appear on the
# listing and nowhere else in this file.
Gestor = Annotated[Usuario, Depends(Exige("gestor"))]
GestorOuAuditor = Annotated[Usuario, Depends(Exige("gestor", "auditor"))]


def _correlation_id(request: Request) -> uuid.UUID:
    bruto = request.scope.get("state", {}).get("correlation_id")
    return bruto if isinstance(bruto, uuid.UUID) else atual()


def _agora() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


@router.get("", response_model=PaginaDeMembros)
def listar(
    sessao: SessaoDb,
    ator: GestorOuAuditor,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PaginaDeMembros:
    """List members. [SPEC-0001 AC-0001-15, -16, -17]"""
    linhas, total = membros.listar(sessao, pagina=page, tamanho=size)
    return PaginaDeMembros(
        items=[MembroSaida.model_validate(u, from_attributes=True) for u in linhas],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=ConviteSaida, status_code=status.HTTP_201_CREATED)
def convidar(
    corpo: ConviteEntrada, request: Request, sessao: SessaoDb, ator: Gestor
) -> ConviteSaida:
    """Invite a member. [SPEC-0001 AC-0001-10, -13, -28]

    The response carries the activation link once. It is not recoverable
    afterwards — only the token's HMAC is stored — so this response must not be
    logged, and no other endpoint returns it.
    """
    agora = _agora()
    usuario, link = membros.convidar(
        sessao,
        ator=ator,
        email=str(corpo.email),
        perfil=corpo.perfil,
        agora=agora,
        correlation_id=_correlation_id(request),
    )
    return ConviteSaida(
        usuario=UsuarioSaida(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            perfil=usuario.perfil,
            status=usuario.status,
        ),
        link=link,
        expira_em=agora + datetime.timedelta(hours=_ttl_convite()),
    )


@router.post("/{usuario_id}/bloquear", response_model=UsuarioSaida)
def bloquear(
    usuario_id: uuid.UUID, request: Request, sessao: SessaoDb, ator: Gestor
) -> UsuarioSaida:
    """Block an account. [SPEC-0001 AC-0001-12, -13, -29]"""
    usuario = membros.bloquear(
        sessao,
        ator=ator,
        usuario_id=usuario_id,
        agora=_agora(),
        correlation_id=_correlation_id(request),
    )
    return _saida(usuario)


@router.post("/{usuario_id}/desativar", response_model=UsuarioSaida)
def desativar(
    usuario_id: uuid.UUID, request: Request, sessao: SessaoDb, ator: Gestor
) -> UsuarioSaida:
    """Deactivate and anonymise. [SPEC-0001 AC-0001-13, -14, -29]"""
    usuario = membros.desativar(
        sessao,
        ator=ator,
        usuario_id=usuario_id,
        agora=_agora(),
        correlation_id=_correlation_id(request),
    )
    return _saida(usuario)


def _saida(usuario: Usuario) -> UsuarioSaida:
    return UsuarioSaida(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=usuario.perfil,
        status=usuario.status,
    )


def _ttl_convite() -> int:
    from app.core.config import get_settings

    return get_settings().convite_ttl_horas
