"""The NF conference: registration, correction, the four statuses and quarantine (SPEC-0005).

Every write locks the NE row first, so two NFs of one NE are checked against
each other's value and quantities in turn, never both against the same total.
The NF reaches its ATA only through the NE (RN02).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.constants.notas_empenho import NUMERO_PATTERN, ZERO
from app.constants.notas_empenho import STAGE_LABEL as NE_STAGE_LABEL
from app.constants.notas_fiscais import (
    ACAO_APROVADA,
    ACAO_CORRIGIDA,
    ACAO_DEVOLVIDA,
    ACAO_ENVIADA,
    ACAO_LIBERADA,
    ACAO_QUARENTENA,
    ACAO_REGISTRADA,
    AGUARDANDO,
    APROVADA,
    COUNTED,
    DEVOLVIDA,
    EDITABLE,
    EM_CONFERENCIA,
    ENTIDADE,
    LIBERADA_LABEL,
    NE_EMITIDA,
    QUARANTINABLE,
    QUARENTENA_LABEL,
    SENDABLE,
    STATUS_LABEL,
)
from app.core import cnpj as cnpj_rules
from app.core.clock import local_date
from app.models.insumo import Insumo, ItemAta
from app.models.nota_empenho import ItemNotaEmpenho, NotaEmpenho
from app.models.nota_fiscal import ItemNotaFiscal, NotaFiscal
from app.models.user import User
from app.repositories import ata as ata_repo
from app.repositories import nota_empenho as ne_repo
from app.repositories import nota_fiscal as repo
from app.services.atas import jsonable
from app.services.audit import Event, record
from app.services.errors import (
    DataAnteriorAoEmpenho,
    FornecedorDivergente,
    InvalidData,
    NeNaoEmitida,
    NeNotFound,
    NfDuplicada,
    NfEmQuarentena,
    NfItemDuplicado,
    NfNaoEditavel,
    NfNotFound,
    NfTransicaoInvalida,
    QuantidadeAcimaDoEmpenho,
    ValorAcimaDoEmpenho,
)
from app.services.notas_empenho import brl


@dataclass(frozen=True)
class LineInput:
    """One line as the caller sends it: a line of the NE and how much of it arrived."""

    item_nota_empenho_id: uuid.UUID
    quantity: decimal.Decimal


@dataclass(frozen=True)
class NfInput:
    """What the servidor types from the document, for registering or correcting."""

    numero: str
    data_emissao: datetime.date
    valor: decimal.Decimal
    fornecedor_cnpj: str
    lines: Sequence[LineInput]


@dataclass(frozen=True)
class NfLine:
    """One line of an NF with what a reader needs to name it."""

    line: ItemNotaFiscal
    ne_line: ItemNotaEmpenho
    item: ItemAta
    insumo: Insumo


@dataclass(frozen=True)
class NfView:
    """An NF with its NE and its lines."""

    nf: NotaFiscal
    ne: NotaEmpenho
    lines: list[NfLine]


@dataclass(frozen=True)
class LineQuantities:
    """What an NE line received, holds in quarantine and still waits for (AC-0005-10, -13)."""

    recebida: decimal.Decimal
    em_quarentena: decimal.Decimal
    faltante: decimal.Decimal


def register(
    session: Session,
    *,
    actor: User,
    nota_empenho_id: uuid.UUID,
    data: NfInput,
    confirmar_data_anterior: bool,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Register an NF in `aguardando` against an issued NE (AC-0005-01 to -07, -12, -15)."""
    ne = ne_repo.by_id_for_update(session, nota_empenho_id)
    if ne is None:
        raise NeNotFound()
    numero, fornecedor_id = _check(session, ne, data, confirmar_data_anterior, at=at, nf_id=None)
    nf = repo.add(
        session,
        NotaFiscal(
            numero=numero,
            issued_on=data.data_emissao,
            value=data.valor,
            nota_empenho_id=ne.id,
            fornecedor_id=fornecedor_id,
            owner_id=actor.id,
            status=AGUARDANDO,
            quarentena=False,
        ),
    )
    repo.replace_lines(session, nf.id, _build_lines(nf.id, data.lines))
    previous: dict[str, object] | None = (
        {"confirmar_data_anterior": True} if _back_dated(ne, data) else None
    )
    _audit(session, nf, ACAO_REGISTRADA, actor, correlation_id, at, previous=previous)
    return view(session, nf)


