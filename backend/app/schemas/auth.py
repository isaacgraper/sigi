"""Request and response bodies for the auth routes.

Domain field names stay Portuguese; the envelope's plumbing is English
(ADR-0006, `api-conventions.md`).
"""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class SessaoSaida(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    # The refresh token is deliberately absent: it travels only in the httpOnly
    # cookie, so a body that leaked into a log or a screenshot cannot renew a
    # session (AC-0001-01).
    expira_em: datetime.datetime


class UsuarioSaida(BaseModel):
    id: uuid.UUID
    nome: str | None
    email: str | None
    perfil: str
    status: str
