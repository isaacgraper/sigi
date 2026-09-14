"""The grant that lets someone set a credential (SPEC-0001).

An invitation and a password reset are the same object: a hashed, single-use,
expiring permission to write a password. What differs is where it came from, how
long it lives, and what the message says. So the mechanics live here once, and
`membros.py` (invitations, AC-0001-10/11/25/26) and the reset flow (AC-0001-30
to -32) both call it.

Only the HMAC is stored. That is what makes "the link cannot be recovered after
the response that carried it" a property of the schema rather than a promise
about the code — AC-0001-10 in v0.6 depends on it being the former.
"""

from __future__ import annotations

import datetime
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.segredos import digerir
from app.models.token_credencial import TokenCredencial
from app.repositories import token_credencial as repo
from app.services.erros import ConviteExpirado, ConviteJaUtilizado, SenhaFraca

CONVITE = "convite"
REDEFINICAO = "redefinicao"

# 256 bits from a CSPRNG. The grant is looked up by equality on an indexed
# column, so its security rests entirely on being unguessable.
BYTES_TOKEN = 32


@dataclass(frozen=True)
class GrantEmitido:
    """A freshly issued grant, and the only moment its value exists."""

    token: TokenCredencial
    valor: str
    """The raw token. Never stored, never logged, never returned twice."""

    def link(self, caminho: str) -> str:
        """Build the URL the person opens to use this grant."""
        base = get_settings().url_base_frontend.rstrip("/")
        return f"{base}{caminho}/{self.valor}"


def emitir(
    sessao: Session,
    *,
    usuario_id: uuid.UUID,
    tipo: str,
    agora: datetime.datetime,
    criado_por: uuid.UUID | None,
) -> GrantEmitido:
    """Issue a grant, cancelling any earlier one of the same type.

    Cancelling first is not tidiness: `ux_token_credencial_aberto` permits one
    open grant per usuario per type, so a second invitation would hit a unique
    violation instead of superseding the first.
    """
    cfg = get_settings()
    horas = cfg.convite_ttl_horas if tipo == CONVITE else cfg.redefinicao_ttl_horas
    repo.cancelar_abertos(sessao, usuario_id=usuario_id, tipo=tipo, momento=agora)

    valor = secrets.token_urlsafe(BYTES_TOKEN)
    linha = repo.criar(
        sessao,
        usuario_id=usuario_id,
        tipo=tipo,
        token_hash=digerir(valor),
        expira_em=agora + datetime.timedelta(hours=horas),
        criado_por=criado_por,
    )
    return GrantEmitido(token=linha, valor=valor)


def resgatar(
    sessao: Session, *, valor: str, tipo: str, agora: datetime.datetime
) -> TokenCredencial:
    """Validate a grant and return it, or raise. Does **not** spend it.

    Spending is separate because AC-0001-26 requires a rejected password to
    leave the grant usable: a typo must not burn an invitation and force the
    gestor to issue another. So the caller validates the password first and
    calls `consumir` only once it is going to succeed.
    """
    linha = repo.por_hash(sessao, digerir(valor))
    if linha is None or linha.tipo != tipo:
        # Same answer for "no such token" and "a token of the other kind":
        # distinguishing them would say which grants exist.
        raise ConviteJaUtilizado()
    if linha.utilizado_em is not None:
        raise ConviteJaUtilizado()
    if linha.cancelado_em is not None or linha.expira_em <= agora:
        # A superseded grant reads as expired, which is what it is from the
        # holder's point of view: the gestor issued a newer one.
        raise ConviteExpirado()
    return linha


def consumir(sessao: Session, token: TokenCredencial, *, agora: datetime.datetime) -> None:
    """Spend the grant. Single use is enforced here and by the unique index."""
    repo.marcar_utilizado(sessao, token, momento=agora)


def exigir_senha_forte(senha: str) -> None:
    """Enforce the password policy (AC-0001-26).

    Length only, deliberately. Composition rules (a digit, a symbol, mixed case)
    push people towards `Senha@2026` and are weaker in practice than length;
    NIST dropped them for that reason. If the entity's own policy demands them,
    that is a spec change, not something to add here quietly.
    """
    minimo = get_settings().senha_tamanho_minimo
    if len(senha) < minimo:
        raise SenhaFraca(minimo)
