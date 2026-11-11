"""Reports and their exports (SPEC-0009).

Every figure is read as it stood at the data de referência (AC-0009-03). The
tables keep only the current state, so the past is rebuilt from the history:
a field that changed after the reference takes the prior value its first change
after it recorded (§2.2).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.constants import LOCAL_TIMEZONE
from app.constants.historico import ITEM_ATA_KEY
from app.constants.notas_empenho import COMMITTED, RESERVING, STAGE_LABEL, ZERO
from app.constants.notas_fiscais import APROVADA, DEVOLVIDA, EM_CONFERENCIA
from app.constants.relatorios import (
    ACAO_EXPORTADO,
    ALL_COLUMNS,
    ALL_TITLES,
    ATA_STATUS_LABEL,
    COLUMNS_UNKNOWN,
    DATE_FORMAT,
    ENTIDADE,
    EXECUCAO_ORCAMENTARIA,
    FILE_PREFIX,
    FILE_STAMP_FORMAT,
    FILTER_ATA,
    FORMAT_UNKNOWN,
    INDICADORES_FORNECEDORES,
    KEY_DATA_EMISSAO,
    KEY_ITENS,
    KEY_NUMERO,
    KEY_NUMERO_PRE_EMPENHO,
    KEY_OBJETO,
    KEY_STATUS,
    KEY_VALOR,
    KEY_VALOR_TOTAL,
    KEY_VIGENCIA_FIM,
    KEY_VIGENCIA_INICIO,
    MEDIA_TYPES,
    NFS_EM_CONFERENCIA,
    NO,
    POSICAO_SALDO,
    READERS,
    REFERENCE_IN_FUTURE,
    RESTRICTED,
    REWOUND_ENTIDADES,
    START_AFTER_REFERENCE,
    START_NOT_APPLICABLE,
    UNNAMED_USER,
    YES,
)
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories import ata as ata_repo
from app.repositories import audit_log as audit_repo
from app.repositories import item_ata as item_repo
from app.repositories import nota_empenho as ne_repo
from app.repositories import nota_fiscal as nf_repo
from app.services import saldo as saldo_service
from app.services.audit import Event, record
from app.services.errors import AtaNotFound, InvalidData, RelatorioNotFound, UnauthorizedPerfil
from app.services.itens_ata import item_value


@dataclass(frozen=True)
class Export:
    """One report as generated: its provenance and its table (AC-0009-02)."""

    id: uuid.UUID
    relatorio: str
    formato: str
    title: str
    gerado_em: datetime.datetime
    referencia: datetime.datetime
    inicio: datetime.datetime | None
    usuario: str
    filtros: tuple[tuple[str, str], ...]
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    @property
    def filename(self) -> str:
        """A name that says which report and which reference the file holds."""
        stamp = self.referencia.astimezone(LOCAL_TIMEZONE).strftime(FILE_STAMP_FORMAT)
        return f"{FILE_PREFIX}-{self.relatorio}-{stamp}.{self.formato}"


@dataclass(frozen=True)
class AtaAt:
    """An ATA as it stood at the reference."""

    id: uuid.UUID
    numero: str
    fornecedor: str
    fornecedor_id: uuid.UUID
    cnpj: str
    status: str
    vigencia_fim: datetime.date
    valor_contratado: decimal.Decimal
    objeto: str = ""
    vigencia_inicio: datetime.date | None = None
    criado_em: datetime.datetime | None = None


@dataclass(frozen=True)
class NeAt:
    """An NE as it stood at the reference."""

    id: uuid.UUID
    ata_id: uuid.UUID
    processo_sei: str
    numero_pre_empenho: str
    numero: str
    status: str
    valor: decimal.Decimal
    data_emissao: datetime.date | None
    criado_em: datetime.datetime


@dataclass(frozen=True)
class NfAt:
    """An NF as it stood at the reference."""

    id: uuid.UUID
    nota_empenho_id: uuid.UUID
    numero: str
    status: str
    valor: decimal.Decimal
    data_emissao: datetime.date
    criado_em: datetime.datetime


@dataclass(frozen=True)
class State:
    """Everything the four reports read, at one instant."""

    atas: tuple[AtaAt, ...]
    nes: tuple[NeAt, ...]
    nfs: tuple[NfAt, ...]
    inicio: datetime.datetime | None = None

    @property
    def nes_in_period(self) -> tuple[NeAt, ...]:
        """The NEs created in the window, or all of them without one (AC-0009-09)."""
        return tuple(ne for ne in self.nes if self.inicio is None or ne.criado_em >= self.inicio)

    @property
    def nfs_in_period(self) -> tuple[NfAt, ...]:
        """The NFs created in the window, or all of them without one (AC-0009-09)."""
        return tuple(nf for nf in self.nfs if self.inicio is None or nf.criado_em >= self.inicio)


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
) -> Export:
    """Build a report at its reference and record who exported it (AC-0009-01 to -05).

    The caller may keep only some columns (AC-0009-08) and only what was created
    from `inicio` on (AC-0009-09).
    """
    build = _BUILDERS.get(relatorio)
    if build is None:
        raise RelatorioNotFound()
    if inicio is not None and relatorio == POSICAO_SALDO:
        raise InvalidData({"inicio": START_NOT_APPLICABLE})
    filtros: tuple[tuple[str, str], ...] = ()
    reference = checked_reference(relatorio, formato, referencia, inicio, at, actor=actor)
    kept = chosen(relatorio, colunas)
    if ata_id is not None:
        ata = ata_repo.by_id(session, ata_id)
        if ata is None:
            raise AtaNotFound()
        filtros = ((FILTER_ATA, ata.number),)
    rows = build(state_at(session, referencia=reference, ata_id=ata_id, inicio=inicio), at)
    return recorded(
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
        filtros=filtros,
        rows=rows,
        asked={"ata_id": str(ata_id) if ata_id is not None else None},
    )


def checked_reference(
    relatorio: str,
    formato: str,
    referencia: datetime.datetime | None,
    inicio: datetime.datetime | None,
    at: datetime.datetime,
    *,
    actor: User,
) -> datetime.datetime:
    """The reference an export reads at, once the perfil, format and window are checked."""
    if relatorio in RESTRICTED and actor.role not in READERS:
        raise UnauthorizedPerfil()
    if formato not in MEDIA_TYPES:
        raise InvalidData({"formato": FORMAT_UNKNOWN})
    reference = referencia or at
    if reference > at:
        raise InvalidData({"referencia": REFERENCE_IN_FUTURE})
    if inicio is not None and inicio > reference:
        raise InvalidData({"inicio": START_AFTER_REFERENCE})
    return reference


def recorded(
    session: Session,
    *,
    actor: User,
    relatorio: str,
    formato: str,
    reference: datetime.datetime,
    inicio: datetime.datetime | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
    kept: tuple[int, ...],
    colunas: tuple[str, ...] | None,
    filtros: tuple[tuple[str, str], ...],
    rows: Iterable[tuple[str, ...]],
    asked: Mapping[str, Any],
) -> Export:
    """The export with its provenance, and the audit row that says who took it (AC-0009-02, -04)."""
    columns = ALL_COLUMNS[relatorio]
    result = Export(
        id=uuid.uuid4(),
        relatorio=relatorio,
        formato=formato,
        title=ALL_TITLES[relatorio],
        gerado_em=at,
        referencia=reference,
        inicio=inicio,
        usuario=actor.nome or UNNAMED_USER,
        filtros=filtros,
        columns=tuple(columns[index][1] for index in kept),
        rows=tuple(tuple(row[index] for index in kept) for row in rows),
    )
    record(
        session,
        Event(
            entidade_tipo=ENTIDADE,
            entidade_id=result.id,
            acao=ACAO_EXPORTADO,
            user_id=actor.id,
            # Not prior values: what was asked for, so the export can be run again.
            dados_anteriores={
                "relatorio": relatorio,
                "formato": formato,
                "referencia": reference.isoformat(),
                **asked,
                "inicio": inicio.isoformat() if inicio is not None else None,
                "colunas": ([columns[index][0] for index in kept] if colunas is not None else None),
            },
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return result


def chosen(relatorio: str, colunas: tuple[str, ...] | None) -> tuple[int, ...]:
    """Which columns of a report an export keeps, in the report's own order (AC-0009-08)."""
    keys = [key for key, _ in ALL_COLUMNS[relatorio]]
    if colunas is None:
        return tuple(range(len(keys)))
    if not colunas or not set(colunas) <= set(keys):
        raise InvalidData({"colunas": COLUMNS_UNKNOWN.format(columns=", ".join(keys))})
    return tuple(index for index, key in enumerate(keys) if key in colunas)


