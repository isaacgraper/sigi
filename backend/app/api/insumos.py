"""Catalogue and grupo routes (SPEC-0003 §3.1 to §3.4, §3.9).

Every perfil reads, a servidor inside its grupos (RN07); a servidor and a gestor
register and correct insumos; everything else is the gestor's. Enforced here on
the route, which is the only place it counts (A01).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.uploads import csv_body
from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import DbSession
from app.models.user import User
from app.schemas.insumo import (
    CatalogueReportOut,
    GrupoIn,
    GrupoNodeOut,
    GrupoPatch,
    GrupoRef,
    InsumoAtaOut,
    InsumoDetailOut,
    InsumoIn,
    InsumoOut,
    InsumoPage,
    InsumoPatch,
    JustificationIn,
    SkuChangeIn,
    SubstituteIn,
    SubstituteOut,
)
from app.services import insumos
from app.services.insumos import GrupoNode, InsumoDetail, InsumoView

router = APIRouter(prefix="/api/v1/insumos", tags=["insumos"])
grupos_router = APIRouter(prefix="/api/v1/grupos-materiais", tags=["insumos"])

Gestor = Annotated[User, Depends(Requires("gestor"))]
Writer = Annotated[User, Depends(Requires("gestor", "servidor"))]
Reader = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


def _correlation(request: Request) -> uuid.UUID:
    raw = request.scope.get("state", {}).get("correlation_id")
    return raw if isinstance(raw, uuid.UUID) else current_correlation_id()


def _insumo_out(view: InsumoView) -> InsumoOut:
    insumo = view.insumo
    return InsumoOut(
        id=insumo.id,
        sku=insumo.sku,
        codigo_doms=insumo.codigo_doms,
        external_code=insumo.external_code,
        description=insumo.description,
        unit=insumo.unit,
        grupo_id=insumo.grupo_id,
        grupo_path=[GrupoRef(id=g.id, name=g.name, level=g.level) for g in view.grupo_path],
        reference_quantity=insumo.reference_quantity,
        status=view.status,
        discontinued_on=insumo.discontinued_on,
        substitute=SubstituteOut(
            id=view.substitute.id, sku=view.substitute.sku, description=view.substitute.description
        )
        if view.substitute
        else None,
        created_at=insumo.criado_em,
    )


def _detail_out(detail: InsumoDetail) -> InsumoDetailOut:
    return InsumoDetailOut(
        **_insumo_out(detail).model_dump(),
        atas=[
            InsumoAtaOut(
                ata_id=ata.id,
                ata_number=ata.number,
                ata_status=ata.status,
                item_id=item.id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item, ata in detail.atas
        ],
    )


def _node_out(node: GrupoNode) -> GrupoNodeOut:
    return GrupoNodeOut(
        id=node.grupo.id,
        name=node.grupo.name,
        level=node.grupo.level,
        parent_id=node.grupo.parent_id,
        children=[_node_out(child) for child in node.children],
    )


@router.get("", response_model=InsumoPage)
def list_insumos(
    actor: Reader,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 25,
    q: Annotated[str | None, Query(max_length=100)] = None,
    grupo_id: uuid.UUID | None = None,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(ativo|descontinuado|substituido)$")
    ] = None,
) -> InsumoPage:
    """Search the catalogue (SPEC-0003 AC-0003-12, -29)."""
    views, total = insumos.list_insumos(
        session,
        actor=actor,
        page=page,
        size=size,
        query=q,
        grupo_id=grupo_id,
        status=status_filter,
    )
    return InsumoPage(items=[_insumo_out(v) for v in views], total=total, page=page, size=size)


@router.post("", response_model=InsumoDetailOut, status_code=status.HTTP_201_CREATED)
def register(
    body: InsumoIn, actor: Writer, request: Request, session: DbSession
) -> InsumoDetailOut:
    """Register an insumo (SPEC-0003 AC-0003-01 to -03)."""
    insumo = insumos.register(
        session,
        actor=actor,
        sku=body.sku,
        description=body.description,
        unit=body.unit,
        grupo_id=body.grupo_id,
        codigo_doms=body.codigo_doms,
        external_code=body.external_code,
        reference_quantity=body.reference_quantity,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _detail_out(insumos.get(session, insumo.id, actor=actor))


# Declared before `/{insumo_id}`, which would otherwise swallow "importacao".
@router.post("/importacao", response_model=CatalogueReportOut)
def import_catalogue(
    actor: Gestor,
    request: Request,
    session: DbSession,
    content: Annotated[bytes, Depends(csv_body)],
    dry_run: bool = False,
) -> CatalogueReportOut:
    """Create or update insumos from a CSV file (SPEC-0003 AC-0003-06 to -08, -18, -19)."""
    report = insumos.import_catalogue(
        session,
        actor=actor,
        content=content,
        dry_run=dry_run,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return CatalogueReportOut(
        created=report.created,
        updated=report.updated,
        unchanged=report.unchanged,
        corrected_descriptions=report.corrected_descriptions,
        ignored_columns=list(report.ignored_columns),
        notes=list(report.notes),
        dry_run=report.dry_run,
    )


@router.get("/{insumo_id}", response_model=InsumoDetailOut)
def get_insumo(insumo_id: uuid.UUID, actor: Reader, session: DbSession) -> InsumoDetailOut:
    """One insumo with the ATAs it is an item of (SPEC-0003 AC-0003-12, -29)."""
    return _detail_out(insumos.get(session, insumo_id, actor=actor))


@router.patch("/{insumo_id}", response_model=InsumoDetailOut)
def edit_insumo(
    insumo_id: uuid.UUID, body: InsumoPatch, actor: Writer, request: Request, session: DbSession
) -> InsumoDetailOut:
    """Correct an insumo, never its SKU (SPEC-0003 AC-0003-11)."""
    sent = body.model_dump(exclude_unset=True)
    # An explicit null clears an optional code or the reference quantity, and is
    # a mistake on a required field.
    changes = {
        key: value
        for key, value in sent.items()
        if value is not None or key in ("codigo_doms", "external_code", "reference_quantity")
    }
    insumos.edit(
        session,
        actor=actor,
        insumo_id=insumo_id,
        changes=changes,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _detail_out(insumos.get(session, insumo_id, actor=actor))


@router.post("/{insumo_id}/alterar-sku", response_model=InsumoDetailOut)
def change_sku(
    insumo_id: uuid.UUID, body: SkuChangeIn, actor: Gestor, request: Request, session: DbSession
) -> InsumoDetailOut:
    """Change a SKU, with a justification (SPEC-0003 AC-0003-04)."""
    insumos.change_sku(
        session,
        actor=actor,
        insumo_id=insumo_id,
        sku=body.sku,
        justification=body.justification,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _detail_out(insumos.get(session, insumo_id, actor=actor))


@router.post("/{insumo_id}/descontinuar", response_model=InsumoDetailOut)
def discontinue(
    insumo_id: uuid.UUID,
    body: JustificationIn,
    actor: Gestor,
    request: Request,
    session: DbSession,
) -> InsumoDetailOut:
    """Discontinue an insumo (SPEC-0003 AC-0003-14)."""
    insumos.discontinue(
        session,
        actor=actor,
        insumo_id=insumo_id,
        justification=body.justification,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _detail_out(insumos.get(session, insumo_id, actor=actor))


@router.post("/{insumo_id}/substituir", response_model=InsumoDetailOut)
def substitute(
    insumo_id: uuid.UUID, body: SubstituteIn, actor: Gestor, request: Request, session: DbSession
) -> InsumoDetailOut:
    """Record that an insumo is substituted by another (SPEC-0003 AC-0003-15)."""
    insumos.substitute(
        session,
        actor=actor,
        insumo_id=insumo_id,
        substitute_id=body.substitute_id,
        justification=body.justification,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _detail_out(insumos.get(session, insumo_id, actor=actor))


@router.post("/{insumo_id}/reativar", response_model=InsumoDetailOut)
def reactivate(
    insumo_id: uuid.UUID,
    body: JustificationIn,
    actor: Gestor,
    request: Request,
    session: DbSession,
) -> InsumoDetailOut:
    """Reactivate an insumo discontinued by mistake (SPEC-0003 AC-0003-16)."""
    insumos.reactivate(
        session,
        actor=actor,
        insumo_id=insumo_id,
        justification=body.justification,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return _detail_out(insumos.get(session, insumo_id, actor=actor))


# ── Grupos (AC-0003-09, -13) ────────────────────────────────────────────────


@grupos_router.get("", response_model=list[GrupoNodeOut])
def grupo_tree(actor: Reader, session: DbSession) -> list[GrupoNodeOut]:
    """The grupo tree; a servidor sees its own grupos (SPEC-0003 AC-0003-09, -29)."""
    scope = insumos.scope_of(session, actor)
    return [_node_out(node) for node in insumos.grupo_tree(session, scope)]


@grupos_router.post("", response_model=GrupoNodeOut, status_code=status.HTTP_201_CREATED)
def create_grupo(
    body: GrupoIn, actor: Gestor, request: Request, session: DbSession
) -> GrupoNodeOut:
    """Create a grupo (SPEC-0003 AC-0003-09)."""
    grupo = insumos.create_grupo(
        session,
        actor=actor,
        name=body.name,
        parent_id=body.parent_id,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return GrupoNodeOut(
        id=grupo.id, name=grupo.name, level=grupo.level, parent_id=grupo.parent_id, children=[]
    )


@grupos_router.patch("/{grupo_id}", response_model=GrupoNodeOut)
def rename_grupo(
    grupo_id: uuid.UUID, body: GrupoPatch, actor: Gestor, request: Request, session: DbSession
) -> GrupoNodeOut:
    """Rename a grupo (SPEC-0003 AC-0003-13)."""
    grupo = insumos.rename_grupo(
        session,
        actor=actor,
        grupo_id=grupo_id,
        name=body.name,
        at=clock.now(),
        correlation_id=_correlation(request),
    )
    return GrupoNodeOut(
        id=grupo.id, name=grupo.name, level=grupo.level, parent_id=grupo.parent_id, children=[]
    )
