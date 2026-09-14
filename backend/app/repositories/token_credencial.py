"""Data access for `token_credencial`. No business rule lives here."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.models.token_credencial import TokenCredencial


def criar(
    sessao: Session,
    *,
    usuario_id: uuid.UUID,
    tipo: str,
    token_hash: bytes,
    expira_em: datetime.datetime,
    criado_por: uuid.UUID | None,
) -> TokenCredencial:
    linha = TokenCredencial(
        usuario_id=usuario_id,
        tipo=tipo,
        token_hash=token_hash,
        expira_em=expira_em,
        criado_por=criado_por,
    )
    sessao.add(linha)
    sessao.flush()
    return linha


def por_hash(sessao: Session, token_hash: bytes) -> TokenCredencial | None:
    """Find a grant by its hash — **including spent and cancelled ones**.

    The predicate is load-bearing, the same way it is in `sessao.por_hash`:
    filtering the spent ones out here would turn "already redeemed" into "not
    found", and AC-0001-25 wants those two answered differently.
    """
    return sessao.scalars(
        select(TokenCredencial).where(TokenCredencial.token_hash == token_hash)
    ).one_or_none()


def marcar_utilizado(
    sessao: Session, token: TokenCredencial, *, momento: datetime.datetime
) -> None:
    token.utilizado_em = momento
    sessao.flush()


def cancelar_abertos(
    sessao: Session, *, usuario_id: uuid.UUID, tipo: str, momento: datetime.datetime
) -> int:
    """Close any outstanding grant of this type for this usuario.

    `ux_token_credencial_aberto` allows exactly one open grant per usuario per
    type, so re-issuing means cancelling first. `cancelado_em` exists for this:
    an expired-but-unredeemed grant still matches `utilizado_em IS NULL`, and
    `now()` cannot appear in an index predicate.
    """
    resultado = sessao.execute(
        update(TokenCredencial)
        .where(
            TokenCredencial.usuario_id == usuario_id,
            TokenCredencial.tipo == tipo,
            TokenCredencial.utilizado_em.is_(None),
            TokenCredencial.cancelado_em.is_(None),
        )
        .values(cancelado_em=momento)
    )
    sessao.flush()
    return int(cast("CursorResult[Any]", resultado).rowcount or 0)
