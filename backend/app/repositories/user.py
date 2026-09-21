"""Data access for `usuario`. No business rule lives here (`CLAUDE.md`)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.user import User


def by_email(session: Session, email: str) -> User | None:
    """Find a user by e-mail, or None."""
    return session.scalars(select(User).where(User.email == email.strip().lower())).one_or_none()


def by_id(session: Session, usuario_id: uuid.UUID) -> User | None:
    """Find a user by id, or None."""
    return session.get(User, usuario_id)


def by_oidc_subject(session: Session, subject: str) -> User | None:
    """Find a user by the provider's stable subject, or None."""
    return session.scalars(select(User).where(User.oidc_subject == subject)).one_or_none()


def create(
    session: Session,
    *,
    email: str,
    role: str,
    nome: str | None = None,
) -> User:
    """Insert a `pendente` account and flush it, so the caller has its id."""
    user = User(
        email=email.strip().lower(),
        nome=nome,
        role=role,
        status="pendente",
    )
    session.add(user)
    session.flush()
    return user


# Arbitrary but fixed: an advisory lock key is just a number both sides agree
# on. Named so that a second guard never picks the same one by accident.
GESTOR_LOCK = 0x5163_0001


def list_page(session: Session, *, page: int, size: int) -> Sequence[User]:
    """One page of members, newest first."""
    return session.scalars(
        select(User)
        # Deterministic, so page 2 does not repeat a row from page 1.
        # `criado_em` alone is not unique enough: two invitations in the same
        # millisecond would order arbitrarily between queries.
        .order_by(User.criado_em.desc(), User.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()


def count(session: Session) -> int:
    """How many members exist, in any status."""
    return int(session.scalar(select(func.count()).select_from(User)) or 0)


def lock_gestores(session: Session) -> None:
    """Serialise every decision that could remove the last active gestor.

    "At least one active gestor exists" is an aggregate across rows, and
    snapshot isolation does not stop two concurrent transactions from each
    observing two gestores and both committing: classic write skew. The
    database trigger catches it with `FOR UPDATE`, but measured over 40 runs the
    loser surfaces as a deadlock (`40P01`) 39 times out of 40 rather than the
    criterion's own error, so the service takes this lock first and the trigger
    stays the backstop it should be.

    A transaction-scoped advisory lock: released at commit or rollback, with no
    row to hold and no table to contend on.
    """
    session.execute(text("SELECT pg_advisory_xact_lock(:chave)"), {"chave": GESTOR_LOCK})


def count_active_gestores(session: Session, *, excluding: uuid.UUID | None = None) -> int:
    """How many gestores are `ativo`, optionally ignoring one of them."""
    query = (
        select(func.count()).select_from(User).where(User.role == "gestor", User.status == "ativo")
    )
    if excluding is not None:
        query = query.where(User.id != excluding)
    return int(session.scalar(query) or 0)
