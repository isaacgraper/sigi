"""Report routes (SPEC-0009 §2.3).

Read-only, for the gestor and the auditor. A report is a download, and serving
one writes the audit row that says who took it (AC-0009-04).
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
from app.services import relatorio_files
from app.services import relatorios as service

router = APIRouter(prefix="/api/v1/relatorios", tags=["relatorios"])

Auditor = Annotated[User, Depends(Requires("gestor", "auditor"))]


@router.get("/{relatorio}", response_class=Response)
def export(
    relatorio: str,
    actor: Auditor,
    request: Request,
    session: DbSession,
    formato: str = FORMAT_CSV,
    referencia: AwareDatetime | None = None,
    ata_id: uuid.UUID | None = None,
    colunas: str | None = None,
    inicio: AwareDatetime | None = None,
) -> Response:
    """One report as a file, at its data de referência (AC-0009-01 to -06, -08, -09)."""
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
    )
    return Response(
        content=relatorio_files.render(result),
        media_type=MEDIA_TYPES[result.formato],
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