# ── The state at the reference ──────────────────────────────────────────────


def rewound(rows: Iterable[AuditLog]) -> dict[uuid.UUID, dict[str, Any]]:
    """What each field held before its first change in these rows, per entity.

    The rows come oldest first and all fall after the reference, so the first
    prior value seen for a field is the one it had at the reference.
    """
    state: dict[uuid.UUID, dict[str, Any]] = {}
    for row in rows:
        previous = row.dados_anteriores or {}
        # An ATA row about one of its items carries the item's fields, not the ATA's.
        if ITEM_ATA_KEY in previous:
            continue
        fields = state.setdefault(row.entidade_id, {})
        for key, value in previous.items():
            fields.setdefault(key, value)
    return state


def state_at(
    session: Session,
    *,
    referencia: datetime.datetime,
    ata_id: uuid.UUID | None,
    inicio: datetime.datetime | None = None,
) -> State:
    """The ATAs, NEs and NFs as they stood at an instant (§2.2)."""
    past = rewound(audit_repo.after(session, since=referencia, entidade_tipos=REWOUND_ENTIDADES))
    atas = _atas_at(session, referencia, ata_id, past)
    nes = _nes_at(session, referencia, [ata.id for ata in atas], past)
    nfs = tuple(
        NfAt(
            id=nf.id,
            nota_empenho_id=nf.nota_empenho_id,
            numero=past.get(nf.id, {}).get(KEY_NUMERO, nf.numero),
            status=past.get(nf.id, {}).get(KEY_STATUS, nf.status),
            valor=_decimal(past.get(nf.id, {}).get(KEY_VALOR), nf.value),
            data_emissao=_date(past.get(nf.id, {}).get(KEY_DATA_EMISSAO), nf.issued_on),
            criado_em=nf.criado_em,
        )
        for nf in nf_repo.created_until(session, until=referencia, ne_ids=[ne.id for ne in nes])
    )
    return State(atas=atas, nes=nes, nfs=nfs, inicio=inicio)


