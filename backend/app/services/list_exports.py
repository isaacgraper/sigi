"""Exporting a list as it stood at the data de referência (SPEC-0009 v1.2, AC-0009-10 to -12).

Each list keeps its own filters and, for a servidor, its RN07 scope; every
export goes through the same provenance and audit row as the four reports.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.constants import LOCAL_TIMEZONE
from app.constants.historico import ITEM_ATA_KEY
from app.constants.notas_empenho import STAGE_LABEL
from app.constants.notas_fiscais import STATUS_LABEL as NF_STATUS_LABEL
from app.constants.relatorios import (
    ACAO_ITEM_REMOVIDO,
    ATA_ENTIDADE,
    ATA_STATUS_LABEL,
    ATAS,
    CHANGE_ARROW,
    CHANGE_SEPARATOR,
    DATE_FILTERS,
    FALSE_TEXT,
    FILTER_LABEL,
    GRUPO_SEPARATOR,
    HISTORICO,
    HISTORICO_ENTIDADE_LABEL,
    INSTANT_FORMAT,
    INSUMO_ENTIDADE,
    INSUMO_REWOUND,
    INSUMO_SITUACAO_LABEL,
    INSUMOS,
    ITEM_LINE_SEPARATOR,
    ITEM_REWOUND,
    ITENS_ATA,
    ITENS_WITHOUT_ATA,
    LIST_FILTER_INVALID,
    LIST_FILTERS,
    LIST_TITLES,
    NO,
    NOTA_FISCAL_ENTIDADE,
    NOTAS_EMPENHO,
    NOTAS_FISCAIS,
    NOTHING,
    QUARENTENA_BEFORE,
    SITUACAO_VIGENCIA_LABEL,
    SYSTEM_USER,
    TRUE_TEXT,
    UUID_FILTERS,
    YES,
)
from app.core.clock import local_date
from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories import ata as ata_repo
from app.repositories import audit_log as audit_repo
from app.repositories import insumo as insumo_repo
from app.repositories import item_ata as item_repo
from app.repositories import nota_fiscal as nf_repo
from app.repositories import user as user_repo
from app.services import historico as historico_service
from app.services import relatorios
from app.services.atas import situacao_vigencia
from app.services.errors import AtaNotFound, InvalidData
from app.services.history_changes import Change, Detail
from app.services.insumos import scope_of, visible
from app.services.itens_ata import item_value
from app.services.relatorios import Export, State, day, money, rewound, state_at

Labels = tuple[tuple[str, str], ...]
Rows = list[tuple[str, ...]]
Builder = Callable[
    [Session, User, datetime.datetime, datetime.datetime | None, Mapping[str, Any]],
    tuple[Labels, Rows],
]

# Every status a row may name, as the file prints it.
_STATUS_TEXT: Mapping[str, str] = {**ATA_STATUS_LABEL, **STAGE_LABEL, **NF_STATUS_LABEL}


def export(
    session: Session,
    *,
    actor: User,
    relatorio: str,
    formato: str,
    referencia: datetime.datetime | None,
    ata_id: uuid.UUID | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
    colunas: tuple[str, ...] | None = None,
    inicio: datetime.datetime | None = None,
    filtros: Mapping[str, str | None] | None = None,
) -> Export:
    """A list export, or one of the four reports when `relatorio` names one (AC-0009-10)."""
    if relatorio not in LIST_TITLES:
        return relatorios.export(
            session,
            actor=actor,
            relatorio=relatorio,
            formato=formato,
            referencia=referencia,
            ata_id=ata_id,
            at=at,
            correlation_id=correlation_id,
            colunas=colunas,
            inicio=inicio,
        )
    reference = relatorios.checked_reference(
        relatorio, formato, referencia, inicio, at, actor=actor
    )
    kept = relatorios.chosen(relatorio, colunas)
    raw = dict(filtros or {})
    if ata_id is not None:
        raw["ata_id"] = str(ata_id)
    given = _parsed(relatorio, raw)
    labels, rows = _BUILDERS[relatorio](session, actor, reference, inicio, given)
    return relatorios.recorded(
        session,
        actor=actor,
        relatorio=relatorio,
        formato=formato,
        reference=reference,
        inicio=inicio,
        at=at,
        correlation_id=correlation_id,
        kept=kept,
        colunas=colunas,
        filtros=labels,
        rows=rows,
        asked={"filtros": {key: str(value) for key, value in given.items()}},
    )


def _parsed(relatorio: str, raw: Mapping[str, str | None]) -> dict[str, Any]:
    """The list's own filters, each read as its list reads it; any other is ignored."""
    given: dict[str, Any] = {}
    invalid: dict[str, str] = {}
    for key in LIST_FILTERS[relatorio]:
        value = raw.get(key)
        if value is None or value == "":
            continue
        try:
            if key in UUID_FILTERS:
                given[key] = uuid.UUID(value)
            elif key in DATE_FILTERS:
                given[key] = datetime.date.fromisoformat(value)
            elif key == "quarentena":
                if value not in (TRUE_TEXT, FALSE_TEXT):
                    raise ValueError(value)
                given[key] = value == TRUE_TEXT
            else:
                given[key] = value
        except ValueError:
            invalid[key] = LIST_FILTER_INVALID
    if invalid:
        raise InvalidData(invalid)
    return given


