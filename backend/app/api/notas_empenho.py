"""NE routes (SPEC-0004 §7) and the saldo reads of an ATA (SPEC-0006 §3.1).

Reads are open to the three perfis. Opening, the itens, reversal and
cancellation are the gestor's; advancing is the gestor's and the servidor's
(SPEC-0004 §6), enforced here on the route, which is the only place it counts.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import DbSession
from app.models.user import User
from app.schemas.nota_empenho import (
    AdvanceIn,
    CancelNeIn,
    IndicatorsOut,
    ItemsIn,
    LineIn,
    LineOut,
    NotaEmpenhoIn,
    NotaEmpenhoOut,
    NotaEmpenhoPage,
    ReverseIn,
    SaldoItemOut,
    SaldoItensOut,
    SaldoOut,
    Stage,
)
from app.services import notas_empenho as service
from app.services import saldo as saldo_service
from app.services.notas_empenho import LineInput, NeView

router = APIRouter(prefix="/api/v1/notas-empenho", tags=["notas-empenho"])
saldo_router = APIRouter(prefix="/api/v1/atas", tags=["atas"])

Gestor = Annotated[User, Depends(Requires("gestor"))]
Mover = Annotated[User, Depends(Requires("gestor", "servidor"))]
Reader = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


def _correlation(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


def _lines(items: list[LineIn]) -> list[LineInput]:
    return [LineInput(item_ata_id=i.item_ata_id, quantity=i.quantity) for i in items]


def _out(view: NeView) -> NotaEmpenhoOut:
    ne = view.ne
    return NotaEmpenhoOut(
        id=ne.id,
        number=ne.numero,
        numero_pre_empenho=ne.numero_pre_empenho,
        processo_sei=ne.processo_sei,
        status=ne.status,  # type: ignore[arg-type]
        ata_id=ne.ata_id,
        ata_number=view.ata.number,
        value=view.value,
        items=[
            LineOut(
                id=line.line.id,
                item_ata_id=line.item.id,
                insumo_id=line.insumo.id,
                sku=line.insumo.sku,
                description=line.insumo.description,
                unit=line.insumo.unit,
                quantity=line.line.quantity,
                unit_price=line.line.unit_price,
                value=line.line.value,
            )
            for line in view.lines
        ],
        issued_on=ne.issued_on,
        owner_id=ne.owner_id,
        created_at=ne.criado_em,
        updated_at=ne.atualizado_em,
    )


@router.post("", response_model=NotaEmpenhoOut, status_code=status.HTTP_201_CREATED)
def open_ne(
    body: NotaEmpenhoIn, actor: Gestor, request: Request, session: DbSession
) -> NotaEmpenhoOut:
    """Open an NE in demanda (SPEC-0004 AC-0004-01 to -03, -17, -20, -21)."""
    return _out(
        service.open_ne(
            session,
            actor=actor,
            ata_id=body.ata_id,
            processo=body.processo_sei,
            lines=_lines(body.items),
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.get("", response_model=NotaEmpenhoPage)
def list_nes(
    actor: Reader,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
    etapa: Stage | None = None,
    ata_id: uuid.UUID | None = None,
    processo_sei: Annotated[str | None, Query(max_length=30)] = None,
) -> NotaEmpenhoPage:
    """List NEs, newest first, filtered by etapa, ATA and Processo SEI."""
    views, total = service.list_nes(
        session, status=etapa, ata_id=ata_id, processo=processo_sei, page=page, size=size
    )
    return NotaEmpenhoPage(items=[_out(v) for v in views], total=total, page=page, size=size)


# Declared before `/{ne_id}`, which would otherwise swallow "indicadores".
@router.get("/indicadores", response_model=IndicatorsOut)
def indicators(actor: Reader, session: DbSession) -> IndicatorsOut:
    """Emitidas, em andamento and total (SPEC-0004 AC-0004-18, RF13)."""
    counts = service.indicators(session)
    return IndicatorsOut(
        emitidas=counts.emitidas, em_andamento=counts.em_andamento, total=counts.total
    )


@router.get("/{ne_id}", response_model=NotaEmpenhoOut)
def get_ne(ne_id: uuid.UUID, actor: Reader, session: DbSession) -> NotaEmpenhoOut:
    """One NE with its itens (SPEC-0004 §7)."""
    return _out(service.get(session, ne_id))


@router.put("/{ne_id}/itens", response_model=NotaEmpenhoOut)
def replace_items(
    ne_id: uuid.UUID, body: ItemsIn, actor: Gestor, request: Request, session: DbSession
) -> NotaEmpenhoOut:
    """Replace the itens before pré-empenho (SPEC-0004 AC-0004-19, -22)."""
    return _out(
        service.replace_items(
            session,
            actor=actor,
            ne_id=ne_id,
            lines=_lines(body.items),
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.post("/{ne_id}/avancar", response_model=NotaEmpenhoOut)
def advance(
    ne_id: uuid.UUID, body: AdvanceIn, actor: Mover, request: Request, session: DbSession
) -> NotaEmpenhoOut:
    """Advance one stage (SPEC-0004 AC-0004-04, -05, -12 to -15, -24, -28, -29)."""
    return _out(
        service.advance(
            session,
            actor=actor,
            ne_id=ne_id,
            to=body.to,
            numero_pre_empenho=body.numero_pre_empenho,
            numero=body.number,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.post("/{ne_id}/reverter", response_model=NotaEmpenhoOut)
def reverse(
    ne_id: uuid.UUID, body: ReverseIn, actor: Gestor, request: Request, session: DbSession
) -> NotaEmpenhoOut:
    """Reverse one stage with a justification (SPEC-0004 AC-0004-06, -07, -10, RN03)."""
    return _out(
        service.reverse(
            session,
            actor=actor,
            ne_id=ne_id,
            to=body.to,
            justification=body.justification,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.post("/{ne_id}/cancelar", response_model=NotaEmpenhoOut)
def cancel(
    ne_id: uuid.UUID, body: CancelNeIn, actor: Gestor, request: Request, session: DbSession
) -> NotaEmpenhoOut:
    """Cancel with a justification, releasing the reservation (SPEC-0004 AC-0004-16)."""
    return _out(
        service.cancel(
            session,
            actor=actor,
            ne_id=ne_id,
            justification=body.justification,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@saldo_router.get("/{ata_id}/saldo", response_model=SaldoOut)
def saldo(ata_id: uuid.UUID, actor: Reader, session: DbSession) -> SaldoOut:
    """The ATA's saldo in value, summed now (SPEC-0006 AC-0006-01 to -09, -16)."""
    s = saldo_service.saldo_da_ata(session, ata_id, at=clock.now())
    return SaldoOut(
        valor_contratado=s.valor_contratado,
        valor_reservado=s.valor_reservado,
        valor_empenhado=s.valor_empenhado,
        saldo_disponivel=s.saldo_disponivel,
        comprometimento_percentual=s.comprometimento_percentual,
        alto_consumo=s.alto_consumo,
        calculado_em=s.calculado_em,
    )


@saldo_router.get("/{ata_id}/itens/saldo", response_model=SaldoItensOut)
def saldo_dos_itens(ata_id: uuid.UUID, actor: Reader, session: DbSession) -> SaldoItensOut:
    """Each item's saldo in quantity (SPEC-0006 AC-0006-10 to -13)."""
    items, at = saldo_service.saldo_dos_itens(session, ata_id, at=clock.now())
    return SaldoItensOut(
        items=[
            SaldoItemOut(
                item_ata_id=s.item.id,
                insumo_id=s.insumo.id,
                sku=s.insumo.sku,
                description=s.insumo.description,
                unit=s.insumo.unit,
                quantidade_contratada=s.quantidade_contratada,
                quantidade_reservada=s.quantidade_reservada,
                quantidade_empenhada=s.quantidade_empenhada,
                quantidade_disponivel=s.quantidade_disponivel,
                esgotado=s.esgotado,
            )
            for s in items
        ],
        calculado_em=at,
    )
