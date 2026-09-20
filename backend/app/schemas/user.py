"""Request and response bodies for member management."""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class InviteInput(BaseModel):
    """The body of an invitation."""

    email: EmailStr
    perfil: str = Field(pattern="^(gestor|servidor|auditor)$")


class InviteOutput(BaseModel):
    """The created account and its activation link.

    The link is returned exactly once, in this response. Only its HMAC reaches
    the database, so no endpoint can recover it afterwards, and the gestor is
    the one who delivers it (AC-0001-10).
    """

    id: uuid.UUID
    email: str
    perfil: str
    status: str
    criado_em: datetime.datetime
    link_ativacao: str
