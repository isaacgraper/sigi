"""NF routes (SPEC-0005 §7).

Reads are open to the three perfis. Registering, correcting, sending and
quarantining are the gestor's and the servidor's; approving, returning and
releasing are the gestor's (AC-0005-09, -13), enforced here on the route.
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
from app.schemas.nota_fiscal import (
    NfCorrectionIn,
    NfLineOut,
    NfStatus,
    NotaFiscalIn,
    NotaFiscalOut,
    NotaFiscalPage,
    QuarantineIn,
    ReturnIn,
)
from app.services import notas_fiscais as service
from app.services.notas_fiscais import LineInput, NfInput, NfView

router = APIRouter(prefix="/api/v1/notas-fiscais", tags=["notas-fiscais"])

Gestor = Annotated[User, Depends(Requires("gestor"))]
Mover = Annotated[User, Depends(Requires("gestor", "servidor"))]
Reader = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


def _correlation(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


def _input(body: NfCorrectionIn) -> NfInput:
    return NfInput(
        numero=body.numero,
        data_emissao=body.data_emissao,
        valor=body.valor,
        fornecedor_cnpj=body.fornecedor_cnpj,
        lines=[
            LineInput(item_nota_empenho_id=i.item_nota_empenho_id, quantity=i.quantidade)
            for i in body.itens
        ],
    )


def _out(view: NfView) -> NotaFiscalOut:
    nf = view.nf
    return NotaFiscalOut(
        id=nf.id,
        numero=nf.numero,
        data_emissao=nf.issued_on,
        valor=nf.value,
        nota_empenho_id=nf.nota_empenho_id,
        nota_empenho_number=view.ne.numero,
        ata_id=view.ne.ata_id,
        fornecedor_id=nf.fornecedor_id,
        owner_id=nf.owner_id,
        status=nf.status,  # type: ignore[arg-type]
        justificativa_devolucao=nf.return_reason,
        quarentena=nf.quarentena,
        motivo_quarentena=nf.motivo_quarentena,
        itens=[
            NfLineOut(
                id=line.line.id,
                item_nota_empenho_id=line.ne_line.id,
                item_ata_id=line.item.id,
                insumo_id=line.insumo.id,
                sku=line.insumo.sku,
                description=line.insumo.description,
                unit=line.insumo.unit,
                quantidade=line.line.quantity,
            )
            for line in view.lines
        ],
        created_at=nf.criado_em,
        updated_at=nf.atualizado_em,
    )


@router.post("", response_model=NotaFiscalOut, status_code=status.HTTP_201_CREATED)
def register(
    body: NotaFiscalIn, actor: Mover, request: Request, session: DbSession
) -> NotaFiscalOut:
    """Register an NF against an issued NE (SPEC-0005 AC-0005-01 to -07, -12, -15)."""
    return _out(
        service.register(
            session,
            actor=actor,
            nota_empenho_id=body.nota_empenho_id,
            data=_input(body),
            confirmar_data_anterior=body.confirmar_data_anterior,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.get("", response_model=NotaFiscalPage)
def list_nfs(
    actor: Reader,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
    status: NfStatus | None = None,
    nota_empenho_id: uuid.UUID | None = None,
    quarentena: bool | None = None,
) -> NotaFiscalPage:
    """List NFs, newest first, filtered by status, NE and quarantine (AC-0005-16)."""
    views, total = service.list_nfs(
        session,
        status=status,
        nota_empenho_id=nota_empenho_id,
        quarentena=quarentena,
        page=page,
        size=size,
    )
    return NotaFiscalPage(items=[_out(v) for v in views], total=total, page=page, size=size)


@router.get("/{nf_id}", response_model=NotaFiscalOut)
def get_nf(nf_id: uuid.UUID, actor: Reader, session: DbSession) -> NotaFiscalOut:
    """One NF with its lines (AC-0005-16)."""
    return _out(service.get(session, nf_id))


@router.put("/{nf_id}", response_model=NotaFiscalOut)
def correct(
    nf_id: uuid.UUID, body: NfCorrectionIn, actor: Mover, request: Request, session: DbSession
) -> NotaFiscalOut:
    """Correct the header and lines before conference (AC-0005-14)."""
    return _out(
        service.correct(
            session,
            actor=actor,
            nf_id=nf_id,
            data=_input(body),
            confirmar_data_anterior=body.confirmar_data_anterior,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.post("/{nf_id}/enviar", response_model=NotaFiscalOut)
def send(nf_id: uuid.UUID, actor: Mover, request: Request, session: DbSession) -> NotaFiscalOut:
    """Send to conference, re-running the caps from devolvida (AC-0005-08)."""
    return _out(
        service.send(
            session, actor=actor, nf_id=nf_id, at=clock.now(), correlation_id=_correlation(request)
        )
    )


@router.post("/{nf_id}/aprovar", response_model=NotaFiscalOut)
def approve(nf_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession) -> NotaFiscalOut:
    """Approve an NF in conference, not in quarantine (AC-0005-08, -09, -13)."""
    return _out(
        service.approve(
            session, actor=actor, nf_id=nf_id, at=clock.now(), correlation_id=_correlation(request)
        )
    )


@router.post("/{nf_id}/devolver", response_model=NotaFiscalOut)
def return_nf(
    nf_id: uuid.UUID, body: ReturnIn, actor: Gestor, request: Request, session: DbSession
) -> NotaFiscalOut:
    """Return an NF in conference with a justificativa (AC-0005-08, -09)."""
    return _out(
        service.return_nf(
            session,
            actor=actor,
            nf_id=nf_id,
            justification=body.justificativa,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.post("/{nf_id}/quarentena", response_model=NotaFiscalOut)
def quarantine(
    nf_id: uuid.UUID, body: QuarantineIn, actor: Mover, request: Request, session: DbSession
) -> NotaFiscalOut:
    """Hold an NF with a problem, with a motivo (AC-0005-13)."""
    return _out(
        service.quarantine(
            session,
            actor=actor,
            nf_id=nf_id,
            motivo=body.motivo,
            at=clock.now(),
            correlation_id=_correlation(request),
        )
    )


@router.post("/{nf_id}/liberar", response_model=NotaFiscalOut)
def release(nf_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession) -> NotaFiscalOut:
    """Release an NF from quarantine (AC-0005-13)."""
    return _out(
        service.release(
            session, actor=actor, nf_id=nf_id, at=clock.now(), correlation_id=_correlation(request)
        )
    )