def correct(
    session: Session,
    *,
    actor: User,
    nf_id: uuid.UUID,
    data: NfInput,
    confirmar_data_anterior: bool,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Correct an NF before conference, under every check again (AC-0005-14)."""
    nf, ne = _lock(session, nf_id)
    if nf.status not in EDITABLE:
        raise NfNaoEditavel(STATUS_LABEL[nf.status].lower())
    previous = _snapshot(session, nf)
    numero, fornecedor_id = _check(session, ne, data, confirmar_data_anterior, at=at, nf_id=nf.id)
    nf.numero = numero
    nf.issued_on = data.data_emissao
    nf.value = data.valor
    nf.fornecedor_id = fornecedor_id
    nf.atualizado_em = at
    session.flush()
    repo.replace_lines(session, nf.id, _build_lines(nf.id, data.lines))
    _audit(session, nf, ACAO_CORRIGIDA, actor, correlation_id, at, previous=previous)
    return view(session, nf)


def send(
    session: Session,
    *,
    actor: User,
    nf_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Send to conference; back from `devolvida` it counts again, so the caps re-run."""
    nf, ne = _lock(session, nf_id)
    if nf.status not in SENDABLE:
        raise NfTransicaoInvalida(STATUS_LABEL[nf.status], STATUS_LABEL[EM_CONFERENCIA])
    if nf.status == DEVOLVIDA:
        current = view(session, nf)
        _caps(
            session,
            ne,
            nf.value,
            [
                (line.ne_line, line.insumo, line.line.quantity, f"itens.{index}.quantidade")
                for index, line in enumerate(current.lines)
            ],
            nf_id=nf.id,
        )
    return _move(session, nf, EM_CONFERENCIA, ACAO_ENVIADA, actor, correlation_id, at)


def approve(
    session: Session,
    *,
    actor: User,
    nf_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Approve an NF in conference; `aprovada` is final (RF17)."""
    nf, _ = _lock(session, nf_id)
    if nf.status != EM_CONFERENCIA:
        raise NfTransicaoInvalida(STATUS_LABEL[nf.status], STATUS_LABEL[APROVADA])
    if nf.quarentena:
        raise NfEmQuarentena()
    return _move(session, nf, APROVADA, ACAO_APROVADA, actor, correlation_id, at)


def return_nf(
    session: Session,
    *,
    actor: User,
    nf_id: uuid.UUID,
    justification: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Return an NF in conference with a justificativa; it stops counting (RN12)."""
    justification = justification.strip()
    if not justification:
        raise InvalidData({"justificativa": "Informe a justificativa."})
    nf, _ = _lock(session, nf_id)
    if nf.status != EM_CONFERENCIA:
        raise NfTransicaoInvalida(STATUS_LABEL[nf.status], STATUS_LABEL[DEVOLVIDA])
    nf.return_reason = justification
    return _move(
        session,
        nf,
        DEVOLVIDA,
        ACAO_DEVOLVIDA,
        actor,
        correlation_id,
        at,
        extra={"justificativa": justification},
        justification=justification,
    )


def quarantine(
    session: Session,
    *,
    actor: User,
    nf_id: uuid.UUID,
    motivo: str,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Hold an NF still in the conference, with a motivo (AC-0005-13)."""
    motivo = motivo.strip()
    if not motivo:
        raise InvalidData({"motivo": "Informe o motivo."})
    nf, _ = _lock(session, nf_id)
    if nf.status not in QUARANTINABLE or nf.quarentena:
        raise NfTransicaoInvalida(STATUS_LABEL[nf.status], QUARENTENA_LABEL)
    nf.quarentena = True
    nf.motivo_quarentena = motivo
    nf.atualizado_em = at
    session.flush()
    _audit(session, nf, ACAO_QUARENTENA, actor, correlation_id, at, previous={"motivo": motivo})
    return view(session, nf)


def release(
    session: Session,
    *,
    actor: User,
    nf_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> NfView:
    """Release an NF from quarantine; its lines count as received again."""
    nf, _ = _lock(session, nf_id)
    if not nf.quarentena:
        raise NfTransicaoInvalida(STATUS_LABEL[nf.status], LIBERADA_LABEL)
    motivo = nf.motivo_quarentena
    nf.quarentena = False
    nf.motivo_quarentena = None
    nf.atualizado_em = at
    session.flush()
    _audit(session, nf, ACAO_LIBERADA, actor, correlation_id, at, previous={"motivo": motivo})
    return view(session, nf)


def get(session: Session, nf_id: uuid.UUID) -> NfView:
    """One NF with its lines, or 404."""
    nf = repo.by_id(session, nf_id)
    if nf is None:
        raise NfNotFound()
    return view(session, nf)


def list_nfs(
    session: Session,
    *,
    status: str | None,
    nota_empenho_id: uuid.UUID | None,
    quarentena: bool | None,
    page: int,
    size: int,
) -> tuple[list[NfView], int]:
    """A page of NFs, newest first, with their lines (AC-0005-16)."""
    rows, total = repo.page(
        session,
        status=status,
        nota_empenho_id=nota_empenho_id,
        quarentena=quarentena,
        offset=(page - 1) * size,
        limit=size,
    )
    return views(session, list(rows)), total


def view(session: Session, nf: NotaFiscal) -> NfView:
    """An NF with its lines."""
    return views(session, [nf])[0]


def views(session: Session, nfs: list[NotaFiscal]) -> list[NfView]:
    """These NFs with their lines, in one query for the lines."""
    by_nf: dict[uuid.UUID, list[NfLine]] = {nf.id: [] for nf in nfs}
    for line, ne_line, item, insumo in repo.lines(session, list(by_nf)):
        by_nf[line.nota_fiscal_id].append(
            NfLine(line=line, ne_line=ne_line, item=item, insumo=insumo)
        )
    nes = {nf.nota_empenho_id: ne_repo.by_id(session, nf.nota_empenho_id) for nf in nfs}
    return [NfView(nf=nf, ne=nes[nf.nota_empenho_id], lines=by_nf[nf.id]) for nf in nfs]  # type: ignore[arg-type]


def ne_quantities(
    session: Session, ne_lines: Sequence[ItemNotaEmpenho]
) -> dict[uuid.UUID, LineQuantities]:
    """Recebida, em quarentena and faltante of each NE line, from the NFs that count.

    Never saldo: what an NE waits for is the NE's, and the ATA's saldo is untouched
    by a launch (AC-0005-10, ADR-0015).
    """
    totals = repo.quantity_by_line(session, [line.id for line in ne_lines], COUNTED)
    result: dict[uuid.UUID, LineQuantities] = {}
    for line in ne_lines:
        recebida = totals.get((line.id, False), ZERO)
        result[line.id] = LineQuantities(
            recebida=recebida,
            em_quarentena=totals.get((line.id, True), ZERO),
            faltante=line.quantity - recebida,
        )
    return result


# ── Rules ───────────────────────────────────────────────────────────────────


def _check(
    session: Session,
    ne: NotaEmpenho,
    data: NfInput,
    confirmar_data_anterior: bool,
    *,
    at: datetime.datetime,
    nf_id: uuid.UUID | None,
) -> tuple[str, uuid.UUID]:
    """Every rule of a registration or correction, in the order the servidor fixes them.

    Returns the número as stored and the ATA's fornecedor id.
    """
    numero = data.numero.strip()
    if not numero:
        raise InvalidData({"numero": "Informe o número."})
    if not NUMERO_PATTERN.fullmatch(numero):
        raise InvalidData({"numero": "Use até 20 letras e números."})
    typed_cnpj = cnpj_rules.normalise(data.fornecedor_cnpj)
    if not typed_cnpj:
        raise InvalidData({"fornecedor_cnpj": "Informe o CNPJ do fornecedor."})
    if not cnpj_rules.is_valid(typed_cnpj):
        raise InvalidData({"fornecedor_cnpj": "Informe um CNPJ válido."})
    if not data.lines:
        raise InvalidData({"itens": "Informe ao menos um item."})
    if ne.status != NE_EMITIDA:
        raise NeNaoEmitida(NE_STAGE_LABEL[ne.status])
    if data.data_emissao > local_date(at):
        raise InvalidData({"data_emissao": "A data de emissão não pode ser futura."})
    if _back_dated(ne, data) and not confirmar_data_anterior:
        assert ne.issued_on is not None  # an issued NE carries its date
        raise DataAnteriorAoEmpenho(_date(data.data_emissao), _date(ne.issued_on))
    fornecedor_id = _fornecedor(session, ne, typed_cnpj)
    lines = _resolve(session, ne, data.lines)
    _caps(session, ne, data.valor, lines, nf_id=nf_id)
    holder = repo.by_numero(session, numero, fornecedor_id)
    if holder is not None and holder.id != nf_id:
        raise NfDuplicada(numero)
    return numero, fornecedor_id


def _back_dated(ne: NotaEmpenho, data: NfInput) -> bool:
    return ne.issued_on is not None and data.data_emissao < ne.issued_on


def _fornecedor(session: Session, ne: NotaEmpenho, typed_cnpj: str) -> uuid.UUID:
    """The ATA's fornecedor, which the NF's CNPJ must be (AC-0005-06)."""
    ata = ata_repo.by_id(session, ne.ata_id)
    fornecedor = ata_repo.fornecedor_by_id(session, ata.fornecedor_id) if ata else None
    if fornecedor is None:  # pragma: no cover - the FKs guarantee it
        raise NeNotFound()
    if cnpj_rules.normalise(fornecedor.cnpj) != typed_cnpj:
        raise FornecedorDivergente(
            _masked(typed_cnpj), fornecedor.legal_name, _masked(fornecedor.cnpj)
        )
    return fornecedor.id


def _resolve(
    session: Session, ne: NotaEmpenho, lines: Sequence[LineInput]
) -> list[tuple[ItemNotaEmpenho, Insumo, decimal.Decimal, str]]:
    """Each line to a line of this NE, once (AC-0005-12, DB14)."""
    of_ne = {line.id: (line, insumo) for line, _, insumo in ne_repo.lines(session, [ne.id])}
    seen: set[uuid.UUID] = set()
    resolved: list[tuple[ItemNotaEmpenho, Insumo, decimal.Decimal, str]] = []
    for index, line in enumerate(lines):
        field = f"itens.{index}.item_nota_empenho_id"
        found = of_ne.get(line.item_nota_empenho_id)
        if found is None:
            raise InvalidData({field: "Item da NE não encontrado."})
        if line.quantity <= 0:
            raise InvalidData({f"itens.{index}.quantidade": "Informe a quantidade."})
        ne_line, insumo = found
        if ne_line.id in seen:
            raise NfItemDuplicado(insumo.description, field)
        seen.add(ne_line.id)
        resolved.append((ne_line, insumo, line.quantity, f"itens.{index}.quantidade"))
    return resolved


def _caps(
    session: Session,
    ne: NotaEmpenho,
    valor: decimal.Decimal,
    lines: Sequence[tuple[ItemNotaEmpenho, Insumo, decimal.Decimal, str]],
    *,
    nf_id: uuid.UUID | None,
) -> None:
    """RN12 on value, then the quantity of each line, quarantine counted (AC-0005-07, -12)."""
    ne_value = sum((line.value for line, _, _ in ne_repo.lines(session, [ne.id])), ZERO)
    billed = repo.value_of_ne(session, ne.id, COUNTED, excluding=nf_id) + valor
    if billed > ne_value:
        raise ValorAcimaDoEmpenho(brl(billed), brl(ne_value))
    totals = repo.quantity_by_line(
        session, [line.id for line, _, _, _ in lines], COUNTED, excluding=nf_id
    )
    for ne_line, insumo, quantity, _ in lines:
        delivered = (
            totals.get((ne_line.id, False), ZERO) + totals.get((ne_line.id, True), ZERO) + quantity
        )
        if delivered > ne_line.quantity:
            raise QuantidadeAcimaDoEmpenho(
                insumo.description, _qty(delivered), _qty(ne_line.quantity)
            )


def _build_lines(nf_id: uuid.UUID, lines: Sequence[LineInput]) -> list[ItemNotaFiscal]:
    return [
        ItemNotaFiscal(
            nota_fiscal_id=nf_id,
            item_nota_empenho_id=line.item_nota_empenho_id,
            quantity=line.quantity,
        )
        for line in lines
    ]


def _snapshot(session: Session, nf: NotaFiscal) -> dict[str, object]:
    """The values a correction replaces, for the audit row."""
    return {
        "numero": nf.numero,
        "data_emissao": nf.issued_on,
        "valor": nf.value,
        "itens": [
            {
                "item_nota_empenho_id": str(line.line.item_nota_empenho_id),
                "quantidade": str(line.line.quantity),
            }
            for line in view(session, nf).lines
        ],
    }


def _move(
    session: Session,
    nf: NotaFiscal,
    status: str,
    acao: str,
    actor: User,
    correlation_id: uuid.UUID,
    at: datetime.datetime,
    *,
    extra: dict[str, object] | None = None,
    justification: str | None = None,
) -> NfView:
    previous: dict[str, object] = {"status": nf.status, **(extra or {})}
    nf.status = status
    nf.atualizado_em = at
    session.flush()
    _audit(
        session, nf, acao, actor, correlation_id, at, previous=previous, justification=justification
    )
    return view(session, nf)


def _lock(session: Session, nf_id: uuid.UUID) -> tuple[NotaFiscal, NotaEmpenho]:
    """The NE row first, then the NF: the order every NF write takes, so none deadlock."""
    nf = repo.by_id(session, nf_id)
    if nf is None:
        raise NfNotFound()
    ne = ne_repo.by_id_for_update(session, nf.nota_empenho_id)
    locked = repo.by_id_for_update(session, nf_id)
    if ne is None or locked is None:  # pragma: no cover - the FK guarantees it
        raise NfNotFound()
    session.refresh(locked)
    return locked, ne


def _date(value: datetime.date) -> str:
    return value.strftime("%d/%m/%Y")


def _masked(value: str) -> str:
    """12.345.678/0001-90, the way the document prints it."""
    v = cnpj_rules.normalise(value)
    return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}" if len(v) == 14 else v


def _qty(value: decimal.Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",")


def _audit(
    session: Session,
    nf: NotaFiscal,
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
            entidade_id=nf.id,
            acao=acao,
            user_id=actor.id,
            dados_anteriores=jsonable(previous) if previous is not None else None,
            justificativa=justification,
        ),
        correlation_id=correlation_id,
        at=at,
    )
