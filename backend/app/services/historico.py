"""Reading the audit trail: the history and the cycle of an insumo (SPEC-0007)."""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections import defaultdict
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.constants import LOCAL_TIMEZONE
from app.constants.historico import (
    ACRESCIMO_ATTRIBUTE,
    ADITIVO_ACAO,
    ATA_ENTIDADE,
    ENTIDADE_SEM_TIPO,
    ENTIDADE_TIPOS,
    ETAPA_ITEM_ATA,
    ETAPA_RANK,
    FIELDS,
    GRUPO_MATERIAL_ENTIDADE,
    INSUMO_ENTIDADE,
    ITEM_ATA_ENTIDADE,
    ITEM_ATA_KEY,
    ITEM_LINE_KEY,
    ITEM_QUANTIDADE_KEY,
    ITENS_KEY,
    NOTA_EMPENHO_ENTIDADE,
    NOTA_FISCAL_ENTIDADE,
    PERIODO_INVERTIDO,
    STATE_KEY,
    TIPO_DESCONHECIDO,
    UNTRACKED_COLUMNS,
)
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.insumo import Insumo
from app.models.user import User
from app.repositories import ata as repo_ata
from app.repositories import audit_log as repo
from app.repositories import insumo as repo_insumo
from app.repositories import item_ata as repo_item
from app.repositories import nota_empenho as repo_ne
from app.repositories import nota_fiscal as repo_nf
from app.services.atas import jsonable
from app.services.errors import InsumoNotFound, InvalidData
from app.services.history_changes import Entry, EventChanges, details_only, walk
from app.services.insumos import scope_of, visible

# An entity a row is about: its entidade_tipo and id, an ATA item being its own.
Subject = tuple[str, uuid.UUID]


@dataclass(frozen=True)
class HistoryPage:
    """A page of history rows and how many match the filters."""

    rows: Sequence[AuditLog]
    total: int
    changes: Mapping[uuid.UUID, EventChanges]


@dataclass(frozen=True)
class CycleEvent:
    """One row of an insumo's cycle, with the stage it belongs to."""

    etapa: str
    row: AuditLog
    changes: EventChanges


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
    return HistoryPage(rows=rows, total=total, changes=changes_of(session, rows))


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
    changes = changes_of(session, rows)
    events = [CycleEvent(etapa=_etapa(row), row=row, changes=changes[row.id]) for row in rows]
    events.sort(key=lambda e: (e.row.ocorrido_em, ETAPA_RANK.get(e.etapa, len(ETAPA_RANK))))
    return Cycle(insumo=insumo, events=events)


# ── What each event changed (AC-0007-10) ────────────────────────────────────


def changes_of(session: Session, rows: Sequence[AuditLog]) -> dict[uuid.UUID, EventChanges]:
    """What each of these rows changed, before and after, keyed by row id.

    The value after is derived, never stored: every row of each entity is walked
    from the entity as it is now, so a page costs a fixed number of queries.
    """
    subjects = {row.id: _subject(row) for row in rows}
    walked = {subject for subject in subjects.values() if subject[0] in FIELDS}
    stored = {(row.entidade_tipo, row.entidade_id) for row in rows if subjects[row.id] in walked}
    history: dict[Subject, list[AuditLog]] = defaultdict(list)
    for row in repo.rows_of(session, stored):
        subject = _subject(row)
        if subject in walked:
            history[subject].append(row)
    states, acrescimos = _states(session, walked)

    result: dict[uuid.UUID, EventChanges] = {}
    for subject, subject_rows in history.items():
        entries = [
            _entry(row, acrescimos.get((subject, row.ocorrido_em)))
            if row.acao == ADITIVO_ACAO
            else _entry(row, None)
            for row in subject_rows
        ]
        result.update(walk(subject[0], entries, states.get(subject)))
    for row in rows:
        if row.id not in result:
            result[row.id] = details_only(row.entidade_tipo, _entry(row, None))
    return result


def _subject(row: AuditLog) -> Subject:
    if _etapa(row) == ETAPA_ITEM_ATA:
        assert row.dados_anteriores is not None  # _etapa read the key from it
        return ITEM_ATA_ENTIDADE, uuid.UUID(str(row.dados_anteriores[ITEM_ATA_KEY]))
    return row.entidade_tipo, row.entidade_id