def _label(key: str, value: str) -> tuple[str, str]:
    return FILTER_LABEL[key], value


def _created_from(created: datetime.datetime | None, inicio: datetime.datetime | None) -> bool:
    return inicio is None or (created is not None and created >= inicio)


def _ata_numbers(state: State) -> dict[uuid.UUID, str]:
    return {ata.id: ata.numero for ata in state.atas}


# ── ATAs, NEs and NFs: the state of §2.2 ────────────────────────────────────


def _atas(
    session: Session,
    actor: User,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    given: Mapping[str, Any],
) -> tuple[Labels, Rows]:
    state = state_at(session, referencia=reference, ata_id=None)
    today = local_date(reference)
    window = get_settings().ata_alert_days
    rows: Rows = []
    for ata in state.atas:
        situacao = situacao_vigencia(ata.vigencia_fim, today, window)
        if not _created_from(ata.criado_em, inicio):
            continue
        if given.get("status") not in (None, ata.status):
            continue
        if given.get("situacao_vigencia") not in (None, situacao):
            continue
        rows.append(
            (
                ata.numero,
                ata.objeto,
                ata.fornecedor,
                day(ata.vigencia_inicio),
                day(ata.vigencia_fim),
                money(ata.valor_contratado),
                ATA_STATUS_LABEL[ata.status],
                SITUACAO_VIGENCIA_LABEL[situacao],
            )
        )
    labels: list[tuple[str, str]] = []
    if "status" in given:
        labels.append(_label("status", ATA_STATUS_LABEL.get(given["status"], given["status"])))
    if "situacao_vigencia" in given:
        value = given["situacao_vigencia"]
        labels.append(_label("situacao_vigencia", SITUACAO_VIGENCIA_LABEL.get(value, value)))
    return tuple(labels), rows


def _notas_empenho(
    session: Session,
    actor: User,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    given: Mapping[str, Any],
) -> tuple[Labels, Rows]:
    state = state_at(session, referencia=reference, ata_id=given.get("ata_id"), inicio=inicio)
    numbers = _ata_numbers(state)
    if "ata_id" in given and given["ata_id"] not in numbers:
        raise AtaNotFound()
    rows: Rows = [
        (
            ne.processo_sei,
            numbers[ne.ata_id],
            STAGE_LABEL[ne.status],
            money(ne.valor),
            ne.numero_pre_empenho,
            ne.numero,
            day(local_date(ne.criado_em)),
        )
        for ne in sorted(state.nes_in_period, key=lambda ne: ne.criado_em, reverse=True)
        if given.get("etapa") in (None, ne.status)
        and given.get("processo_sei", "") in ne.processo_sei
    ]
    labels: list[tuple[str, str]] = []
    if "etapa" in given:
        labels.append(_label("etapa", STAGE_LABEL.get(given["etapa"], given["etapa"])))
    if "ata_id" in given:
        labels.append(_label("ata_id", numbers[given["ata_id"]]))
    if "processo_sei" in given:
        labels.append(_label("processo_sei", given["processo_sei"]))
    return tuple(labels), rows


