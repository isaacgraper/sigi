"""The NE flow: opening, the itens, the five stages, reversal and cancellation (SPEC-0004).

The guard into `pre_empenho` reads saldo with the ATA row locked, in the same
transaction as the status change (AC-0004-13). Reading saldo and writing the
status in two transactions is the defect that lets two NEs both pass.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.constants.atas import PROCESSO_SEI_FORMAT
from app.constants.notas_empenho import (
    ACAO_AVANCADA,
    ACAO_BLOQUEADA,
    ACAO_CANCELADA,
    ACAO_CRIADA,
    ACAO_ITENS,
    ACAO_REVERTIDA,
    CANCELADA,
    ENTIDADE,
    ITEMS_EDITABLE,
    NUMERO_PATTERN,
    RESERVING,
    STAGE_LABEL,
    STAGES,
    TERMINAL,
)
from app.core import processo_sei
from app.core.clock import local_date
from app.models.ata import Ata
from app.models.insumo import Insumo, ItemAta
from app.models.nota_empenho import ItemNotaEmpenho, NotaEmpenho
from app.models.user import User
from app.repositories import ata as ata_repo
from app.repositories import insumo as insumo_repo
from app.repositories import item_ata as item_repo
from app.repositories import nota_empenho as repo
from app.services import saldo as saldo_service
from app.services.atas import jsonable, lock_ata
from app.services.audit import Event, record, record_standalone
from app.services.errors import (
    AtaNaoElegivel,
    AtaNotFound,
    InvalidData,
    ItemDeOutraAta,
    ItemDuplicado,
    NeDuplicada,
    NeItensCongelados,
    NeNotFound,
    NeSemItens,
    NeTransicaoInvalida,
    PreEmpenhoDuplicado,
    ProcessoSeiInvalido,
    QuantidadeInsuficiente,
    SaldoInsuficiente,
)
from app.services.itens_ata import item_value

ZERO = decimal.Decimal("0")


@dataclass(frozen=True)
class LineInput:
    """One line as the caller sends it: the price is the ATA's, never the caller's (I5)."""

    item_ata_id: uuid.UUID
    quantity: decimal.Decimal


@dataclass(frozen=True)
class Line:
    """One line of an NE with what a reader needs to name it."""

    line: ItemNotaEmpenho
    item: ItemAta
    insumo: Insumo


@dataclass(frozen=True)
class NeView:
    """An NE with its lines and its derived value."""

    ne: NotaEmpenho
    ata: Ata
    lines: list[Line]

    @property
    def value(self) -> decimal.Decimal:
        """Σ of the lines: the NE's value is never stored (ADR-0007)."""
        return sum((line.line.value for line in self.lines), ZERO)


@dataclass(frozen=True)
class Indicators:
    """The stage counters of the NE module (AC-0004-18)."""

    emitidas: int
    em_andamento: int
    total: int


def brl(value: decimal.Decimal) -> str:
    """R$ 1.234,56, for messages the servidor reads."""
    text = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {text}"


