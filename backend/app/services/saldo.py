"""Saldo of an ATA, in value and per item in quantity (SPEC-0006).

A pure function of the NE ledger, summed on every read. There is no saldo
column and nothing here writes (ADR-0003): the entity's own sheet keeps `SALDO`
beside `SALDO CALCULADO` and disagrees with itself in 32,5% of rows.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.constants.notas_empenho import ALTO_CONSUMO, COMMITTED, RESERVING, ZERO
from app.models.ata import Ata
from app.models.insumo import Insumo, ItemAta
from app.repositories import ata as ata_repo
from app.repositories import insumo as insumo_repo
from app.repositories import item_ata as item_repo
from app.repositories import nota_empenho as ne_repo
from app.services.errors import AtaNotFound


@dataclass(frozen=True)
class SaldoAta:
    """The value saldo of an ATA at an instant (AC-0006-01 to -04, -09)."""

    valor_contratado: decimal.Decimal
    valor_reservado: decimal.Decimal
    valor_empenhado: decimal.Decimal
    saldo_disponivel: decimal.Decimal
    comprometimento_percentual: decimal.Decimal
    alto_consumo: bool
    calculado_em: datetime.datetime


@dataclass(frozen=True)
class SaldoItem:
    """The quantity saldo of one item (AC-0006-10, -11, -13)."""

    item: ItemAta
    insumo: Insumo
    quantidade_contratada: decimal.Decimal
    quantidade_reservada: decimal.Decimal
    quantidade_empenhada: decimal.Decimal

    @property
    def quantidade_disponivel(self) -> decimal.Decimal:
        """What can still be reserved of this item."""
        return self.quantidade_contratada - self.quantidade_reservada - self.quantidade_empenhada

    @property
    def esgotado(self) -> bool:
        """Whether nothing is left of it, whatever the ATA's money says (AC-0006-11)."""
        return self.quantidade_disponivel <= ZERO


def saldo_da_ata(session: Session, ata_id: uuid.UUID, *, at: datetime.datetime) -> SaldoAta:
    """Sum an ATA's saldo now, or refuse an unknown ATA with 404 (AC-0006-16)."""
    ata = ata_repo.by_id(session, ata_id)
    if ata is None:
        raise AtaNotFound()
    return compute(session, ata, at=at)


def compute(session: Session, ata: Ata, *, at: datetime.datetime) -> SaldoAta:
    """The value saldo of an ATA the caller already holds, locked or not."""
    contratado = ata.total_value + ata_repo.sum_aditivos_de_valor(session, ata.id)
    by_status = ne_repo.value_by_status(session, ata.id)
    reservado = sum((by_status.get(s, ZERO) for s in RESERVING), ZERO)
    empenhado = sum((by_status.get(s, ZERO) for s in COMMITTED), ZERO)
    percentual = (reservado + empenhado) * 100 / contratado if contratado else ZERO
    return SaldoAta(
        valor_contratado=contratado,
        valor_reservado=reservado,
        valor_empenhado=empenhado,
        saldo_disponivel=contratado - reservado - empenhado,
        comprometimento_percentual=percentual.quantize(
            decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP
        ),
        alto_consumo=percentual >= ALTO_CONSUMO,
        calculado_em=at,
    )


def saldo_dos_itens(
    session: Session, ata_id: uuid.UUID, *, at: datetime.datetime
) -> tuple[list[SaldoItem], datetime.datetime]:
    """The quantity saldo of every item of an ATA, or 404 for an unknown ATA."""
    if ata_repo.by_id(session, ata_id) is None:
        raise AtaNotFound()
    items = list(item_repo.items_of(session, ata_id))
    return items_saldo(session, items), at


def items_saldo(session: Session, items: list[ItemAta]) -> list[SaldoItem]:
    """The quantity saldo of these items, in insumo order."""
    ids = [item.id for item in items]
    aditivos = item_repo.aditivos_de_quantidade(session, ids)
    by_status = ne_repo.quantity_by_item_and_status(session, ids)
    insumos = insumo_repo.insumos_by_id(session, [item.insumo_id for item in items])
    result = [
        SaldoItem(
            item=item,
            insumo=insumos[item.insumo_id],
            quantidade_contratada=item.quantity + aditivos.get(item.id, ZERO),
            quantidade_reservada=sum((by_status.get((item.id, s), ZERO) for s in RESERVING), ZERO),
            quantidade_empenhada=sum((by_status.get((item.id, s), ZERO) for s in COMMITTED), ZERO),
        )
        for item in items
    ]
    return sorted(result, key=lambda s: s.insumo.description)
