"""Data access for `item_ata` and the aditivos de quantidade on it.

No business rule lives here (`CLAUDE.md`): which items count and what the
ceiling is are the service's.
"""

from __future__ import annotations

import decimal
import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ata import Ata, AtaAditivo
from app.models.insumo import ItemAta


def items_of(session: Session, ata_id: uuid.UUID) -> Sequence[ItemAta]:
    """The items of an ATA that were not removed."""
    return session.scalars(
        select(ItemAta).where(ItemAta.ata_id == ata_id, ItemAta.removed_at.is_(None))
    ).all()


def item_of(session: Session, ata_id: uuid.UUID, item_id: uuid.UUID) -> ItemAta | None:
    """One item of an ATA that was not removed, locked until the transaction ends."""
    return session.scalars(
        select(ItemAta)
        .where(ItemAta.id == item_id, ItemAta.ata_id == ata_id, ItemAta.removed_at.is_(None))
        .with_for_update()
    ).one_or_none()


def by_ids(session: Session, item_ids: Collection[uuid.UUID]) -> dict[uuid.UUID, ItemAta]:
    """These items, removed or not, keyed by id."""
    if not item_ids:
        return {}
    return {
        item.id: item
        for item in session.scalars(select(ItemAta).where(ItemAta.id.in_(list(item_ids))))
    }


def item_for_insumo(session: Session, ata_id: uuid.UUID, insumo_id: uuid.UUID) -> ItemAta | None:
    """The item of an ATA that holds this insumo, if it was not removed."""
    return session.scalars(
        select(ItemAta).where(
            ItemAta.ata_id == ata_id,
            ItemAta.insumo_id == insumo_id,
            ItemAta.removed_at.is_(None),
        )
    ).one_or_none()


def add_item(session: Session, item: ItemAta) -> ItemAta:
    """Insert an item and flush it."""
    session.add(item)
    session.flush()
    return item


def aditivos_de_quantidade(
    session: Session, item_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, decimal.Decimal]:
    """The total of the aditivos de quantidade of each item, keyed by item."""
    if not item_ids:
        return {}
    rows = session.execute(
        select(AtaAditivo.item_ata_id, func.sum(AtaAditivo.quantidade_acrescimo))
        .where(AtaAditivo.item_ata_id.in_(list(item_ids)), AtaAditivo.kind == "quantidade")
        .group_by(AtaAditivo.item_ata_id)
    ).all()
    return {item_id: decimal.Decimal(total) for item_id, total in rows if item_id is not None}


def atas_of_insumo(session: Session, insumo_id: uuid.UUID) -> Sequence[tuple[ItemAta, Ata]]:
    """The items holding an insumo, not removed, with their ATA, newest ATA first."""
    return session.execute(
        select(ItemAta, Ata)
        .join(Ata, Ata.id == ItemAta.ata_id)
        .where(ItemAta.insumo_id == insumo_id, ItemAta.removed_at.is_(None))
        .order_by(Ata.criado_em.desc(), Ata.id)
    ).all()  # type: ignore[return-value]