def open_ne(
    session: Session,
    *,
    actor: User,
    ata_id: uuid.UUID,
    processo: str,
    lines: Sequence[LineInput],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NeView:
    """Open an NE in `demanda` against an eligible ATA (AC-0004-01 to -03, -17, -20, -21)."""
    processo = processo.strip()
    if not processo_sei.is_valid(processo):
        raise ProcessoSeiInvalido(PROCESSO_SEI_FORMAT)
    ata = ata_repo.by_id(session, ata_id)
    if ata is None:
        raise InvalidData({"ata_id": "ATA não encontrada."})
    _require_eligible(ata, local_date(at))
    ne = repo.add(
        session,
        NotaEmpenho(processo_sei=processo, ata_id=ata.id, owner_id=actor.id, status=STAGES[0]),
    )
    repo.replace_lines(session, ne.id, _build_lines(session, ata, ne.id, lines))
    _audit(session, ne, ACAO_CRIADA, actor, correlation_id, at, previous=None)
    return view(session, ne)


def replace_items(
    session: Session,
    *,
    actor: User,
    ne_id: uuid.UUID,
    lines: Sequence[LineInput],
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NeView:
    """Replace the itens of an NE before saldo is reserved (AC-0004-19, -22)."""
    ne = _lock(session, ne_id)
    if ne.status not in ITEMS_EDITABLE:
        raise NeItensCongelados()
    if not lines:
        raise NeSemItens()
    ata = ata_repo.by_id(session, ne.ata_id)
    assert ata is not None  # the FK guarantees it
    previous = [
        {"item_ata_id": str(line.line.item_ata_id), "quantidade": str(line.line.quantity)}
        for line in view(session, ne).lines
    ]
    repo.replace_lines(session, ne.id, _build_lines(session, ata, ne.id, lines))
    ne.atualizado_em = at
    _audit(session, ne, ACAO_ITENS, actor, correlation_id, at, previous={"itens": previous})
    return view(session, ne)


def advance(
    session: Session,
    *,
    actor: User,
    ne_id: uuid.UUID,
    to: str | None,
    numero_pre_empenho: str | None,
    numero: str | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NeView:
    """Move an NE one stage forward, through the saldo guard into `pre_empenho`.

    A refusal by the flow or by the guard is recorded as `ne.bloqueada` in a
    transaction of its own, because the 409 rolls the request's back.
    """
    ne = _lock(session, ne_id)
    target = _next(ne.status)
    if target is None or (to is not None and to != target):
        _blocked(ne, "TRANSICAO_INVALIDA", actor, correlation_id, saldo=None)
        raise NeTransicaoInvalida(STAGE_LABEL[ne.status], STAGE_LABEL.get(to or "", to or "—"))

    previous_status = ne.status
    if target == "pre_empenho":
        ne.numero_pre_empenho = _numero(
            session, numero_pre_empenho, "numero_pre_empenho", ne, pre_empenho=True
        )
        reservado_antes = _guard(session, ne, actor, correlation_id, at)
    else:
        reservado_antes = saldo_service.compute(session, _ata(session, ne), at=at).valor_reservado
    if target == "ne_emitida":
        ne.numero = _numero(session, numero, "number", ne, pre_empenho=False)
        ne.issued_on = local_date(at)

    ne.status = target
    ne.atualizado_em = at
    session.flush()
    _audit(
        session,
        ne,
        ACAO_AVANCADA,
        actor,
        correlation_id,
        at,
        previous={"status": previous_status, "valor_reservado_ata": reservado_antes},
    )
    return view(session, ne)


def reverse(
    session: Session,
    *,
    actor: User,
    ne_id: uuid.UUID,
    to: str | None,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NeView:
    """Move an NE one stage back, with a justification (AC-0004-06, -07, -10, RN03).

    Leaving `pre_empenho` clears its número, since the reservation it recorded
    no longer holds; the audit row keeps it (AC-0004-29).
    """
    ne = _lock(session, ne_id)
    target = _previous(ne.status)
    if target is None or (to is not None and to != target):
        _blocked(ne, "TRANSICAO_INVALIDA", actor, correlation_id, saldo=None)
        raise NeTransicaoInvalida(STAGE_LABEL[ne.status], STAGE_LABEL.get(to or "", to or "—"))
    previous: dict[str, object] = {"status": ne.status}
    if ne.status == "pre_empenho":
        previous["numero_pre_empenho"] = ne.numero_pre_empenho
        ne.numero_pre_empenho = None
    ne.status = target
    ne.atualizado_em = at
    session.flush()
    _audit(
        session,
        ne,
        ACAO_REVERTIDA,
        actor,
        correlation_id,
        at,
        previous=previous,
        justification=justification.strip(),
    )
    return view(session, ne)


def cancel(
    session: Session,
    *,
    actor: User,
    ne_id: uuid.UUID,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NeView:
    """Cancel an NE that is not terminal, releasing what it reserved (AC-0004-16)."""
    ne = _lock(session, ne_id)
    if ne.status in TERMINAL:
        _blocked(ne, "TRANSICAO_INVALIDA", actor, correlation_id, saldo=None)
        raise NeTransicaoInvalida(STAGE_LABEL[ne.status], STAGE_LABEL[CANCELADA])
    released = view(session, ne).value if ne.status in RESERVING else ZERO
    previous = {"status": ne.status, "valor_liberado": released}
    ne.status = CANCELADA
    ne.atualizado_em = at
    session.flush()
    _audit(
        session,
        ne,
        ACAO_CANCELADA,
        actor,
        correlation_id,
        at,
        previous=previous,
        justification=justification.strip(),
    )
    return view(session, ne)


def get(session: Session, ne_id: uuid.UUID) -> NeView:
    """One NE with its lines, or 404."""
    ne = repo.by_id(session, ne_id)
    if ne is None:
        raise NeNotFound()
    return view(session, ne)


def list_nes(
    session: Session,
    *,
    status: str | None,
    ata_id: uuid.UUID | None,
    processo: str | None,
    page: int,
    size: int,
) -> tuple[list[NeView], int]:
    """A page of NEs, newest first, with their lines."""
    rows, total = repo.page(
        session,
        status=status,
        ata_id=ata_id,
        processo_sei=processo,
        offset=(page - 1) * size,
        limit=size,
    )
    return views(session, list(rows)), total


def indicators(session: Session) -> Indicators:
    """Emitidas, em andamento and total; a cancelled NE counts only in the total."""
    counts = repo.count_by_status(session)
    return Indicators(
        emitidas=counts.get("ne_emitida", 0),
        em_andamento=sum(counts.get(s, 0) for s in STAGES if s not in TERMINAL),
        total=sum(counts.values()),
    )


def view(session: Session, ne: NotaEmpenho) -> NeView:
    """An NE with its lines."""
    return views(session, [ne])[0]


def views(session: Session, nes: list[NotaEmpenho]) -> list[NeView]:
    """These NEs with their lines, in one query for the lines."""
    by_ne: dict[uuid.UUID, list[Line]] = {ne.id: [] for ne in nes}
    for line, item, insumo in repo.lines(session, list(by_ne)):
        by_ne[line.nota_empenho_id].append(Line(line=line, item=item, insumo=insumo))
    atas = {ne.ata_id: _ata(session, ne) for ne in nes}
    return [NeView(ne=ne, ata=atas[ne.ata_id], lines=by_ne[ne.id]) for ne in nes]


# ── Rules ───────────────────────────────────────────────────────────────────


def _require_eligible(ata: Ata, today: datetime.date) -> None:
    """RN11: vigente, and its vigência covers today (AC-0004-17)."""
    motivo = (
        ata.status
        if ata.status != "vigente"
        else "vencida"
        if ata.vigencia_fim < today
        else "não iniciada"
        if ata.vigencia_inicio > today
        else None
    )
    if motivo is not None:
        raise AtaNaoElegivel(ata.number, motivo)


def _build_lines(
    session: Session, ata: Ata, ne_id: uuid.UUID, lines: Sequence[LineInput]
) -> list[ItemNotaEmpenho]:
    """Resolve each line to an item of this ATA and copy its price (AC-0004-20, -21, -23)."""
    items = item_repo.by_ids(session, [line.item_ata_id for line in lines])
    insumos = insumo_repo.insumos_by_id(session, [item.insumo_id for item in items.values()])
    seen: set[uuid.UUID] = set()
    built: list[ItemNotaEmpenho] = []
    for index, line in enumerate(lines):
        item = items.get(line.item_ata_id)
        if item is None or item.removed_at is not None:
            raise InvalidData({f"itens.{index}.item_ata_id": "Item da ATA não encontrado."})
        insumo = insumos[item.insumo_id]
        if item.ata_id != ata.id:
            other = ata_repo.by_id(session, item.ata_id)
            raise ItemDeOutraAta(insumo.description, other.number if other else "outra ATA")
        if item.id in seen:
            raise ItemDuplicado(insumo.description)
        seen.add(item.id)
        built.append(
            ItemNotaEmpenho(
                nota_empenho_id=ne_id,
                item_ata_id=item.id,
                quantity=line.quantity,
                unit_price=item.unit_price,
                value=item_value(line.quantity, item.unit_price),
            )
        )
    return built


def _guard(
    session: Session,
    ne: NotaEmpenho,
    actor: User,
    correlation_id: uuid.UUID,
    at: datetime.datetime,
) -> decimal.Decimal:
    """RN10: refuse on value first, then on quantity, with the ATA row locked.

    Returns the ATA's reserved value before this NE, for the audit row.
    """
    ata = lock_ata(session, ne.ata_id)
    saldo = saldo_service.compute(session, ata, at=at)
    current = view(session, ne)
    if current.value > saldo.saldo_disponivel:
        _blocked(ne, "SALDO_INSUFICIENTE", actor, correlation_id, saldo=saldo.saldo_disponivel)
        raise SaldoInsuficiente(ata.number, brl(saldo.saldo_disponivel), brl(current.value))
    available = {
        s.item.id: s
        for s in saldo_service.items_saldo(session, [line.item for line in current.lines])
    }
    for line in current.lines:
        left = available[line.item.id].quantidade_disponivel
        if line.line.quantity > left:
            _blocked(
                ne, "QUANTIDADE_INSUFICIENTE", actor, correlation_id, saldo=saldo.saldo_disponivel
            )
            raise QuantidadeInsuficiente(
                line.insumo.description, ata.number, _qty(left), _qty(line.line.quantity)
            )
    return saldo.valor_reservado


def _numero(
    session: Session, given: str | None, field: str, ne: NotaEmpenho, *, pre_empenho: bool
) -> str:
    """A número typed in as issued: required, letters and digits, unique (AC-0004-28, -29)."""
    value = (given or "").strip()
    if not value:
        raise InvalidData({field: "Informe o número."})
    if not NUMERO_PATTERN.fullmatch(value):
        raise InvalidData({field: "Use até 20 letras e números."})
    holder = (
        repo.by_numero_pre_empenho(session, value)
        if pre_empenho
        else repo.by_numero(session, value)
    )
    if holder is not None and holder.id != ne.id:
        raise PreEmpenhoDuplicado(value) if pre_empenho else NeDuplicada(value)
    return value


def _next(status: str) -> str | None:
    if status in TERMINAL:
        return None
    return STAGES[STAGES.index(status) + 1]


def _previous(status: str) -> str | None:
    if status in TERMINAL or status == STAGES[0]:
        return None
    return STAGES[STAGES.index(status) - 1]


def _lock(session: Session, ne_id: uuid.UUID) -> NotaEmpenho:
    ne = repo.by_id_for_update(session, ne_id)
    if ne is None:
        raise NeNotFound()
    return ne


def _ata(session: Session, ne: NotaEmpenho) -> Ata:
    ata = ata_repo.by_id(session, ne.ata_id)
    if ata is None:  # pragma: no cover - the FK guarantees it
        raise AtaNotFound()
    return ata


def _qty(value: decimal.Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",")


def _audit(
    session: Session,
    ne: NotaEmpenho,
    acao: str,
    actor: User,
    correlation_id: uuid.UUID,
    at: datetime.datetime,
    *,
    previous: dict[str, object] | None,
    justification: str | None = None,
) -> None:
    record(
        session,
        Event(
            entidade_tipo=ENTIDADE,
            entidade_id=ne.id,
            acao=acao,
            user_id=actor.id,
            dados_anteriores=jsonable(previous) if previous is not None else None,
            justificativa=justification,
        ),
        correlation_id=correlation_id,
        at=at,
    )


def _blocked(
    ne: NotaEmpenho,
    motivo: str,
    actor: User,
    correlation_id: uuid.UUID,
    *,
    saldo: decimal.Decimal | None,
) -> None:
    """A refused move, kept on purpose: repeated blocks on one ATA are the gargalo (§8)."""
    record_standalone(
        Event(
            entidade_tipo=ENTIDADE,
            entidade_id=ne.id,
            acao=ACAO_BLOQUEADA,
            user_id=actor.id,
            dados_anteriores={
                "status": ne.status,
                "motivo": motivo,
                "saldo_disponivel": str(saldo) if saldo is not None else None,
            },
        ),
        correlation_id=correlation_id,
    )