def _notas_fiscais(
    session: Session,
    actor: User,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    given: Mapping[str, Any],
) -> tuple[Labels, Rows]:
    state = state_at(session, referencia=reference, ata_id=None, inicio=inicio)
    numbers = _ata_numbers(state)
    nes = {ne.id: ne for ne in state.nes}
    held = _quarentena_at(session, reference, [nf.id for nf in state.nfs])
    rows: Rows = []
    for nf in sorted(state.nfs_in_period, key=lambda nf: nf.criado_em, reverse=True):
        if given.get("status") not in (None, nf.status):
            continue
        if given.get("nota_empenho_id") not in (None, nf.nota_empenho_id):
            continue
        if given.get("quarentena") not in (None, held[nf.id]):
            continue
        ne = nes[nf.nota_empenho_id]
        rows.append(
            (
                nf.numero,
                ne.numero,
                numbers[ne.ata_id],
                day(nf.data_emissao),
                money(nf.valor),
                NF_STATUS_LABEL[nf.status],
                YES if held[nf.id] else NO,
            )
        )
    labels: list[tuple[str, str]] = []
    if "status" in given:
        labels.append(_label("status", NF_STATUS_LABEL.get(given["status"], given["status"])))
    if "nota_empenho_id" in given:
        ne_at = nes.get(given["nota_empenho_id"])
        labels.append(
            _label("nota_empenho_id", ne_at.numero if ne_at else str(given["nota_empenho_id"]))
        )
    if "quarentena" in given:
        labels.append(_label("quarentena", YES if given["quarentena"] else NO))
    return tuple(labels), rows


def _quarentena_at(
    session: Session, reference: datetime.datetime, nf_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, bool]:
    """Whether each NF was held at the reference.

    A quarentena row records the motivo, not the flag, so the flag before the
    first such row after the reference is the one its acao implies.
    """
    current = {nf.id: nf.quarentena for nf in nf_repo.by_ids(session, nf_ids).values()}
    before: dict[uuid.UUID, bool] = {}
    for row in audit_repo.after(session, since=reference, entidade_tipos=(NOTA_FISCAL_ENTIDADE,)):
        if row.acao in QUARENTENA_BEFORE and row.entidade_id not in before:
            before[row.entidade_id] = QUARENTENA_BEFORE[row.acao]
    return {nf_id: before.get(nf_id, current.get(nf_id, False)) for nf_id in nf_ids}


# ── Insumos and the items of an ATA ─────────────────────────────────────────


def _insumos(
    session: Session,
    actor: User,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    given: Mapping[str, Any],
) -> tuple[Labels, Rows]:
    scope = scope_of(session, actor)
    grupos = {grupo.id: grupo for grupo in insumo_repo.all_grupos(session)}
    within = insumo_repo.descendants(session, [given["grupo_id"]]) if "grupo_id" in given else None
    past = rewound(audit_repo.after(session, since=reference, entidade_tipos=(INSUMO_ENTIDADE,)))
    query = str(given.get("q", "")).casefold()
    rows: Rows = []
    for insumo in insumo_repo.insumos_created_until(session, until=reference):
        # RN07 is the servidor's scope now: a past grupo never widens it.
        if not visible(scope, insumo) or not _created_from(insumo.criado_em, inicio):
            continue
        fields = past.get(insumo.id, {})
        value = {
            attribute: fields.get(key, getattr(insumo, attribute))
            for key, attribute in INSUMO_REWOUND.items()
        }
        grupo_id = uuid.UUID(str(value["grupo_id"]))
        situacao = (
            "substituido"
            if value["substitute_id"]
            else "descontinuado"
            if value["discontinued_on"]
            else "ativo"
        )
        searched = (str(value["sku"]), str(value["codigo_doms"] or ""), str(value["description"]))
        if query and not any(query in text.casefold() for text in searched):
            continue
        if within is not None and grupo_id not in within:
            continue
        if given.get("status") not in (None, situacao):
            continue
        rows.append(
            (
                str(value["sku"]),
                str(value["description"]),
                str(value["unit"]),
                _grupo_path(grupos, grupo_id),
                str(value["codigo_doms"] or ""),
                str(value["external_code"] or ""),
                INSUMO_SITUACAO_LABEL[situacao],
            )
        )
    labels: list[tuple[str, str]] = []
    if "q" in given:
        labels.append(_label("q", given["q"]))
    if "grupo_id" in given:
        labels.append(_label("grupo_id", _grupo_path(grupos, given["grupo_id"])))
    if "status" in given:
        labels.append(_label("status", INSUMO_SITUACAO_LABEL.get(given["status"], given["status"])))
    return tuple(labels), rows


