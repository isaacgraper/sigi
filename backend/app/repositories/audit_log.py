"""Data access for the audit trail. No business logic — see `CLAUDE.md`."""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants.historico import (
    ATA_ENTIDADE,
    ITEM_ATA_KEY,
    NOTA_EMPENHO_ENTIDADE,
    NOTA_FISCAL_ENTIDADE,
)
from app.models.audit_log import AuditLog


def insert_row(session: Session, row: AuditLog) -> None:
    """Append one row, in the caller's transaction.

    `flush` rather than leaving it to the commit: a constraint violation should
    surface where the offending call is, not at the end of the request when the
    stack no longer says who wrote it.
    """
    session.add(row)
    session.flush()


def page(
    session: Session,
    *,
    entidade_tipo: str | None,
    entidade_id: uuid.UUID | None,
    usuario_id: uuid.UUID | None,
    since: datetime.datetime | None,
    until: datetime.datetime | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[AuditLog], int]:
    """A page of rows, newest first, and how many match (AC-0007-08).

    `until` is exclusive, so a period ends at the start of the day after it.
    """
    query = select(AuditLog)
    if entidade_tipo is not None:
        query = query.where(AuditLog.entidade_tipo == entidade_tipo)
    if entidade_id is not None:
        query = query.where(AuditLog.entidade_id == entidade_id)
    if usuario_id is not None:
        query = query.where(AuditLog.user_id == usuario_id)
    if since is not None:
        query = query.where(AuditLog.ocorrido_em >= since)
    if until is not None:
        query = query.where(AuditLog.ocorrido_em < until)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(
        query.order_by(AuditLog.ocorrido_em.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
    ).all()
    return rows, total


def cycle_rows(
    session: Session,
    *,
    ata_ids: Collection[uuid.UUID],
    item_ids: Collection[uuid.UUID],
    ne_ids: Collection[uuid.UUID],
    nf_ids: Collection[uuid.UUID],
) -> Sequence[AuditLog]:
    """The rows of these ATAs, NEs and NFs, oldest first (AC-0007-07).

    An ATA row about an item is kept only when the item is one of `item_ids`;
    rows about the ATA itself carry no item key and are always kept.
    """
    clauses = []
    if ata_ids:
        data = AuditLog.dados_anteriores
        clauses.append(
            (AuditLog.entidade_tipo == ATA_ENTIDADE)
            & AuditLog.entidade_id.in_(list(ata_ids))
            & or_(
                data.is_(None),
                ~data.has_key(ITEM_ATA_KEY),
                data[ITEM_ATA_KEY].astext.in_([str(i) for i in item_ids]),
            )
        )
    if ne_ids:
        clauses.append(
            (AuditLog.entidade_tipo == NOTA_EMPENHO_ENTIDADE)
            & AuditLog.entidade_id.in_(list(ne_ids))
        )
    if nf_ids:
        clauses.append(
            (AuditLog.entidade_tipo == NOTA_FISCAL_ENTIDADE)
            & AuditLog.entidade_id.in_(list(nf_ids))
        )
    if not clauses:
        return []
    return session.scalars(
        select(AuditLog).where(or_(*clauses)).order_by(AuditLog.ocorrido_em, AuditLog.id)
    ).all()
