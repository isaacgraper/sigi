"""Data access for `sessao_familia` and `sessao`."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from app.models.sessao import Sessao, SessaoFamilia


def criar_familia(sessao: Session, usuario_id: uuid.UUID) -> uuid.UUID:
    familia = uuid.uuid4()
    sessao.add(SessaoFamilia(familia=familia, usuario_id=usuario_id))
    sessao.flush()
    return familia


def criar(
    sessao: Session,
    *,
    usuario_id: uuid.UUID,
    familia: uuid.UUID,
    geracao: int,
    token_hash: bytes,
    expira_em: datetime.datetime,
) -> Sessao:
    linha = Sessao(
        usuario_id=usuario_id,
        familia=familia,
        geracao=geracao,
        refresh_token_hash=token_hash,
        expira_em=expira_em,
    )
    sessao.add(linha)
    sessao.flush()
    return linha


def por_hash(sessao: Session, token_hash: bytes) -> Sessao | None:
    """Find a session by its token hash — **including revoked ones**.

    The predicate is load-bearing: filtering `revogado_em IS NULL` here would
    turn a replay into "not found", which is a plain 401 with no family
    revocation, leaving AC-0001-07 unmet behind a test that still sees its 401.
    """
    return sessao.scalars(
        select(Sessao).where(Sessao.refresh_token_hash == token_hash)
    ).one_or_none()


def proxima_geracao(sessao: Session, familia: uuid.UUID) -> int:
    atual = sessao.scalar(select(func.max(Sessao.geracao)).where(Sessao.familia == familia))
    return int(atual or 0) + 1


def revogar_familia(
    sessao: Session, familia: uuid.UUID, *, motivo: str, momento: datetime.datetime
) -> int:
    """Revoke every live session descended from one login. Returns how many."""
    resultado = sessao.execute(
        update(Sessao)
        .where(Sessao.familia == familia, Sessao.revogado_em.is_(None))
        .values(revogado_em=momento, revogado_motivo=motivo)
    )
    sessao.execute(
        update(SessaoFamilia)
        .where(SessaoFamilia.familia == familia, SessaoFamilia.revogada_em.is_(None))
        .values(revogada_em=momento)
    )
    sessao.flush()
    return int(cast("CursorResult[Any]", resultado).rowcount or 0)


def revogar_do_usuario(
    sessao: Session, usuario_id: uuid.UUID, *, motivo: str, momento: datetime.datetime
) -> int:
    resultado = sessao.execute(
        update(Sessao)
        .where(Sessao.usuario_id == usuario_id, Sessao.revogado_em.is_(None))
        .values(revogado_em=momento, revogado_motivo=motivo)
    )
    sessao.flush()
    return int(cast("CursorResult[Any]", resultado).rowcount or 0)