def _grupo_path(grupos: Mapping[uuid.UUID, Any], grupo_id: uuid.UUID) -> str:
    names: list[str] = []
    current: uuid.UUID | None = grupo_id
    while current is not None and current in grupos:
        names.append(grupos[current].name)
        current = grupos[current].parent_id
    return GRUPO_SEPARATOR.join(reversed(names))


def _itens_ata(
    session: Session,
    actor: User,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    given: Mapping[str, Any],
) -> tuple[Labels, Rows]:
    if "ata_id" not in given:
        raise InvalidData({"ata_id": ITENS_WITHOUT_ATA})
    ata = ata_repo.by_id(session, given["ata_id"])
    if ata is None or ata.criado_em > reference:
        raise AtaNotFound()
    scope = scope_of(session, actor)
    items = item_repo.of_ata_created_until(session, ata_id=ata.id, until=reference)
    past = _items_rewound(
        audit_repo.after(session, since=reference, entidade_tipos=(ATA_ENTIDADE,)), ata.id
    )
    values = {
        item.id: {
            attribute: past.get(item.id, {}).get(key, getattr(item, attribute))
            for key, attribute in ITEM_REWOUND.items()
        }
        for item in items
    }
    insumos = insumo_repo.insumos_by_id(
        session,
        {item.insumo_id for item in items}
        | {uuid.UUID(str(value["insumo_id"])) for value in values.values()},
    )
    rows: Rows = []
    for item in items:
        if item.removed_at is not None and item.removed_at <= reference:
            continue
        if not _created_from(item.criado_em, inicio) or not visible(scope, insumos[item.insumo_id]):
            continue
        value = values[item.id]
        insumo = insumos[uuid.UUID(str(value["insumo_id"]))]
        quantity = decimal.Decimal(str(value["quantity"]))
        price = decimal.Decimal(str(value["unit_price"]))
        rows.append(
            (
                str(value["item_number"] or ""),
                insumo.sku,
                insumo.description,
                insumo.unit,
                _number(quantity),
                _number(price),
                money(item_value(quantity, price)),
            )
        )
    return (_label("ata_id", ata.number),), rows


def _items_rewound(rows: Sequence[AuditLog], ata_id: uuid.UUID) -> dict[uuid.UUID, dict[str, Any]]:
    """What each item's fields held before their first change after the reference."""
    state: dict[uuid.UUID, dict[str, Any]] = {}
    for row in rows:
        previous = row.dados_anteriores or {}
        if row.entidade_id != ata_id or ITEM_ATA_KEY not in previous:
            continue
        # A removal records the values the item still has, not a change to them.
        if row.acao == ACAO_ITEM_REMOVIDO:
            continue
        fields = state.setdefault(uuid.UUID(str(previous[ITEM_ATA_KEY])), {})
        for key, value in previous.items():
            fields.setdefault(key, value)
    return state


def _number(value: decimal.Decimal) -> str:
    """A quantity or a unit price as the file writes figures: comma, no trailing zeros."""
    return format(value.normalize(), "f").replace(".", ",")


