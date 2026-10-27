"""ATAs — registration, lifecycle, aditivos, reajuste and the two alerts (SPEC-0002).

The ATA is the root of every supply cycle. What is derived here, and has no
column anywhere, is `situacao_vigencia`, the reajuste date and `valor_contratado`:
a date that follows another date goes stale the moment nobody runs the job that
refreshes it (SPEC-0002 §2).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants.atas import (
    ADITIVO_CEILING,
    EDITABLE_COLUMN,
    MOVES,
    NOT_EDITABLE_STATUS,
    PROCESSO_SEI_FORMAT,
)
from app.constants.notas_empenho import COMMITTED, LOCKED_ATA_FIELDS, NE_IN_PROGRESS
from app.core import cnpj as cnpj_lib
from app.core import processo_sei
from app.core.clock import local_date
from app.core.config import get_settings
from app.models.ata import Ata, AtaAditivo, AtaReajuste
from app.models.fornecedor import Fornecedor
from app.models.user import User
from app.repositories import ata as repo
from app.repositories import nota_empenho as ne_repo
from app.repositories import user as repo_user
from app.services.audit import Event, record
from app.services.errors import (
    AditivoAcimaDoLimite,
    AtaComNeEmitida,
    AtaComNePendente,
    AtaDuplicada,
    AtaNaoEditavel,
    AtaNaoVigente,
    AtaNotFound,
    InvalidData,
    ProcessoSeiInvalido,
    TransicaoInvalida,
)


@dataclass(frozen=True)
class FornecedorInput:
    """The fornecedor as the gestor typed it."""

    cnpj: str
    legal_name: str


@dataclass(frozen=True)
class AtaView:
    """An ATA with what is derived from it, as every read returns it."""

    ata: Ata
    fornecedor: Fornecedor
    valor_contratado: decimal.Decimal
    situacao_vigencia: str
    data_reajuste: datetime.date


@dataclass(frozen=True)
class AtaDetail(AtaView):
    """One ATA with its aditivos and reajuste requests."""

    aditivos: Sequence[AtaAditivo]
    reajustes: Sequence[AtaReajuste]


@dataclass(frozen=True)
class AlertItem:
    """One row of either alert."""

    view: AtaView
    days_remaining: int


def reajuste_date(budget_date: datetime.date) -> datetime.date:
    """One calendar year after the data do orçamento (AC-0002-18).

    An orçamento dated 29/02 falls due on 28/02, because the next year has no 29.
    """
    try:
        return budget_date.replace(year=budget_date.year + 1)
    except ValueError:
        return budget_date.replace(year=budget_date.year + 1, day=28)


def situacao_vigencia(vigencia_fim: datetime.date, today: datetime.date, window: int) -> str:
    """`vigente`, `a_vencer` (at most `window` days left) or `vencida` (AC-0002-15)."""
    remaining = (vigencia_fim - today).days
    if remaining < 0:
        return "vencida"
    return "a_vencer" if remaining <= window else "vigente"


def register(
    session: Session,
    *,
    actor: User,
    number: str,
    subject: str,
    organ: str,
    fornecedor: FornecedorInput,
    issued_on: datetime.date | None,
    vigencia_inicio: datetime.date,
    vigencia_fim: datetime.date,
    total_value: decimal.Decimal,
    budget_date: datetime.date,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Ata:
    """Register an ATA, vigente from the start (AC-0002-01, -02, -03, -25).

    The gestor has already reviewed it on the screen, so nothing waits for an
    activation (SPEC-0002 v1.2).
    """
    _require_interval(vigencia_inicio, vigencia_fim)
    if repo.by_number(session, number) is not None:
        raise AtaDuplicada()
    supplier = find_or_create_fornecedor(session, fornecedor)

    ata = Ata(
        number=number,
        subject=subject,
        organ=organ,
        fornecedor_id=supplier.id,
        issued_on=issued_on,
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=vigencia_fim,
        total_value=total_value,
        budget_date=budget_date,
        status="vigente",
        owner_id=actor.id,
        criado_em=at,
        atualizado_em=at,
    )
    try:
        # A savepoint, so losing the race on `numero` leaves the request's own
        # transaction usable for the error to be reported from.
        with session.begin_nested():
            repo.add(session, ata)
    except IntegrityError as exc:
        raise AtaDuplicada() from exc
    audit_ata(session, ata, "ata.criada", actor, correlation_id, at, previous=None)
    return ata


def edit(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    changes: dict[str, Any],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Ata:
    """Correct any field of an ATA that is not history (AC-0002-24).

    An edit corrects what was typed, an aditivo changes what was contracted;
    both leave the prior values in the audit row. An `encerrada` or `cancelada`
    ATA is history and is refused before anything is looked up.
    """
    ata = lock_ata(session, ata_id)
    if ata.status in NOT_EDITABLE_STATUS:
        raise AtaNaoEditavel()
    if LOCKED_ATA_FIELDS & changes.keys() and ne_repo.of_ata_in(session, ata.id, COMMITTED):
        # An NE was committed against these figures; only an aditivo moves them (AC-0004-26).
        raise AtaComNeEmitida()
    supplier: Fornecedor | None = None
    if "fornecedor" in changes:
        supplier = find_or_create_fornecedor(session, changes.pop("fornecedor"))
        changes["fornecedor_id"] = supplier.id

    effective = {key: value for key, value in changes.items() if getattr(ata, key) != value}
    if not effective:
        return ata

    start = effective.get("vigencia_inicio", ata.vigencia_inicio)
    end = effective.get("vigencia_fim", ata.vigencia_fim)
    _require_interval(start, end)
    if "number" in effective and repo.by_number(session, effective["number"]) is not None:
        raise AtaDuplicada()
    if "owner_id" in effective:
        owner = repo_user.by_id(session, effective["owner_id"])
        if owner is None or owner.status != "ativo":
            raise InvalidData({"owner_id": "Informe um membro ativo."})

    # The keys of `dados_anteriores` are columns, read by a DBA (ADR-0013).
    previous = {EDITABLE_COLUMN[key]: getattr(ata, key) for key in effective}
    for key, value in effective.items():
        setattr(ata, key, value)
    ata.atualizado_em = at
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise AtaDuplicada() from exc
    audit_ata(session, ata, "ata.editada", actor, correlation_id, at, previous=previous)
    return ata


def move(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    move_name: str,
    justification: str | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Ata:
    """Move an ATA along its lifecycle (AC-0002-10, -22).

    The set of moves is fixed in `MOVES`. Anything else, including any move out of
    `encerrada` or `cancelada`, is refused and changes nothing.
    """
    allowed_from, destination, acao = MOVES[move_name]
    ata = lock_ata(session, ata_id)
    if ata.status not in allowed_from:
        raise TransicaoInvalida(ata.status, destination)
    if destination == "encerrada":
        pending = ne_repo.of_ata_in(session, ata.id, NE_IN_PROGRESS)
        if pending:
            # RN13: closing would orphan the commitments in flight (AC-0004-25).
            raise AtaComNePendente(ata.number, [ne.processo_sei for ne in pending])

    previous = ata.status
    ata.status = destination
    ata.atualizado_em = at
    session.flush()
    audit_ata(
        session,
        ata,
        acao,
        actor,
        correlation_id,
        at,
        previous={"status": previous},
        justification=justification,
    )
    return ata


def add_aditivo(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    kind: str,
    valor_acrescimo: decimal.Decimal | None,
    nova_vigencia_fim: datetime.date | None,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> AtaAditivo:
    """Record an aditivo of value or of prazo on a vigente ATA (AC-0002-13, -14)."""
    ata = lock_ata(session, ata_id)
    if ata.status != "vigente":
        raise AtaNaoVigente()

    previous: dict[str, Any]
    if kind == "valor":
        if valor_acrescimo is None or valor_acrescimo <= 0:
            raise InvalidData({"valor_acrescimo": "Informe um valor maior que zero."})
        already = repo.sum_aditivos_de_valor(session, ata.id)
        if already + valor_acrescimo > ata.total_value * ADITIVO_CEILING:
            raise AditivoAcimaDoLimite()
        previous = {"valor_contratado": str(ata.total_value + already)}
        nova_vigencia_fim = None
    else:
        if nova_vigencia_fim is None or nova_vigencia_fim <= ata.vigencia_fim:
            raise InvalidData({"nova_vigencia_fim": "Informe uma data depois do fim atual."})
        previous = {"vigencia_fim": ata.vigencia_fim}
        ata.vigencia_fim = nova_vigencia_fim
        ata.atualizado_em = at
        valor_acrescimo = None

    aditivo = repo.add_aditivo(
        session,
        AtaAditivo(
            ata_id=ata.id,
            kind=kind,
            valor_acrescimo=valor_acrescimo,
            nova_vigencia_fim=nova_vigencia_fim,
            justification=justification,
            created_by=actor.id,
            criado_em=at,
        ),
    )
    audit_ata(
        session,
        ata,
        "ata.aditivo_registrado",
        actor,
        correlation_id,
        at,
        previous=previous,
        justification=justification,
    )
    return aditivo


def add_reajuste(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    processo: str,
    requested_on: datetime.date,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> AtaReajuste:
    """Record that a reajuste request was filed in SEI (AC-0002-19, -21).

    It records the request and changes no price: applying a new price needs the
    index and the approver, which nobody has said (OQ-08).
    """
    if not processo_sei.is_valid(processo):
        raise ProcessoSeiInvalido(PROCESSO_SEI_FORMAT)
    ata = lock_ata(session, ata_id)
    if ata.status != "vigente":
        raise AtaNaoVigente()

    reajuste = repo.add_reajuste(
        session,
        AtaReajuste(
            ata_id=ata.id,
            processo_sei=processo.strip(),
            requested_on=requested_on,
            created_by=actor.id,
            criado_em=at,
        ),
    )
    audit_ata(session, ata, "ata.reajuste_registrado", actor, correlation_id, at, previous=None)
    return reajuste


def get(session: Session, ata_id: uuid.UUID, *, at: datetime.datetime) -> AtaDetail:
    """One ATA with its aditivos and reajuste requests (AC-0002-23)."""
    ata = repo.by_id(session, ata_id)
    if ata is None:
        raise AtaNotFound()
    view = _view(session, ata, at)
    return AtaDetail(
        ata=view.ata,
        fornecedor=view.fornecedor,
        valor_contratado=view.valor_contratado,
        situacao_vigencia=view.situacao_vigencia,
        data_reajuste=view.data_reajuste,
        aditivos=repo.aditivos_of(session, ata.id),
        reajustes=repo.reajustes_of(session, ata.id),
    )


def list_atas(
    session: Session,
    *,
    page: int,
    size: int,
    status: str | None,
    situacao: str | None,
    at: datetime.datetime,
) -> tuple[list[AtaView], int]:
    """One page of ATAs, filtered by status and by the derived situacao (AC-0002-23)."""
    today = local_date(at)
    window = get_settings().ata_alert_days
    horizon = today + datetime.timedelta(days=window)
    fim_from: datetime.date | None = None
    fim_to: datetime.date | None = None
    if situacao == "vencida":
        fim_to = today - datetime.timedelta(days=1)
    elif situacao == "a_vencer":
        fim_from, fim_to = today, horizon
    elif situacao == "vigente":
        fim_from = horizon + datetime.timedelta(days=1)
    rows, total = repo.list_page(
        session, page=page, size=size, status=status, fim_from=fim_from, fim_to=fim_to
    )
    return [_view(session, ata, at) for ata in rows], total


def renewal_alert(session: Session, *, at: datetime.datetime) -> list[AlertItem]:
    """ATAs about to end, with no aditivo de prazo, soonest first (AC-0002-09)."""
    today = local_date(at)
    horizon = today + datetime.timedelta(days=get_settings().ata_alert_days)
    return [
        AlertItem(view=_view(session, ata, at), days_remaining=(ata.vigencia_fim - today).days)
        for ata in repo.renewal_alert(session, until=horizon)
    ]


def reajuste_alert(session: Session, *, at: datetime.datetime) -> list[AlertItem]:
    """ATAs whose reajuste is near or past, with no request, soonest first (AC-0002-20)."""
    today = local_date(at)
    horizon = today + datetime.timedelta(days=get_settings().ata_alert_days)
    return [
        AlertItem(
            view=_view(session, ata, at),
            days_remaining=(reajuste_date(ata.budget_date) - today).days,
        )
        for ata in repo.reajuste_alert(session, until=horizon)
    ]


def lock_ata(session: Session, ata_id: uuid.UUID) -> Ata:
    """Find an ATA and lock it for this transaction, or refuse with 404."""
    ata = repo.by_id_for_update(session, ata_id)
    if ata is None:
        raise AtaNotFound()
    return ata


def _view(session: Session, ata: Ata, at: datetime.datetime) -> AtaView:
    supplier = repo.fornecedor_by_id(session, ata.fornecedor_id)
    assert supplier is not None  # the FK guarantees it
    return AtaView(
        ata=ata,
        fornecedor=supplier,
        valor_contratado=ata.total_value + repo.sum_aditivos_de_valor(session, ata.id),
        situacao_vigencia=situacao_vigencia(
            ata.vigencia_fim, local_date(at), get_settings().ata_alert_days
        ),
        data_reajuste=reajuste_date(ata.budget_date),
    )


def _require_interval(start: datetime.date, end: datetime.date) -> None:
    if end <= start:
        raise InvalidData({"vigencia_fim": "A vigência precisa terminar depois de começar."})


def find_or_create_fornecedor(session: Session, given: FornecedorInput) -> Fornecedor:
    """Find a fornecedor by its CNPJ, or create it, the check digits validated (AC-0002-25)."""
    if not cnpj_lib.is_valid(given.cnpj):
        raise InvalidData({"fornecedor.cnpj": "CNPJ inválido."})
    cnpj = cnpj_lib.normalise(given.cnpj)
    existing = repo.fornecedor_by_cnpj(session, cnpj)
    if existing is not None:
        # The razão social already on record is kept: an ATA is not the place to
        # rename a company.
        return existing
    return repo.create_fornecedor(session, cnpj=cnpj, legal_name=given.legal_name.strip())


def audit_ata(
    session: Session,
    ata: Ata,
    acao: str,
    actor: User,
    correlation_id: uuid.UUID,
    at: datetime.datetime,
    *,
    previous: dict[str, Any] | None,
    justification: str | None = None,
) -> None:
    """Write the audit row of a mutation on an ATA, in the caller's transaction."""
    record(
        session,
        Event(
            entidade_tipo="ata",
            entidade_id=ata.id,
            acao=acao,
            user_id=actor.id,
            dados_anteriores=jsonable(previous) if previous is not None else None,
            justificativa=justification,
        ),
        correlation_id=correlation_id,
        at=at,
    )


def jsonable(values: dict[str, Any]) -> dict[str, Any]:
    """Make prior values storable as JSON: dates as ISO text, money and ids as text."""
    return {
        key: value.isoformat()
        if isinstance(value, datetime.date)
        else str(value)
        if isinstance(value, decimal.Decimal | uuid.UUID)
        else value
        for key, value in values.items()
    }
