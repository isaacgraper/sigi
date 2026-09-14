"""Data access for `usuario`. No business rule lives here (`CLAUDE.md`)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

# Arbitrary but fixed: an advisory lock key is just a number both sides agree
# on. Named so that a second guard never picks the same one by accident.
TRAVA_GESTORES = 0x5163_0001


def por_email(sessao: Session, email: str) -> Usuario | None:
    return sessao.scalars(
        select(Usuario).where(Usuario.email == email.strip().lower())
    ).one_or_none()


def por_id(sessao: Session, usuario_id: uuid.UUID) -> Usuario | None:
    return sessao.get(Usuario, usuario_id)


def criar(
    sessao: Session,
    *,
    email: str,
    perfil: str,
    nome: str | None = None,
) -> Usuario:
    usuario = Usuario(
        email=email.strip().lower(),
        nome=nome,
        perfil=perfil,
        status="pendente",
    )
    sessao.add(usuario)
    sessao.flush()
    return usuario


def listar(sessao: Session, *, pagina: int, tamanho: int) -> Sequence[Usuario]:
    return sessao.scalars(
        select(Usuario)
        # Deterministic, so page 2 does not repeat a row from page 1. `criado_em`
        # alone is not unique enough — two invitations in the same millisecond
        # would order arbitrarily between queries.
        .order_by(Usuario.criado_em.desc(), Usuario.id)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    ).all()


def contar(sessao: Session) -> int:
    return int(sessao.scalar(select(func.count()).select_from(Usuario)) or 0)


def travar_gestores(sessao: Session) -> None:
    """Serialise every decision that could remove the last active gestor.

    "At least one active gestor exists" is an aggregate across rows, and
    snapshot isolation does not prevent two concurrent transactions from each
    observing two gestores and both committing — classic write skew. The
    database trigger catches it with `FOR UPDATE`, but measured over 40 runs the
    loser surfaces as a deadlock (`40P01`) 39 times out of 40 rather than the
    criterion's own error, so the service takes this lock first and the trigger
    stays as the backstop it should be.

    A transaction-scoped advisory lock: released at commit or rollback, with no
    row to hold and no table to contend on.
    """
    sessao.execute(text("SELECT pg_advisory_xact_lock(:chave)"), {"chave": TRAVA_GESTORES})


def contar_gestores_ativos(sessao: Session, *, exceto: uuid.UUID | None = None) -> int:
    consulta = (
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.perfil == "gestor", Usuario.status == "ativo")
    )
    if exceto is not None:
        consulta = consulta.where(Usuario.id != exceto)
    return int(sessao.scalar(consulta) or 0)
