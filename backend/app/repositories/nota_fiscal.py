"""Data access for `nota_fiscal` and `item_nota_fiscal`.

No business rule lives here (`CLAUDE.md`): which statuses count against the
empenho is the service's, passed in as plain sets.
"""

from __future__ import annotations

import decimal
import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.insumo import Insumo, ItemAta
from app.models.nota_empenho import ItemNotaEmpenho
from app.models.nota_fiscal import ItemNotaFiscal, NotaFiscal


def add(session: Session, nf: NotaFiscal) -> NotaFiscal:
    """Insert an NF and flush it, so the caller has its id."""
    session.add(nf)
    session.flush()
    return nf


def by_id(session: Session, nf_id: uuid.UUID) -> NotaFiscal | None:
    """Find an NF by id, or None."""
    return session.get(NotaFiscal, nf_id)


def by_id_for_update(session: Session, nf_id: uuid.UUID) -> NotaFiscal | None:
    """Find an NF and lock its row until the transaction ends."""
    return session.scalars(
        select(NotaFiscal).where(NotaFiscal.id == nf_id).with_for_update()
    ).one_or_none()


def by_numero(session: Session, numero: str, fornecedor_id: uuid.UUID) -> NotaFiscal | None:
    """The NF with this número of this fornecedor, or None."""
    return session.scalars(
        select(NotaFiscal).where(
            NotaFiscal.numero == numero, NotaFiscal.fornecedor_id == fornecedor_id
        )
    ).one_or_none()


def lines(
    session: Session, nf_ids: Collection[uuid.UUID]
) -> Sequence[tuple[ItemNotaFiscal, ItemNotaEmpenho, ItemAta, Insumo]]:
    """The lines of these NFs with the NE line, the item and the insumo, in insumo order."""
    if not nf_ids:
        return []
    return session.execute(  # type: ignore[return-value]
        select(ItemNotaFiscal, ItemNotaEmpenho, ItemAta, Insumo)
        .join(ItemNotaEmpenho, ItemNotaEmpenho.id == ItemNotaFiscal.item_nota_empenho_id)
        .join(ItemAta, ItemAta.id == ItemNotaEmpenho.item_ata_id)
        .join(Insumo, Insumo.id == ItemAta.insumo_id)
        .where(ItemNotaFiscal.nota_fiscal_id.in_(list(nf_ids)))
        .order_by(Insumo.description, ItemNotaFiscal.id)
    ).all()


def replace_lines(session: Session, nf_id: uuid.UUID, new: Sequence[ItemNotaFiscal]) -> None:
    """Delete the lines of an NF and insert these in their place."""
    session.execute(delete(ItemNotaFiscal).where(ItemNotaFiscal.nota_fiscal_id == nf_id))
    session.add_all(new)
    session.flush()


def page(
    session: Session,
    *,
    status: str | None,
    nota_empenho_id: uuid.UUID | None,
    quarentena: bool | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[NotaFiscal], int]:
    """A page of NFs, newest first, and how many match."""
    query = select(NotaFiscal)
    if status is not None:
        query = query.where(NotaFiscal.status == status)
    if nota_empenho_id is not None:
        query = query.where(NotaFiscal.nota_empenho_id == nota_empenho_id)
    if quarentena is not None:
        query = query.where(NotaFiscal.quarentena == quarentena)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(
        query.order_by(NotaFiscal.criado_em.desc(), NotaFiscal.id).offset(offset).limit(limit)
    ).all()
    return rows, total


def value_of_ne(
    session: Session,
    ne_id: uuid.UUID,
    statuses: Collection[str],
    *,
    excluding: uuid.UUID | None,
) -> decimal.Decimal:
    """Σ `valor` of the NFs of an NE in these statuses, leaving one NF out."""
    query = select(func.coalesce(func.sum(NotaFiscal.value), 0)).where(
        NotaFiscal.nota_empenho_id == ne_id, NotaFiscal.status.in_(list(statuses))
    )
    if excluding is not None:
        query = query.where(NotaFiscal.id != excluding)
    return decimal.Decimal(session.scalar(query) or 0)


def quantity_by_line(
    session: Session,
    line_ids: Collection[uuid.UUID],
    statuses: Collection[str],
    *,
    excluding: uuid.UUID | None = None,
) -> dict[tuple[uuid.UUID, bool], decimal.Decimal]:
    """Σ `quantidade` per NE line and quarantine flag, of the NFs in these statuses."""
    if not line_ids:
        return {}
    query = (
        select(
            ItemNotaFiscal.item_nota_empenho_id,
            NotaFiscal.quarentena,
            func.sum(ItemNotaFiscal.quantity),
        )
        .join(NotaFiscal, NotaFiscal.id == ItemNotaFiscal.nota_fiscal_id)
        .where(
            ItemNotaFiscal.item_nota_empenho_id.in_(list(line_ids)),
            NotaFiscal.status.in_(list(statuses)),
        )
        .group_by(ItemNotaFiscal.item_nota_empenho_id, NotaFiscal.quarentena)
    )
    if excluding is not None:
        query = query.where(NotaFiscal.id != excluding)
    rows = session.execute(query).all()
    return {(line, held): decimal.Decimal(total) for line, held, total in rows}


def ids_of_nes(session: Session, ne_ids: Collection[uuid.UUID]) -> Sequence[uuid.UUID]:
    """The NFs launched against these NEs (AC-0007-07)."""
    if not ne_ids:
        return []
    return session.scalars(
        select(NotaFiscal.id).where(NotaFiscal.nota_empenho_id.in_(list(ne_ids)))
    ).all()