def _entry(row: AuditLog, acrescimo: decimal.Decimal | None) -> Entry:
    return Entry(
        id=row.id,
        acao=row.acao,
        ocorrido_em=row.ocorrido_em,
        dados=row.dados_anteriores,
        acrescimo=acrescimo,
    )


def _ids(subjects: Collection[Subject], entidade: str) -> set[uuid.UUID]:
    return {entity_id for tipo, entity_id in subjects if tipo == entidade}


def _states(
    session: Session, subjects: Collection[Subject]
) -> tuple[
    dict[Subject, dict[str, Any]],
    dict[tuple[Subject, datetime.datetime], decimal.Decimal],
]:
    """Each entity as it is now, and the acréscimo of each aditivo by its subject and instant."""
    states: dict[Subject, dict[str, Any]] = {}
    atas = repo_ata.by_ids(session, _ids(subjects, ATA_ENTIDADE))
    items = repo_item.by_ids(session, _ids(subjects, ITEM_ATA_ENTIDADE))
    for ata in atas.values():
        states[ATA_ENTIDADE, ata.id] = _state(ata)
    for item in items.values():
        states[ITEM_ATA_ENTIDADE, item.id] = _state(item)
    for insumo in repo_insumo.insumos_by_id(session, _ids(subjects, INSUMO_ENTIDADE)).values():
        states[INSUMO_ENTIDADE, insumo.id] = _state(insumo)
    grupo_ids = _ids(subjects, GRUPO_MATERIAL_ENTIDADE)
    for grupo in repo_insumo.grupos_by_ids(session, grupo_ids).values():
        states[GRUPO_MATERIAL_ENTIDADE, grupo.id] = _state(grupo)

    nes = repo_ne.by_ids(session, _ids(subjects, NOTA_EMPENHO_ENTIDADE))
    ne_lines: dict[uuid.UUID, list[dict[str, str]]] = defaultdict(list)
    for ne_line, _item, _insumo in repo_ne.lines(session, nes.keys()):
        ne_lines[ne_line.nota_empenho_id].append(
            {
                ITEM_LINE_KEY[NOTA_EMPENHO_ENTIDADE]: str(ne_line.item_ata_id),
                ITEM_QUANTIDADE_KEY: str(ne_line.quantity),
            }
        )
    for ne in nes.values():
        states[NOTA_EMPENHO_ENTIDADE, ne.id] = {**_state(ne), ITENS_KEY: ne_lines[ne.id]}

    nfs = repo_nf.by_ids(session, _ids(subjects, NOTA_FISCAL_ENTIDADE))
    nf_lines: dict[uuid.UUID, list[dict[str, str]]] = defaultdict(list)
    for nf_line, _ne_line, _item, _insumo in repo_nf.lines(session, nfs.keys()):
        nf_lines[nf_line.nota_fiscal_id].append(
            {
                ITEM_LINE_KEY[NOTA_FISCAL_ENTIDADE]: str(nf_line.item_nota_empenho_id),
                ITEM_QUANTIDADE_KEY: str(nf_line.quantity),
            }
        )
    for nf in nfs.values():
        states[NOTA_FISCAL_ENTIDADE, nf.id] = {**_state(nf), ITENS_KEY: nf_lines[nf.id]}

    acrescimos: dict[tuple[Subject, datetime.datetime], decimal.Decimal] = {}
    ata_ids = atas.keys() | {item.ata_id for item in items.values()}
    for aditivo in repo_ata.aditivos_of_atas(session, ata_ids):
        attribute = ACRESCIMO_ATTRIBUTE.get(aditivo.kind)
        value = getattr(aditivo, attribute) if attribute else None
        if value is None:
            continue
        subject: Subject = (
            (ITEM_ATA_ENTIDADE, aditivo.item_ata_id)
            if aditivo.item_ata_id is not None
            else (ATA_ENTIDADE, aditivo.ata_id)
        )
        acrescimos[subject, aditivo.criado_em] = value
    return states, acrescimos


def _state(entity: Base) -> dict[str, Any]:
    """An entity's columns under the names its rows record, stored as `jsonable` stores them."""
    values = {
        STATE_KEY.get(attr.columns[0].name, attr.columns[0].name): getattr(entity, attr.key)
        for attr in inspect(entity).mapper.column_attrs
        if attr.columns[0].name not in UNTRACKED_COLUMNS
    }
    return jsonable(values)
