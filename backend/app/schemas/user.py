"""Request and response bodies for member management."""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints

# Trimmed and non-blank, bounded like every other field (AC-0001-41). No format
# for the registration: none is known (OQ-41).
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Registration = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Justification = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class InviteInput(BaseModel):
    """The body of an invitation (AC-0001-10, -45).

    `name` and `registration` are mandatory on a new invitation. The columns stay
    nullable, because accounts created before v1.7 have neither.
    """

    email: EmailStr
    perfil: str = Field(pattern="^(gestor|servidor|auditor)$")
    name: Name
    registration: Registration


class UnblockInput(BaseModel):
    """The body of an unblock: the justification is the one thing required (AC-0001-44)."""

    justification: Justification


class InviteOutput(BaseModel):
    """The created account and its activation link.

    The link is returned exactly once, in this response. Only its HMAC reaches
    the database, so no endpoint can recover it afterwards, and the gestor is
    the one who delivers it (AC-0001-10).
    """

    id: uuid.UUID
    name: str | None
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
    # Read by a gestor or an auditor only, and the routes that return it are
    # theirs alone (SPEC-0001 §6). Null after anonymisation (AC-0001-14).
    registration: str | None
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

    token: str = Field(min_length=1, max_length=512)
    password: str = Field(min_length=1, max_length=128)
