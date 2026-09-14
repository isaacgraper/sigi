"""Request and response bodies for member management."""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth import UsuarioSaida


class ConviteEntrada(BaseModel):
    email: EmailStr
    perfil: Literal["gestor", "servidor", "auditor"]


class ConviteSaida(BaseModel):
    """The invitation, and the only time its link is ever visible.

    `link` is here because AC-0001-10 (v0.6) makes the gestor the delivery
    channel: they copy it and pass it on. It is not stored — the database keeps
    only the token's HMAC — so no endpoint can return it a second time.
    """

    usuario: UsuarioSaida
    link: str
    expira_em: datetime.datetime


class MembroSaida(BaseModel):
    id: uuid.UUID
    nome: str | None
    email: str | None
    perfil: str
    status: str
    criado_em: datetime.datetime
    anonimizado_em: datetime.datetime | None


class PaginaDeMembros(BaseModel):
    """The envelope from `api-conventions.md`: English plumbing, Portuguese domain."""

    items: list[MembroSaida]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
