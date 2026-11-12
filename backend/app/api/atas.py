"""ATA routes (SPEC-0002 §3, §7).

Reads are open to the three perfis and writes to the gestor, enforced here on the
route, which is the only place it counts (A01, RN04).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.uploads import csv_body
from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import DbSession
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
    FornecedorIn,
    FornecedorOut,
    ReajusteIn,
    ReajusteOut,
)
from app.schemas.item_ata import (
    ItemIn,
    ItemInsumoOut,
    ItemOut,
    ItemPatch,
    ItemsLineOut,
    ItemsOut,
    ItemsReportOut,
)
from app.services import atas, itens_ata
from app.services.atas import AlertItem, AtaDetail, AtaView, FornecedorInput
from app.services.insumos import status_of
from app.services.itens_ata import ItemsView

router = APIRouter(prefix="/api/v1/atas", tags=["atas"])

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
                item_id=a.item_ata_id,
                quantity=a.quantidade_acrescimo,
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
        Query(alias="status", pattern="^(vigente|suspensa|encerrada|cancelada)$"),
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
    """Correct an ATA that is not encerrada or cancelada (SPEC-0002 AC-0002-24)."""
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
    """Record an aditivo of value, of prazo or of quantity.

    SPEC-0002 AC-0002-13, -14; the aditivo of quantity is SPEC-0003 AC-0003-27, -28.
    """
    at = clock.now()
    if body.kind == "quantidade":
        itens_ata.add_quantity_aditivo(
            session,
            actor=actor,
            ata_id=ata_id,
            item_id=body.item_id,
            quantity=body.quantity,
            justification=body.justification,
            at=at,
            correlation_id=_correlation(request),
        )
        return _detail_out(atas.get(session, ata_id, at=at))
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


# ── Items (SPEC-0003 §3.5) ──────────────────────────────────────────────────


def _items_out(view: ItemsView) -> ItemsOut:
    return ItemsOut(
        items=[
            ItemOut(
                id=v.item.id,
                insumo=ItemInsumoOut(
                    id=v.insumo.id,
                    sku=v.insumo.sku,
                    description=v.insumo.description,
                    unit=v.insumo.unit,
                    status=status_of(v.insumo),
                ),
                item_number=v.item.item_number,
                quantity=v.item.quantity,
                contracted_quantity=v.contracted_quantity,
                unit_price=v.item.unit_price,
                total_value=v.total_value,
                fornecedor=FornecedorOut(
                    id=v.fornecedor.id, cnpj=v.fornecedor.cnpj, legal_name=v.fornecedor.legal_name
                ),
                own_fornecedor=v.item.fornecedor_id is not None,
            )
            for v in view.items
        ],
        items_value=view.items_value,
        total_value=view.total_value,
        items_value_differs=view.items_value != view.total_value,
    )


@router.get("/{ata_id}/itens", response_model=ItemsOut)
def list_items(ata_id: uuid.UUID, actor: Reader, session: DbSession) -> ItemsOut:
    """An ATA's items and their sum (SPEC-0003 AC-0003-22, -29)."""
    return _items_out(itens_ata.list_items(session, ata_id, actor=actor))


@router.post("/{ata_id}/itens", response_model=ItemsOut, status_code=status.HTTP_201_CREATED)
def add_item(
    ata_id: uuid.UUID, body: ItemIn, actor: Gestor, request: Request, session: DbSession
) -> ItemsOut:
    """Add an insumo to an ATA (SPEC-0003 AC-0003-17, -20, -23)."""
    itens_ata.add_item(
        session,
        actor=actor,
        ata_id=ata_id,
        insumo_id=body.insumo_id,
        quantity=body.quantity,
        unit_price=body.unit_price,
        item_number=body.item_number,
        fornecedor=_fornecedor(body.fornecedor),
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _items_out(itens_ata.list_items(session, ata_id, actor=actor))


@router.post("/{ata_id}/itens/importacao", response_model=ItemsReportOut)
def import_items(
    ata_id: uuid.UUID,
    actor: Gestor,
    request: Request,
    session: DbSession,
    content: Annotated[bytes, Depends(csv_body)],
    dry_run: bool = False,
) -> ItemsReportOut:
    """Add or correct an ATA's items from a CSV file (SPEC-0003 AC-0003-26)."""
    report = itens_ata.import_items(
        session,
        actor=actor,
        ata_id=ata_id,
        content=content,
        dry_run=dry_run,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return ItemsReportOut(
        lines=[
            ItemsLineOut(
                line=line.line,
                sku=line.sku,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                item_number=line.item_number,
                fornecedor=line.fornecedor,
                action=line.action,
            )
            for line in report.lines
        ],
        added=report.added,
        corrected=report.corrected,
        unchanged=report.unchanged,
        ignored_columns=list(report.ignored_columns),
        dry_run=report.dry_run,
    )


@router.patch("/{ata_id}/itens/{item_id}", response_model=ItemsOut)
def edit_item(
    ata_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ItemPatch,
    actor: Gestor,
    request: Request,
    session: DbSession,
) -> ItemsOut:
    """Correct an item (SPEC-0003 AC-0003-23, -24, -28)."""
    sent = body.model_dump(exclude_unset=True)
    # An explicit null clears `item_number` and the item's own fornecedor, and is
    # a mistake anywhere else.
    changes = {
        key: value
        for key, value in sent.items()
        if value is not None or key in ("item_number", "fornecedor")
    }
    if "fornecedor" in changes:
        changes["fornecedor"] = _fornecedor(body.fornecedor)
    itens_ata.edit_item(
        session,
        actor=actor,
        ata_id=ata_id,
        item_id=item_id,
        changes=changes,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _items_out(itens_ata.list_items(session, ata_id, actor=actor))


@router.post("/{ata_id}/itens/{item_id}/remover", response_model=ItemsOut)
def remove_item(
    ata_id: uuid.UUID, item_id: uuid.UUID, actor: Gestor, request: Request, session: DbSession
) -> ItemsOut:
    """Remove an item, keeping its history (SPEC-0003 AC-0003-24)."""
    itens_ata.remove_item(
        session,
        actor=actor,
        ata_id=ata_id,
        item_id=item_id,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _items_out(itens_ata.list_items(session, ata_id, actor=actor))


def _fornecedor(given: FornecedorIn | None) -> FornecedorInput | None:
    if given is None:
        return None
    return FornecedorInput(cnpj=given.cnpj, legal_name=given.legal_name)
