"""Data access for `sessao_familia` and `sessao`."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import Session

from app.models.user_session import SessionFamily, UserSession


def create_family(session: Session, user_id: uuid.UUID) -> uuid.UUID:
    """Open a session family for one user, and return its id."""
    family = uuid.uuid4()
    session.add(SessionFamily(family=family, user_id=user_id))
    session.flush()
    return family


def create(
    session: Session,
    *,
    user_id: uuid.UUID,
    family: uuid.UUID,
    generation: int,
    token_hash: bytes,
    expires_at: datetime.datetime,
) -> UserSession:
    """Insert one session row of a family, storing only the token HMAC."""
    row = UserSession(
        user_id=user_id,
        family=family,
        generation=generation,
        refresh_token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(row)
    session.flush()
    return row


def by_hash(session: Session, token_hash: bytes) -> UserSession | None:
    """Find a session by its token hash — **including revoked ones**.

    The predicate is load-bearing: filtering `revogado_em IS NULL` here would
    turn a replay into "not found", which is a plain 401 with no family
    revocation, leaving AC-0001-07 unmet behind a test that still sees its 401.
    """
    return session.scalars(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash)
    ).one_or_none()


def next_generation(session: Session, family: uuid.UUID) -> int:
    """The next generation number in a family, counting from one."""
    current = session.scalar(
        select(func.max(UserSession.generation)).where(UserSession.family == family)
    )
    return int(current or 0) + 1


def revoke_family(
    session: Session, family: uuid.UUID, *, reason: str, at: datetime.datetime
) -> int:
    """Revoke every live session descended from one login. Returns how many."""
    result = session.execute(
        update(UserSession)
        .where(UserSession.family == family, UserSession.revogado_em.is_(None))
        .values(revogado_em=at, revogado_motivo=reason)
    )
    session.execute(
        update(SessionFamily)
        .where(SessionFamily.family == family, SessionFamily.revogada_em.is_(None))
        .values(revogada_em=at)
    )
    session.flush()
    return int(cast("CursorResult[Any]", result).rowcount or 0)


def revoke_for_usuario(
    session: Session, user_id: uuid.UUID, *, reason: str, at: datetime.datetime
) -> int:
    """Revoke every live session of one user. Returns how many."""
    result = session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revogado_em.is_(None))
        .values(revogado_em=at, revogado_motivo=reason)
    )
    session.flush()
    return int(cast("CursorResult[Any]", result).rowcount or 0)