def _atas_at(
    session: Session,
    referencia: datetime.datetime,
    ata_id: uuid.UUID | None,
    past: Mapping[uuid.UUID, Mapping[str, Any]],
) -> tuple[AtaAt, ...]:
    rows = ata_repo.created_until(session, until=referencia, ata_id=ata_id)
    aditivos = ata_repo.aditivos_de_valor_until(session, until=referencia)
    fornecedores = ata_repo.fornecedores_by_id(session, {ata.fornecedor_id for ata in rows})
    return tuple(
        AtaAt(
            id=ata.id,
            numero=ata.number,
            fornecedor=fornecedores[ata.fornecedor_id].legal_name,
            fornecedor_id=ata.fornecedor_id,
            cnpj=fornecedores[ata.fornecedor_id].cnpj,
            status=past.get(ata.id, {}).get(KEY_STATUS, ata.status),
            vigencia_fim=_date(past.get(ata.id, {}).get(KEY_VIGENCIA_FIM), ata.vigencia_fim),
            valor_contratado=_decimal(past.get(ata.id, {}).get(KEY_VALOR_TOTAL), ata.total_value)
            + aditivos.get(ata.id, ZERO),
            objeto=past.get(ata.id, {}).get(KEY_OBJETO, ata.subject),
            criado_em=ata.criado_em,
            vigencia_inicio=_date(
                past.get(ata.id, {}).get(KEY_VIGENCIA_INICIO), ata.vigencia_inicio
            ),
        )
        for ata in rows
    )


def _nes_at(
    session: Session,
    referencia: datetime.datetime,
    ata_ids: list[uuid.UUID],
    past: Mapping[uuid.UUID, Mapping[str, Any]],
) -> tuple[NeAt, ...]:
    rows = ne_repo.created_until(session, until=referencia, ata_ids=ata_ids)
    current: dict[uuid.UUID, decimal.Decimal] = {}
    for line, _, _ in ne_repo.lines(session, [ne.id for ne in rows]):
        current[line.nota_empenho_id] = current.get(line.nota_empenho_id, ZERO) + line.value
    former = {ne.id: past[ne.id][KEY_ITENS] for ne in rows if KEY_ITENS in past.get(ne.id, {})}
    prices = item_repo.by_ids(
        session, {uuid.UUID(item["item_ata_id"]) for itens in former.values() for item in itens}
    )
    result = []
    for ne in rows:
        fields = past.get(ne.id, {})
        status = fields.get(KEY_STATUS, ne.status)
        counted = status in RESERVING or status in COMMITTED
        emitted = status in COMMITTED
        valor = (
            sum(
                (
                    item_value(
                        decimal.Decimal(item["quantidade"]),
                        prices[uuid.UUID(item["item_ata_id"])].unit_price,
                    )
                    for item in former[ne.id]
                ),
                ZERO,
            )
            if ne.id in former
            else current.get(ne.id, ZERO)
        )
        result.append(
            NeAt(
                id=ne.id,
                ata_id=ne.ata_id,
                processo_sei=ne.processo_sei,
                numero_pre_empenho=(
                    fields.get(KEY_NUMERO_PRE_EMPENHO, ne.numero_pre_empenho) or ""
                    if counted
                    else ""
                ),
                numero=(ne.numero or "") if emitted else "",
                status=status,
                valor=valor,
                data_emissao=ne.issued_on if emitted else None,
                criado_em=ne.criado_em,
            )
        )
    return tuple(result)


def _decimal(former: str | None, current: decimal.Decimal) -> decimal.Decimal:
    return decimal.Decimal(former) if former is not None else current


