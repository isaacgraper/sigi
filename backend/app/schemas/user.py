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
    created_at: datetime.datetime
    activation_link: str


class MemberOutput(BaseModel):
    """One member, as the member list shows them.

    A deactivated usuario reads with `nome` and `email` null and `pseudonimo`
    set: the record of what they did survives their identifying fields
    (AC-0001-14).
    """

    id: uuid.UUID
    name: str | None
    email: str | None
    perfil: str
    status: str
    created_at: datetime.datetime
    pseudonym: str | None


class MemberPage(BaseModel):
    """A page of members, in the envelope `api-conventions.md` fixes."""

    items: list[MemberOutput]
    total: int
    page: int
    size: int


class ResetTriggerOutput(BaseModel):
    """The reset link, returned to the gestor who asked for it.

    Returned exactly once. Only the HMAC reaches the database, so no endpoint
    can recover it afterwards (AC-0001-32, as amended in v1.0).
    """

    id: uuid.UUID
    reset_link: str


class ResetConfirmInput(BaseModel):
    """The body of a reset confirmation.

    The token is a field rather than a path segment (OQ-30), for the same reason
    as activation: a single-use credential in a path lands in access logs,
    proxies and browser history.
    """

    token: str = Field(min_length=1)
    password: str = Field(min_length=1)
