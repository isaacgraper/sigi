"""Request and response bodies for redeeming an invitation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.auth import SessaoSaida


class AtivacaoEntrada(BaseModel):
    # No `min_length` here on purpose. The policy lives in
    # `credenciais.exigir_senha_forte`, which raises SENHA_FRACA with the length
    # rule in the message — AC-0001-26 asks for that code, not a generic 422,
    # and two places stating the minimum is how they come to disagree.
    senha: str = Field(min_length=1)


class AtivacaoSaida(BaseModel):
    """Activation and first login are one step (AC-0001-11)."""

    sessao: SessaoSaida
