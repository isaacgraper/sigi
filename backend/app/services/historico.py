"""Reading the audit trail: the history and the cycle of an insumo (SPEC-0007)."""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.constants import LOCAL_TIMEZONE
from app.constants.historico import (
    ATA_ENTIDADE,
    ENTIDADE_SEM_TIPO,
    ENTIDADE_TIPOS,
    ETAPA_ITEM_ATA,
    ETAPA_RANK,
    ITEM_ATA_KEY,
    PERIODO_INVERTIDO,
    TIPO_DESCONHECIDO,
)
from app.models.audit_log import AuditLog
from app.models.insumo import Insumo
from app.models.user import User
from app.repositories import audit_log as repo
from app.repositories import insumo as repo_insumo
from app.repositories import item_ata as repo_item
from app.repositories import nota_empenho as repo_ne
from app.repositories import nota_fiscal as repo_nf
from app.services.errors import InsumoNotFound, InvalidData
from app.services.insumos import scope_of, visible


@dataclass(frozen=True)
class HistoryPage:
    """A page of history rows and how many match the filters."""

    rows: Sequence[AuditLog]
    total: int


@dataclass(frozen=True)
class CycleEvent:
    """One row of an insumo's cycle, with the stage it belongs to."""

    etapa: str
    row: AuditLog


@dataclass(frozen=True)
class Cycle:
    """The insumo and its events, oldest first."""

    insumo: Insumo
    events: Sequence[CycleEvent]


def _start_of(day: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(day, datetime.time.min, LOCAL_TIMEZONE)


def list_history(
    session: Session,
    *,
    entidade_tipo: str | None,
    entidade_id: uuid.UUID | None,
    usuario_id: uuid.UUID | None,
    de: datetime.date | None,
    ate: datetime.date | None,
    page: int,
    size: int,
) -> HistoryPage:
    """The history filtered, newest first (AC-0007-08).

    A period is whole days in America/Sao_Paulo, `ate` included.
    """
    fields: dict[str, str] = {}
    if de is not None and ate is not None and de > ate:
        fields["de"] = PERIODO_INVERTIDO
    if entidade_id is not None and entidade_tipo is None:
        fields["entidade_tipo"] = ENTIDADE_SEM_TIPO
    if entidade_tipo is not None and entidade_tipo not in ENTIDADE_TIPOS:
        fields["entidade_tipo"] = TIPO_DESCONHECIDO
    if fields:
        raise InvalidData(fields)
    rows, total = repo.page(
        session,
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        usuario_id=usuario_id,
        since=_start_of(de) if de is not None else None,
        until=_start_of(ate + datetime.timedelta(days=1)) if ate is not None else None,
        offset=(page - 1) * size,
        limit=size,
    )
    return HistoryPage(rows=rows, total=total)


def _etapa(row: AuditLog) -> str:
    if (
        row.entidade_tipo == ATA_ENTIDADE
        and row.dados_anteriores
        and ITEM_ATA_KEY in row.dados_anteriores
    ):
        return ETAPA_ITEM_ATA
    return row.entidade_tipo


def cycle(session: Session, insumo_id: uuid.UUID, *, actor: User) -> Cycle:
    """The ATAs, items, NEs and NFs of an insumo, in the order of the cycle (AC-0007-07).

    Outside the servidor's grupos the insumo does not exist (RN07, AC-0003-29).
    """
    insumo = repo_insumo.insumo_by_id(session, insumo_id)
    if insumo is None or not visible(scope_of(session, actor), insumo):
        raise InsumoNotFound()
    items = repo_item.all_of_insumo(session, insumo.id)
    item_ids = [item.id for item in items]
    ne_ids = repo_ne.ids_with_items(session, item_ids)
    rows = repo.cycle_rows(
        session,
        ata_ids={item.ata_id for item in items},
        item_ids=item_ids,
        ne_ids=ne_ids,
        nf_ids=repo_nf.ids_of_nes(session, ne_ids),
    )
    events = [CycleEvent(etapa=_etapa(row), row=row) for row in rows]
    events.sort(key=lambda e: (e.row.ocorrido_em, ETAPA_RANK.get(e.etapa, len(ETAPA_RANK))))
    return Cycle(insumo=insumo, events=events)