# ── The Histórico ───────────────────────────────────────────────────────────


def _historico(
    session: Session,
    actor: User,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    given: Mapping[str, Any],
) -> tuple[Labels, Rows]:
    since, until = historico_service.period(
        entidade_tipo=given.get("entidade_tipo"),
        entidade_id=given.get("entidade_id"),
        de=given.get("de"),
        ate=given.get("ate"),
    )
    # The reference is included; `until` excludes its own instant.
    edge = reference + datetime.timedelta(microseconds=1)
    until = min(until, edge) if until is not None else edge
    if inicio is not None:
        since = max(since, inicio) if since is not None else inicio

    def read(limit: int) -> tuple[Sequence[AuditLog], int]:
        return audit_repo.page(
            session,
            entidade_tipo=given.get("entidade_tipo"),
            entidade_id=given.get("entidade_id"),
            usuario_id=given.get("usuario_id"),
            since=since,
            until=until,
            offset=0,
            limit=limit,
        )

    _, total = read(1)
    rows, _ = read(max(total, 1))
    changes = historico_service.changes_of(session, rows)
    users = user_repo.by_ids(session, {row.user_id for row in rows if row.user_id is not None})
    table: Rows = [
        (
            row.ocorrido_em.astimezone(LOCAL_TIMEZONE).strftime(INSTANT_FORMAT),
            changes[row.id].acao_rotulo,
            HISTORICO_ENTIDADE_LABEL.get(row.entidade_tipo, row.entidade_tipo),
            str(row.entidade_id),
            (users[row.user_id].nome or NOTHING) if row.user_id in users else SYSTEM_USER,
            CHANGE_SEPARATOR.join(_change_text(change) for change in changes[row.id].alteracoes),
            CHANGE_SEPARATOR.join(_detail_text(detail) for detail in changes[row.id].detalhes),
        )
        for row in rows
    ]
    labels: list[tuple[str, str]] = []
    if "entidade_tipo" in given:
        tipo = given["entidade_tipo"]
        labels.append(_label("entidade_tipo", HISTORICO_ENTIDADE_LABEL.get(tipo, tipo)))
    for key in ("entidade_id", "usuario_id"):
        if key in given:
            member = users.get(given[key]) if key == "usuario_id" else None
            labels.append(_label(key, (member.nome if member else None) or str(given[key])))
    for key in ("de", "ate"):
        if key in given:
            labels.append(_label(key, day(given[key])))
    return tuple(labels), table


def _change_text(change: Change) -> str:
    """`Campo: antes → depois`, each value as the file writes it (AC-0009-12)."""
    return (
        f"{change.rotulo}: {_value_text(change.tipo, change.antes)}"
        f"{CHANGE_ARROW}{_value_text(change.tipo, change.depois)}"
    )


def _detail_text(detail: Detail) -> str:
    return f"{detail.rotulo}: {_value_text('texto', detail.valor)}"


def _value_text(tipo: str, value: Any) -> str:
    if value is None or value == "" or value == []:
        return NOTHING
    if isinstance(value, bool):
        return YES if value else NO
    if isinstance(value, list):
        return ITEM_LINE_SEPARATOR.join(
            _number(decimal.Decimal(str(line.get("quantidade", "0"))))
            if isinstance(line, dict)
            else str(line)
            for line in value
        )
    text = str(value)
    if tipo == "data":
        try:
            return day(datetime.date.fromisoformat(text[:10]))
        except ValueError:
            return text
    if tipo in ("dinheiro", "quantidade"):
        try:
            return _number(decimal.Decimal(text))
        except decimal.InvalidOperation:
            return text
    if tipo == "status":
        return _STATUS_TEXT.get(text, text)
    return text


_BUILDERS: Mapping[str, Builder] = {
    ATAS: _atas,
    ITENS_ATA: _itens_ata,
    INSUMOS: _insumos,
    NOTAS_EMPENHO: _notas_empenho,
    NOTAS_FISCAIS: _notas_fiscais,
    HISTORICO: _historico,
}
