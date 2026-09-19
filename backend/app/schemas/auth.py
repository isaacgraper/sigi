"""Request and response bodies for the auth routes.

Domain field names stay Portuguese; the envelope's plumbing is English
(ADR-0006, `api-conventions.md`).
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginEntrada(BaseModel):
    """The body of a local login."""

    email: EmailStr
    senha: str = Field(min_length=1)


class SessaoSaida(BaseModel):
    """The access token and its expiry. The refresh token travels as a cookie."""

    access_token: str
    token_type: str = "Bearer"
    # The refresh token is deliberately absent: it travels only in the httpOnly
    # cookie, so a body that leaked into a log or a screenshot cannot renew a
    # session (AC-0001-01).
    expira_em: datetime.datetime


class UsuarioSaida(BaseModel):
    """The caller's identity, declared field by field so `senha_hash` cannot leak."""

    id: uuid.UUID
    nome: str | None
    email: str | None
    perfil: str
    status: str
