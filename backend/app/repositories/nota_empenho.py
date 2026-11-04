"""Data access for `nota_empenho` and `item_nota_empenho`.

No business rule lives here (`CLAUDE.md`): which statuses reserve, commit or
lock is the service's, passed in as plain sets.
"""

from __future__ import annotations

import decimal
import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.insumo import Insumo, ItemAta
from app.models.nota_empenho import ItemNotaEmpenho, NotaEmpenho


def add(session: Session, ne: NotaEmpenho) -> NotaEmpenho:
    """Insert an NE and flush it, so the caller has its id."""
    session.add(ne)
    session.flush()
    return ne


def by_id(session: Session, ne_id: uuid.UUID) -> NotaEmpenho | None:
    """Find an NE by id, or None."""
    return session.get(NotaEmpenho, ne_id)


def by_id_for_update(session: Session, ne_id: uuid.UUID) -> NotaEmpenho | None:
    """Find an NE and lock its row until the transaction ends."""
    return session.scalars(
        select(NotaEmpenho).where(NotaEmpenho.id == ne_id).with_for_update()
    ).one_or_none()


def lines(
    session: Session, ne_ids: Collection[uuid.UUID]
) -> Sequence[tuple[ItemNotaEmpenho, ItemAta, Insumo]]:
    """The lines of these NEs with the item and the insumo each commits, in insumo order."""
    if not ne_ids:
        return []
    return session.execute(  # type: ignore[return-value]
        select(ItemNotaEmpenho, ItemAta, Insumo)
        .join(ItemAta, ItemAta.id == ItemNotaEmpenho.item_ata_id)
        .join(Insumo, Insumo.id == ItemAta.insumo_id)
        .where(ItemNotaEmpenho.nota_empenho_id.in_(list(ne_ids)))
        .order_by(Insumo.description, ItemNotaEmpenho.id)
    ).all()


def replace_lines(session: Session, ne_id: uuid.UUID, new: Sequence[ItemNotaEmpenho]) -> None:
    """Delete the lines of an NE and insert these in their place."""
    session.execute(delete(ItemNotaEmpenho).where(ItemNotaEmpenho.nota_empenho_id == ne_id))
    session.add_all(new)
    session.flush()


def page(
    session: Session,
    *,
    status: str | None,
    ata_id: uuid.UUID | None,
    processo_sei: str | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[NotaEmpenho], int]:
    """A page of NEs, newest first, and how many match."""
    query = select(NotaEmpenho)
    if status is not None:
        query = query.where(NotaEmpenho.status == status)
    if ata_id is not None:
        query = query.where(NotaEmpenho.ata_id == ata_id)
    if processo_sei is not None:
        query = query.where(NotaEmpenho.processo_sei.contains(processo_sei))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(
        query.order_by(NotaEmpenho.criado_em.desc(), NotaEmpenho.id).offset(offset).limit(limit)
    ).all()
    return rows, total


def count_by_status(session: Session) -> dict[str, int]:
    """How many NEs are in each status."""
    rows = session.execute(
        select(NotaEmpenho.status, func.count()).group_by(NotaEmpenho.status)
    ).all()
    return {status: count for status, count in rows}


def of_ata_in(
    session: Session, ata_id: uuid.UUID, statuses: Collection[str]
) -> Sequence[NotaEmpenho]:
    """The NEs of an ATA in these statuses, oldest first."""
    return session.scalars(
        select(NotaEmpenho)
        .where(NotaEmpenho.ata_id == ata_id, NotaEmpenho.status.in_(list(statuses)))
        .order_by(NotaEmpenho.criado_em, NotaEmpenho.id)
    ).all()


def item_referenced_in(session: Session, item_ata_id: uuid.UUID, statuses: Collection[str]) -> bool:
    """Whether an NE in these statuses carries this item."""
    found = session.scalar(
        select(func.count())
        .select_from(ItemNotaEmpenho)
        .join(NotaEmpenho, NotaEmpenho.id == ItemNotaEmpenho.nota_empenho_id)
        .where(
            ItemNotaEmpenho.item_ata_id == item_ata_id,
            NotaEmpenho.status.in_(list(statuses)),
        )
    )
    return bool(found)


def by_numero(session: Session, numero: str) -> NotaEmpenho | None:
    """The NE with this número, or None."""
    return session.scalars(select(NotaEmpenho).where(NotaEmpenho.numero == numero)).one_or_none()


def by_numero_pre_empenho(session: Session, numero: str) -> NotaEmpenho | None:
    """The NE with this pré-empenho número, or None."""
    return session.scalars(
        select(NotaEmpenho).where(NotaEmpenho.numero_pre_empenho == numero)
    ).one_or_none()


# ── Saldo (SPEC-0006): sums of the lines by the parent NE's status ──────────


def value_by_status(session: Session, ata_id: uuid.UUID) -> dict[str, decimal.Decimal]:
    """Σ `item_nota_empenho.valor` of an ATA's NEs, keyed by the NE's status."""
    rows = session.execute(
        select(NotaEmpenho.status, func.sum(ItemNotaEmpenho.value))
        .join(ItemNotaEmpenho, ItemNotaEmpenho.nota_empenho_id == NotaEmpenho.id)
        .where(NotaEmpenho.ata_id == ata_id)
        .group_by(NotaEmpenho.status)
    ).all()
    return {status: decimal.Decimal(total) for status, total in rows}


def quantity_by_item_and_status(
    session: Session, item_ids: Collection[uuid.UUID]
) -> dict[tuple[uuid.UUID, str], decimal.Decimal]:
    """Σ `item_nota_empenho.quantidade` per item and the NE's status."""
    if not item_ids:
        return {}
    rows = session.execute(
        select(ItemNotaEmpenho.item_ata_id, NotaEmpenho.status, func.sum(ItemNotaEmpenho.quantity))
        .join(NotaEmpenho, NotaEmpenho.id == ItemNotaEmpenho.nota_empenho_id)
        .where(ItemNotaEmpenho.item_ata_id.in_(list(item_ids)))
        .group_by(ItemNotaEmpenho.item_ata_id, NotaEmpenho.status)
    ).all()
    return {(item, status): decimal.Decimal(total) for item, status, total in rows}
