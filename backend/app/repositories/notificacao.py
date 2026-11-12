"""Data access for the ATA notices (SPEC-0008). No business rule lives here."""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.ata import Ata
from app.models.notificacao import Notificacao, NotificacaoLeitura


def raise_once(
    session: Session,
    *,
    ata_id: uuid.UUID,
    motivo: str,
    chave: str,
    dados: dict[str, Any],
    at: datetime.datetime,
) -> Notificacao | None:
    """Insert a notice unless one exists for this ATA, reason and key; the new one or None."""
    created = session.scalar(
        insert(Notificacao)
        .values(ata_id=ata_id, motivo=motivo, chave=chave, dados=dados, criada_em=at)
        .on_conflict_do_nothing(constraint="uq_notificacao_ata_motivo_chave")
        .returning(Notificacao.id)
    )
    return session.get(Notificacao, created) if created is not None else None


def page(
    session: Session, *, usuario_id: uuid.UUID, offset: int, limit: int
) -> tuple[Sequence[tuple[Notificacao, Ata, datetime.datetime | None]], int, int]:
    """A page of notices newest first, each with its ATA and when this member read it.

    Also the total and how many this member has not read.
    """
    read = (
        select(NotificacaoLeitura.lida_em)
        .where(
            NotificacaoLeitura.notificacao_id == Notificacao.id,
            NotificacaoLeitura.usuario_id == usuario_id,
        )
        .correlate(Notificacao)
        .scalar_subquery()
    )
    rows = session.execute(
        select(Notificacao, Ata, read)
        .join(Ata, Ata.id == Notificacao.ata_id)
        .order_by(Notificacao.criada_em.desc(), Notificacao.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    total = session.scalar(select(func.count()).select_from(Notificacao)) or 0
    unread = (
        session.scalar(
            select(func.count())
            .select_from(Notificacao)
            .where(
                ~select(NotificacaoLeitura.notificacao_id)
                .where(
                    NotificacaoLeitura.notificacao_id == Notificacao.id,
                    NotificacaoLeitura.usuario_id == usuario_id,
                )
                .exists()
            )
        )
        or 0
    )
    return [(row[0], row[1], row[2]) for row in rows], int(total), int(unread)


def by_id(session: Session, notificacao_id: uuid.UUID) -> Notificacao | None:
    """One notice, or None."""
    return session.get(Notificacao, notificacao_id)


def mark_read(
    session: Session,
    *,
    notificacao_ids: Collection[uuid.UUID],
    usuario_id: uuid.UUID,
    at: datetime.datetime,
) -> int:
    """Record that this member read these notices; one already read is left as it was."""
    if not notificacao_ids:
        return 0
    result = session.execute(
        insert(NotificacaoLeitura)
        .values(
            [
                {"notificacao_id": n, "usuario_id": usuario_id, "lida_em": at}
                for n in notificacao_ids
            ]
        )
        .on_conflict_do_nothing()
        .returning(NotificacaoLeitura.notificacao_id)
    )
    return len(result.all())


def unread_ids(session: Session, *, usuario_id: uuid.UUID) -> Sequence[uuid.UUID]:
    """Every notice this member has not read."""
    return session.scalars(
        select(Notificacao.id).where(
            ~select(NotificacaoLeitura.notificacao_id)
            .where(
                NotificacaoLeitura.notificacao_id == Notificacao.id,
                NotificacaoLeitura.usuario_id == usuario_id,
            )
            .exists()
        )
    ).all()