def _date(former: str | None, current: datetime.date) -> datetime.date:
    return datetime.date.fromisoformat(former) if former is not None else current


# ── The four tables ─────────────────────────────────────────────────────────


def _execucao(state: State, at: datetime.datetime) -> list[tuple[str, ...]]:
    """One row per NE, under its ATA (§2.1)."""
    atas = {ata.id: ata for ata in state.atas}
    order = {ata.id: index for index, ata in enumerate(state.atas)}
    return [
        (
            atas[ne.ata_id].numero,
            atas[ne.ata_id].fornecedor,
            ne.processo_sei,
            ne.numero_pre_empenho,
            ne.numero,
            STAGE_LABEL[ne.status],
            money(ne.valor),
            day(ne.data_emissao),
        )
        for ne in sorted(state.nes_in_period, key=lambda ne: order[ne.ata_id])
    ]


def _posicao(state: State, at: datetime.datetime) -> list[tuple[str, ...]]:
    """One row per ATA with its saldo, summed as SPEC-0006 sums it (§2.1)."""
    rows: list[tuple[str, ...]] = []
    for ata in state.atas:
        nes = [ne for ne in state.nes if ne.ata_id == ata.id]
        saldo = saldo_service.position(
            ata.valor_contratado,
            sum((ne.valor for ne in nes if ne.status in RESERVING), ZERO),
            sum((ne.valor for ne in nes if ne.status in COMMITTED), ZERO),
            at=at,
        )
        rows.append(
            (
                ata.numero,
                ata.fornecedor,
                ATA_STATUS_LABEL[ata.status],
                day(ata.vigencia_fim),
                money(saldo.valor_contratado),
                money(saldo.valor_reservado),
                money(saldo.valor_empenhado),
                money(saldo.saldo_disponivel),
                money(saldo.comprometimento_percentual),
                YES if saldo.alto_consumo else NO,
            )
        )
    return rows


def _em_conferencia(state: State, at: datetime.datetime) -> list[tuple[str, ...]]:
    """One row per NF that was in the conference (§2.1)."""
    atas = {ata.id: ata for ata in state.atas}
    nes = {ne.id: ne for ne in state.nes}
    return [
        (
            nf.numero,
            atas[nes[nf.nota_empenho_id].ata_id].fornecedor,
            nes[nf.nota_empenho_id].numero,
            atas[nes[nf.nota_empenho_id].ata_id].numero,
            day(nf.data_emissao),
            money(nf.valor),
        )
        for nf in state.nfs_in_period
        if nf.status == EM_CONFERENCIA
    ]


def _indicadores(state: State, at: datetime.datetime) -> list[tuple[str, ...]]:
    """One row per fornecedor with an ATA, by razão social (§2.1)."""
    ata_fornecedor = {ata.id: ata.fornecedor_id for ata in state.atas}
    ne_fornecedor = {ne.id: ata_fornecedor[ne.ata_id] for ne in state.nes}
    rows: list[tuple[str, ...]] = []
    for fornecedor_id, nome, cnpj in sorted(
        {(ata.fornecedor_id, ata.fornecedor, ata.cnpj) for ata in state.atas},
        key=lambda found: (found[1], found[2]),
    ):
        atas = [ata for ata in state.atas if ata.fornecedor_id == fornecedor_id]
        nes = [ne for ne in state.nes_in_period if ne_fornecedor[ne.id] == fornecedor_id]
        nfs = [
            nf for nf in state.nfs_in_period if ne_fornecedor[nf.nota_empenho_id] == fornecedor_id
        ]
        aprovadas = [nf for nf in nfs if nf.status == APROVADA]
        rows.append(
            (
                nome,
                cnpj,
                str(len(atas)),
                money(sum((ata.valor_contratado for ata in atas), ZERO)),
                money(sum((ne.valor for ne in nes if ne.status in COMMITTED), ZERO)),
                str(len(nfs)),
                str(len(aprovadas)),
                str(len([nf for nf in nfs if nf.status == DEVOLVIDA])),
                money(sum((nf.valor for nf in aprovadas), ZERO)),
            )
        )
    return rows


def money(value: decimal.Decimal) -> str:
    """A figure with the comma as its decimal mark and no grouping (AC-0009-06)."""
    return f"{value:.2f}".replace(".", ",")


def day(value: datetime.date | None) -> str:
    """A date as the servidor writes it, or nothing."""
    return value.strftime(DATE_FORMAT) if value is not None else ""


_BUILDERS: Mapping[str, Callable[[State, datetime.datetime], list[tuple[str, ...]]]] = {
    EXECUCAO_ORCAMENTARIA: _execucao,
    POSICAO_SALDO: _posicao,
    NFS_EM_CONFERENCIA: _em_conferencia,
    INDICADORES_FORNECEDORES: _indicadores,
}
