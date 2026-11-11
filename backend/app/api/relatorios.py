"""Report routes (SPEC-0009 §2.3).

Read-only. The four reports and the Histórico are the gestor's and the
auditor's; a list export is for whoever reads the list, which the service
decides (AC-0009-11). A report is a download, and serving one writes the
audit row that says who took it (AC-0009-04).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import AwareDatetime

from app.constants.relatorios import FORMAT_CSV, MEDIA_TYPES
from app.core import clock
from app.core.authorization import Requires
from app.core.correlation import current as current_correlation_id
from app.core.db import DbSession
from app.models.user import User
from app.services import list_exports as service
from app.services import relatorio_files

router = APIRouter(prefix="/api/v1/relatorios", tags=["relatorios"])

Reader = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


@router.get("/{relatorio}", response_class=Response)
def export(
    relatorio: str,
    actor: Reader,
    request: Request,
    session: DbSession,
    formato: str = FORMAT_CSV,
    referencia: AwareDatetime | None = None,
    ata_id: uuid.UUID | None = None,
    colunas: str | None = None,
    inicio: AwareDatetime | None = None,
    status: str | None = None,
    situacao_vigencia: str | None = None,
    q: str | None = None,
    grupo_id: str | None = None,
    etapa: str | None = None,
    processo_sei: str | None = None,
    nota_empenho_id: str | None = None,
    quarentena: str | None = None,
    entidade_tipo: str | None = None,
    entidade_id: str | None = None,
    usuario_id: str | None = None,
    de: str | None = None,
    ate: str | None = None,
) -> Response:
    """One report or one list as a file, at its data de referência (AC-0009-01 to -12)."""
    raw = request.scope.get("state", {}).get("correlation_id")
    result = service.export(
        session,
        actor=actor,
        relatorio=relatorio,
        formato=formato,
        referencia=referencia,
        ata_id=ata_id,
        at=clock.now(),
        correlation_id=raw if isinstance(raw, uuid.UUID) else current_correlation_id(),
        colunas=(
            tuple(key.strip() for key in colunas.split(",") if key.strip())
            if colunas is not None
            else None
        ),
        inicio=inicio,
        filtros={
            "status": status,
            "situacao_vigencia": situacao_vigencia,
            "q": q,
            "grupo_id": grupo_id,
            "etapa": etapa,
            "processo_sei": processo_sei,
            "nota_empenho_id": nota_empenho_id,
            "quarentena": quarentena,
            "entidade_tipo": entidade_tipo,
            "entidade_id": entidade_id,
            "usuario_id": usuario_id,
            "de": de,
            "ate": ate,
        },
    )
    return Response(
        content=relatorio_files.render(result),
        media_type=MEDIA_TYPES[result.formato],
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
