"""Data access for each member's e-mail choice (SPEC-0008 AC-0008-07). No business rule here."""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.notificacao import PreferenciaEmail


def of(session: Session, usuario_id: uuid.UUID) -> PreferenciaEmail | None:
    """One member's choice, or None when they never chose."""
    return session.get(PreferenciaEmail, usuario_id)


def of_members(
    session: Session, usuario_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, PreferenciaEmail]:
    """These members' choices, keyed by member; one who never chose is absent."""
    if not usuario_ids:
        return {}
    return {
        p.usuario_id: p
        for p in session.scalars(
            select(PreferenciaEmail).where(PreferenciaEmail.usuario_id.in_(list(usuario_ids)))
        )
    }


def save(
    session: Session,
    *,
    usuario_id: uuid.UUID,
    frequencia: str,
    dia_semana: int,
    at: datetime.datetime,
) -> None:
    """Write a member's choice, keeping when their last summary went out."""
    session.execute(
        insert(PreferenciaEmail)
        .values(
            usuario_id=usuario_id, frequencia=frequencia, dia_semana=dia_semana, atualizada_em=at
        )
        .on_conflict_do_update(
            index_elements=[PreferenciaEmail.usuario_id],
            set_={"frequencia": frequencia, "dia_semana": dia_semana, "atualizada_em": at},
        )
    )


def mark_sent(
    session: Session,
    *,
    usuario_id: uuid.UUID,
    at: datetime.datetime,
    frequencia: str,
    dia_semana: int,
) -> None:
    """Record a member's summary sent; a member who never chose gets the default row."""
    session.execute(
        insert(PreferenciaEmail)
        .values(
            usuario_id=usuario_id,
            frequencia=frequencia,
            dia_semana=dia_semana,
            ultimo_envio_em=at,
            atualizada_em=at,
        )
        .on_conflict_do_update(
            index_elements=[PreferenciaEmail.usuario_id], set_={"ultimo_envio_em": at}
        )
    )
