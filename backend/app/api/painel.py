"""The dashboard's data, one section at a time (SPEC-0012 §7)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.authorization import Requires
from app.core.config import get_settings
from app.models.user import User
from app.schemas.painel import BlockOut, PainelOut
from app.services import painel

router = APIRouter(prefix="/api/v1/painel", tags=["painel"])

Reader = Annotated[User, Depends(Requires("gestor", "servidor", "auditor"))]


@router.get("/{section}", response_model=PainelOut)
def read_section(section: str, actor: Reader) -> PainelOut:
    """Every block of one section, empty while its source does not exist (AC-0012-12)."""
    demo = get_settings().dashboard_demo
    blocks = painel.read(section, demo=demo)
    return PainelOut(
        section=section,
        demo=demo,
        blocks={name: BlockOut(rows=rows) for name, rows in blocks.items()},
    )
