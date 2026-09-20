"""Data access for `token_credencial`. No business rule lives here."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.models.credential_token import CredentialToken


def create(
    session: Session,
    *,
    usuario_id: uuid.UUID,
    tipo: str,
    token_hash: bytes,
    expira_em: datetime.datetime,
    criado_por: uuid.UUID | None,
) -> CredentialToken:
    """Insert a grant row and flush it, so the caller has its id."""
    row = CredentialToken(
        usuario_id=usuario_id,
        tipo=tipo,
        token_hash=token_hash,
        expira_em=expira_em,
        criado_por=criado_por,
    )
    session.add(row)
    session.flush()
    return row


def by_hash(session: Session, token_hash: bytes) -> CredentialToken | None:
    """Find a grant by its hash, **including spent and cancelled ones**.

    The absent predicate is load-bearing, the same way it is in the session
    repository: filtering the spent ones out here would turn "already redeemed"
    into "not found", and AC-0001-25 wants those two answered differently.
    """
    return session.scalars(
        select(CredentialToken).where(CredentialToken.token_hash == token_hash)
    ).one_or_none()


def mark_used(session: Session, token: CredentialToken, *, at: datetime.datetime) -> None:
    """Spend the grant."""
    token.utilizado_em = at
    session.flush()


def cancel_open(
    session: Session, *, usuario_id: uuid.UUID, tipo: str, at: datetime.datetime
) -> int:
    """Close any outstanding grant of this type for this usuario.

    `ux_token_credencial_aberto` allows exactly one open grant per usuario per
    type, so re-issuing means cancelling first. `cancelado_em` exists for this:
    an expired but unredeemed grant still matches `utilizado_em IS NULL`, and
    `now()` cannot appear in an index predicate.
    """
    result = session.execute(
        update(CredentialToken)
        .where(
            CredentialToken.usuario_id == usuario_id,
            CredentialToken.tipo == tipo,
            CredentialToken.utilizado_em.is_(None),
            CredentialToken.cancelado_em.is_(None),
        )
        .values(cancelado_em=at)
    )
    session.flush()
    return int(cast("CursorResult[Any]", result).rowcount or 0)
