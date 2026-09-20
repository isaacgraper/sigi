"""Request and response bodies for the auth routes.

Nobody but a developer reads this surface, so it is English, except a
glossary noun such as `perfil` (ADR-0013, `api-conventions.md`).
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginInput(BaseModel):
    """The body of a local login."""

    email: EmailStr
    password: str = Field(min_length=1)


class SessionOutput(BaseModel):
    """The access token and its expiry. The refresh token travels as a cookie."""

    access_token: str
    token_type: str = "Bearer"
    # The refresh token is deliberately absent: it travels only in the httpOnly
    # cookie, so a body that leaked into a log or a screenshot cannot renew a
    # session (AC-0001-01).
    expires_at: datetime.datetime


class UserOutput(BaseModel):
    """The caller's identity, declared field by field so `senha_hash` cannot leak."""

    id: uuid.UUID
    name: str | None
    email: str | None
    perfil: str
    status: str
