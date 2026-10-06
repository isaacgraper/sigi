"""ATA routes (SPEC-0002 §3, §7).

Reads are open to the three perfis and writes to the gestor, enforced here on the
route, which is the only place it counts (A01, RN04).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import get_session
from app.models.user import User
from app.schemas.ata import (
    AditivoIn,
    AditivoOut,
    AlertOut,
    AtaDetailOut,
    AtaIn,
    AtaOut,
    AtaPage,
    AtaPatch,
    CancelIn,
    FornecedorOut,
    ReajusteIn,
    ReajusteOut,
)
from app.services import atas
from app.services.atas import AlertItem, AtaDetail, AtaView, FornecedorInput

router = APIRouter(prefix="/api/v1/atas", tags=["atas"])

DbSession = Annotated[Session, Depends(get_session)]
Gestor = Annotated[User, Depends(Requires("gestor"))]
Reader = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


def _correlation(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


def _ata_out(view: AtaView) -> AtaOut:
    ata = view.ata
    return AtaOut(
        id=ata.id,
        number=ata.number,
        subject=ata.subject,
        organ=ata.organ,
        fornecedor=FornecedorOut(
            id=view.fornecedor.id, cnpj=view.fornecedor.cnpj, legal_name=view.fornecedor.legal_name
        ),
        issued_on=ata.issued_on,
        vigencia_inicio=ata.vigencia_inicio,
        vigencia_fim=ata.vigencia_fim,
        total_value=ata.total_value,
        valor_contratado=view.valor_contratado,
        budget_date=ata.budget_date,
        status=ata.status,
        situacao_vigencia=view.situacao_vigencia,
        data_reajuste=view.data_reajuste,
        owner_id=ata.owner_id,
        created_at=ata.criado_em,
    )


def _detail_out(detail: AtaDetail) -> AtaDetailOut:
    return AtaDetailOut(
        **_ata_out(detail).model_dump(),
        aditivos=[
            AditivoOut(
                id=a.id,
                kind=a.kind,
                valor_acrescimo=a.valor_acrescimo,
                nova_vigencia_fim=a.nova_vigencia_fim,
                justification=a.justification,
                created_at=a.criado_em,
            )
            for a in detail.aditivos
        ],
        reajustes=[
            ReajusteOut(
                id=r.id,
                processo_sei=r.processo_sei,
                requested_on=r.requested_on,
                created_at=r.criado_em,
            )
            for r in detail.reajustes
        ],
    )


def _alert_out(item: AlertItem) -> AlertOut:
    return AlertOut(ata=_ata_out(item.view), days_remaining=item.days_remaining)


@router.post("", response_model=AtaDetailOut, status_code=status.HTTP_201_CREATED)
def register(body: AtaIn, actor: Gestor, request: Request, session: DbSession) -> AtaDetailOut:
    """Register an ATA as a draft (SPEC-0002 AC-0002-01 to -05, -25)."""
    at = clock.now()
    ata = atas.register(
        session,
        actor=actor,
        number=body.number,
        subject=body.subject,
        organ=body.organ,
        fornecedor=FornecedorInput(
            cnpj=body.fornecedor.cnpj, legal_name=body.fornecedor.legal_name
        ),
        issued_on=body.issued_on,
        vigencia_inicio=body.vigencia_inicio,
        vigencia_fim=body.vigencia_fim,
        total_value=body.total_value,
        budget_date=body.budget_date,
        at=at,
        correlation_id=_correlation(request),
    )
    return _detail_out(atas.get(session, ata.id, at=at))


@router.get("", response_model=AtaPage)
def list_atas(
    actor: Reader,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(rascunho|vigente|suspensa|encerrada|cancelada)$"),
    ] = None,
    situacao_vigencia: Annotated[str | None, Query(pattern="^(vigente|a_vencer|vencida)$")] = None,
) -> AtaPage:
    """List ATAs, filtered by status and by situacao_vigencia (SPEC-0002 AC-0002-23)."""
    views, total = atas.list_atas(
        session,
        page=page,
        size=size,
        status=status_filter,
        situacao=situacao_vigencia,
        at=clock.now(),
    )
    return AtaPage(items=[_ata_out(v) for v in views], total=total, page=page, size=size)


# Declared before `/{ata_id}`, which would otherwise swallow "alertas".
@router.get("/alertas/renovacao", response_model=list[AlertOut])
def renewal_alert(actor: Reader, session: DbSession) -> list[AlertOut]:
    """ATAs about to end with no aditivo de prazo (SPEC-0002 AC-0002-09, RF19)."""
    return [_alert_out(item) for item in atas.renewal_alert(session, at=clock.now())]


@router.get("/alertas/reajuste", response_model=list[AlertOut])
def reajuste_alert(actor: Reader, session: DbSession) -> list[AlertOut]:
    """ATAs whose reajuste is near or past with no request (SPEC-0002 AC-0002-20)."""
    return [_alert_out(item) for item in atas.reajuste_alert(session, at=clock.now())]


@router.get("/{ata_id}", response_model=AtaDetailOut)
def get_ata(ata_id: uuid.UUID, actor: Reader, session: DbSession) -> AtaDetailOut:
    """One ATA, with its aditivos and reajuste requests (SPEC-0002 AC-0002-23)."""
    return _detail_out(atas.get(session, ata_id, at=clock.now()))


@router.patch("/{ata_id}", response_model=AtaDetailOut)
def edit_ata(
    ata_id: uuid.UUID, body: AtaPatch, actor: Gestor, request: Request, session: DbSession
) -> AtaDetailOut:
    """Edit an ATA; past `rascunho` only objeto, orgao and responsavel (AC-0002-24)."""
    at = clock.now()
    sent = body.model_dump(exclude_unset=True)
    # An explicit null is a way to clear `issued_on` and a mistake anywhere else.
    changes = {key: value for key, value in sent.items() if value is not None or key == "issued_on"}
    if body.fornecedor is not None:
        changes["fornecedor"] = FornecedorInput(
            cnpj=body.fornecedor.cnpj, legal_name=body.fornecedor.legal_name
        )
    atas.edit(
        session,
        actor=actor,
        ata_id=ata_id,
        changes=changes,
        at=at,
        correlation_id=_correlation(request),
    )
    return _detail_out(atas.get(session, ata_id, at=at))


def _move(
    ata_id: uuid.UUID,
    move_name: str,
    actor: User,
    request: Request,
    session: Session,
    justification: str | None = None,
) -> AtaDetailOut:
    at = clock.now()
    atas.move(
        session,
        actor=actor,
        ata_id=ata_id,
        move_name=move_name,
        justification=justification,
        at=at,
        correlation_id=_correlation(request),
    )
    return _detail_out(atas.get(session, ata_id, at=at))


@router.post("/{ata_id}/ativar", response_model=AtaDetailOut)
def activate(
    ata_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession
) -> AtaDetailOut:
    """Move an ATA from rascunho to vigente (SPEC-0002 AC-0002-22)."""
    return _move(ata_id, "ativar", actor, request, session)


@router.post("/{ata_id}/suspender", response_model=AtaDetailOut)
def suspend(ata_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession) -> AtaDetailOut:
    """Move an ATA from vigente to suspensa (SPEC-0002 AC-0002-22)."""
    return _move(ata_id, "suspender", actor, request, session)


@router.post("/{ata_id}/retomar", response_model=AtaDetailOut)
def resume(ata_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession) -> AtaDetailOut:
    """Move an ATA from suspensa back to vigente (SPEC-0002 AC-0002-22)."""
    return _move(ata_id, "retomar", actor, request, session)


@router.post("/{ata_id}/encerrar", response_model=AtaDetailOut)
def close(ata_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession) -> AtaDetailOut:
    """Close an ATA (SPEC-0002 AC-0002-10, -22)."""
    return _move(ata_id, "encerrar", actor, request, session)


@router.post("/{ata_id}/cancelar", response_model=AtaDetailOut)
def cancel(
    ata_id: uuid.UUID, body: CancelIn, actor: Gestor, request: Request, session: DbSession
) -> AtaDetailOut:
    """Cancel an ATA, with a justification (SPEC-0002 AC-0002-22)."""
    return _move(ata_id, "cancelar", actor, request, session, body.justification)


@router.post("/{ata_id}/aditivos", response_model=AtaDetailOut, status_code=status.HTTP_201_CREATED)
def add_aditivo(
    ata_id: uuid.UUID, body: AditivoIn, actor: Gestor, request: Request, session: DbSession
) -> AtaDetailOut:
    """Record an aditivo of value or of prazo (SPEC-0002 AC-0002-13, -14)."""
    at = clock.now()
    atas.add_aditivo(
        session,
        actor=actor,
        ata_id=ata_id,
        kind=body.kind,
        valor_acrescimo=body.valor_acrescimo,
        nova_vigencia_fim=body.nova_vigencia_fim,
        justification=body.justification,
        at=at,
        correlation_id=_correlation(request),
    )
    return _detail_out(atas.get(session, ata_id, at=at))


@router.post(
    "/{ata_id}/reajustes", response_model=AtaDetailOut, status_code=status.HTTP_201_CREATED
)
def add_reajuste(
    ata_id: uuid.UUID, body: ReajusteIn, actor: Gestor, request: Request, session: DbSession
) -> AtaDetailOut:
    """Record a reajuste request filed in SEI (SPEC-0002 AC-0002-08, -19, -21)."""
    at = clock.now()
    atas.add_reajuste(
        session,
        actor=actor,
        ata_id=ata_id,
        processo=body.processo_sei,
        requested_on=body.requested_on,
        at=at,
        correlation_id=_correlation(request),
    )
    return _detail_out(atas.get(session, ata_id, at=at))
