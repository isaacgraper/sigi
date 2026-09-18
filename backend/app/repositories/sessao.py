"""Data access for `sessao_familia` and `sessao`."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from app.models.sessao import Sessao, SessaoFamilia


def create_familia(sessao: Session, usuario_id: uuid.UUID) -> uuid.UUID:
    """Open a session family for one usuario, and return its id."""
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
    """Insert one session row of a family, storing only the token HMAC."""
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


def by_hash(sessao: Session, token_hash: bytes) -> Sessao | None:
    """Find a session by its token hash — **including revoked ones**.

    The predicate is load-bearing: filtering `revogado_em IS NULL` here would
    turn a replay into "not found", which is a plain 401 with no family
    revocation, leaving AC-0001-07 unmet behind a test that still sees its 401.
    """
    return sessao.scalars(
        select(Sessao).where(Sessao.refresh_token_hash == token_hash)
    ).one_or_none()


def next_geracao(sessao: Session, familia: uuid.UUID) -> int:
    """The next generation number in a family, counting from one."""
    atual = sessao.scalar(select(func.max(Sessao.geracao)).where(Sessao.familia == familia))
    return int(atual or 0) + 1


def revoke_familia(
    sessao: Session, familia: uuid.UUID, *, motivo: str, at: datetime.datetime
) -> int:
    """Revoke every live session descended from one login. Returns how many."""
    result = sessao.execute(
        update(Sessao)
        .where(Sessao.familia == familia, Sessao.revogado_em.is_(None))
        .values(revogado_em=at, revogado_motivo=motivo)
    )
    sessao.execute(
        update(SessaoFamilia)
        .where(SessaoFamilia.familia == familia, SessaoFamilia.revogada_em.is_(None))
        .values(revogada_em=at)
    )
    sessao.flush()
    return int(cast("CursorResult[Any]", result).rowcount or 0)


def revoke_for_usuario(
    sessao: Session, usuario_id: uuid.UUID, *, motivo: str, at: datetime.datetime
) -> int:
    """Revoke every live session of one usuario. Returns how many."""
    result = sessao.execute(
        update(Sessao)
        .where(Sessao.usuario_id == usuario_id, Sessao.revogado_em.is_(None))
        .values(revogado_em=at, revogado_motivo=motivo)
    )
    sessao.flush()
    return int(cast("CursorResult[Any]", result).rowcount or 0)
