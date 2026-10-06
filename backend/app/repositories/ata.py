"""Data access for `ata`, `fornecedor`, `ata_aditivo` and `ata_reajuste`.

No business rule lives here (`CLAUDE.md`): the service decides what a window or a
status means and passes plain dates and values in.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ata import Ata, AtaAditivo, AtaReajuste
from app.models.fornecedor import Fornecedor


def fornecedor_by_cnpj(session: Session, cnpj: str) -> Fornecedor | None:
    """Find a fornecedor by its 14 digits, or None."""
    return session.scalars(select(Fornecedor).where(Fornecedor.cnpj == cnpj)).one_or_none()


def create_fornecedor(session: Session, *, cnpj: str, legal_name: str) -> Fornecedor:
    """Insert a fornecedor and flush it, so the caller has its id."""
    fornecedor = Fornecedor(cnpj=cnpj, legal_name=legal_name)
    session.add(fornecedor)
    session.flush()
    return fornecedor


def fornecedor_by_id(session: Session, fornecedor_id: uuid.UUID) -> Fornecedor | None:
    """Find a fornecedor by id, or None."""
    return session.get(Fornecedor, fornecedor_id)


def by_number(session: Session, number: str) -> Ata | None:
    """Find an ATA by its numero, or None."""
    return session.scalars(select(Ata).where(Ata.number == number)).one_or_none()


def by_id(session: Session, ata_id: uuid.UUID) -> Ata | None:
    """Find an ATA by id, or None."""
    return session.get(Ata, ata_id)


def by_id_for_update(session: Session, ata_id: uuid.UUID) -> Ata | None:
    """Find an ATA and lock its row until the transaction ends.

    Every write to an ATA takes this first, so two gestores moving the same ATA
    at once are serialised instead of the second silently overwriting the first.
    """
    return session.scalars(select(Ata).where(Ata.id == ata_id).with_for_update()).one_or_none()


def add(session: Session, ata: Ata) -> Ata:
    """Insert an ATA and flush it."""
    session.add(ata)
    session.flush()
    return ata


def list_page(
    session: Session,
    *,
    page: int,
    size: int,
    status: str | None,
    fim_from: datetime.date | None,
    fim_to: datetime.date | None,
) -> tuple[Sequence[Ata], int]:
    """One page of ATAs, newest first, and the total that matches the filters."""
    conditions = []
    if status is not None:
        conditions.append(Ata.status == status)
    if fim_from is not None:
        conditions.append(Ata.vigencia_fim >= fim_from)
    if fim_to is not None:
        conditions.append(Ata.vigencia_fim <= fim_to)
    total = session.scalar(select(func.count()).select_from(Ata).where(*conditions)) or 0
    rows = session.scalars(
        select(Ata)
        .where(*conditions)
        # Deterministic, so page 2 never repeats a row from page 1.
        .order_by(Ata.criado_em.desc(), Ata.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return rows, int(total)


def aditivos_of(session: Session, ata_id: uuid.UUID) -> Sequence[AtaAditivo]:
    """The aditivos of an ATA, oldest first."""
    return session.scalars(
        select(AtaAditivo).where(AtaAditivo.ata_id == ata_id).order_by(AtaAditivo.criado_em)
    ).all()


def reajustes_of(session: Session, ata_id: uuid.UUID) -> Sequence[AtaReajuste]:
    """The reajuste requests of an ATA, oldest first."""
    return session.scalars(
        select(AtaReajuste).where(AtaReajuste.ata_id == ata_id).order_by(AtaReajuste.criado_em)
    ).all()


def sum_aditivos_de_valor(session: Session, ata_id: uuid.UUID) -> decimal.Decimal:
    """The total of the aditivos of value of an ATA."""
    total = session.scalar(
        select(func.coalesce(func.sum(AtaAditivo.valor_acrescimo), 0)).where(
            AtaAditivo.ata_id == ata_id, AtaAditivo.kind == "valor"
        )
    )
    return decimal.Decimal(total or 0)


def add_aditivo(session: Session, aditivo: AtaAditivo) -> AtaAditivo:
    """Insert an aditivo and flush it."""
    session.add(aditivo)
    session.flush()
    return aditivo


def add_reajuste(session: Session, reajuste: AtaReajuste) -> AtaReajuste:
    """Insert a reajuste request and flush it."""
    session.add(reajuste)
    session.flush()
    return reajuste


def renewal_alert(session: Session, *, until: datetime.date) -> Sequence[Ata]:
    """Vigente ATAs ending on or before `until`, with no aditivo de prazo (RF19).

    Ordered by the end date, which is the same order as days remaining ascending.
    An ATA already past its end and still `vigente` is included on purpose: it is
    the one most in need of the alert.
    """
    has_prazo = (
        select(AtaAditivo.id)
        .where(AtaAditivo.ata_id == Ata.id, AtaAditivo.kind == "prazo")
        .exists()
    )
    return session.scalars(
        select(Ata)
        .where(Ata.status == "vigente", Ata.vigencia_fim <= until, ~has_prazo)
        .order_by(Ata.vigencia_fim, Ata.id)
    ).all()


def reajuste_alert(session: Session, *, until: datetime.date) -> Sequence[Ata]:
    """Vigente ATAs whose reajuste date is on or before `until`, with no request.

    The reajuste date is the data do orçamento plus one calendar year. PostgreSQL
    moves 29/02 to 28/02 for it, which is what AC-0002-18 asks for.
    """
    reajuste_date = Ata.budget_date + func.make_interval(1)
    has_request = select(AtaReajuste.id).where(AtaReajuste.ata_id == Ata.id).exists()
    return session.scalars(
        select(Ata)
        .where(Ata.status == "vigente", reajuste_date <= until, ~has_request)
        .order_by(reajuste_date, Ata.id)
    ).all()
