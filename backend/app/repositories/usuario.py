"""Data access for `usuario`. No business rule lives here (`CLAUDE.md`)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


def by_email(sessao: Session, email: str) -> Usuario | None:
    """Find a usuario by e-mail, or None."""
    return sessao.scalars(
        select(Usuario).where(Usuario.email == email.strip().lower())
    ).one_or_none()


def by_id(sessao: Session, usuario_id: uuid.UUID) -> Usuario | None:
    """Find a usuario by id, or None."""
    return sessao.get(Usuario, usuario_id)
