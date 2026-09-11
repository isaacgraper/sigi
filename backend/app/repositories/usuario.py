"""Data access for `usuario`. No business rule lives here (`CLAUDE.md`)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


def por_email(sessao: Session, email: str) -> Usuario | None:
    return sessao.scalars(
        select(Usuario).where(Usuario.email == email.strip().lower())
    ).one_or_none()


def por_id(sessao: Session, usuario_id: uuid.UUID) -> Usuario | None:
    return sessao.get(Usuario, usuario_id)
