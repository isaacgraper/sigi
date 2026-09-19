"""Data access for `usuario`. No business rule lives here (`CLAUDE.md`)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def by_email(session: Session, email: str) -> User | None:
    """Find a user by e-mail, or None."""
    return session.scalars(select(User).where(User.email == email.strip().lower())).one_or_none()


def by_id(session: Session, usuario_id: uuid.UUID) -> User | None:
    """Find a user by id, or None."""
    return session.get(User, usuario_id)
