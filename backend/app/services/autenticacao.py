"""Local credential authentication (AC-0001-01 to -05, -08, -24).

The shape of this module is dictated by AC-0001-02: a wrong password, an
unknown address and an address outside the institutional domains must be
**indistinguishable**. That is why there is one exception class for all three,
why the lookup and the verification are not short-circuited, and why the failure
record is written outside the request's transaction.
"""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.segredos import digest_secret
from app.core.senhas import check_senha, hash_senha
from app.models.usuario import Usuario
from app.repositories import usuario as repo
from app.services.auditoria import Evento, record_standalone
from app.services.erros import CredenciaisInvalidas, RotaIndisponivel, UsuarioInativo

# Verified against when no account matches, so that "unknown address" costs the
# same ~300 ms as "wrong password". Without it the response time is an oracle
# that answers the question AC-0001-02 forbids answering.
_HASH_SENTINELA = hash_senha(secrets.token_urlsafe(32))


def autenticar_local(
    sessao: Session, *, email: str, senha: str, correlation_id: uuid.UUID
) -> Usuario:
    """Verify an e-mail and senha, or raise.

    Wrong senha, unknown e-mail and an address off the allowlist all raise the
    same error with the same shape: AC-0001-02 wants the three responses
    indistinguishable, so that six attempts cannot tell an attacker which
    addresses exist.
    """
    cfg = get_settings()
    if not cfg.local_login_enabled:
        # 404, not 403: a mechanism switched off should be indistinguishable
        # from one that was never built (AC-0001-24).
        raise RotaIndisponivel()

    usuario = (
        repo.by_email(sessao, email)
        if _dominio_institucional(email, cfg.dominios_institucionais)
        else None
    )
    armazenado = usuario.senha_hash if usuario and usuario.senha_hash else _HASH_SENTINELA
    senha_confere = check_senha(senha, armazenado)

    if usuario is None or not senha_confere:
        _auditar_falha(
            email,
            motivo="credenciais_invalidas",
            usuario_id=usuario.id if usuario else None,
            correlation_id=correlation_id,
        )
        raise CredenciaisInvalidas()

    if not usuario.ativo:
        # The password was right, so this is a legitimate person whose account
        # was blocked or never activated — telling them so is a kindness, and it
        # reveals nothing to anyone who does not already hold the credential.
        _auditar_falha(
            email,
            motivo=f"status_{usuario.status}",
            usuario_id=usuario.id,
            correlation_id=correlation_id,
        )
        raise UsuarioInativo()

    return usuario


def _dominio_institucional(email: str, permitidos: list[str]) -> bool:
    _, _, dominio = email.strip().lower().rpartition("@")
    return bool(dominio) and any(
        dominio == d.lower() or dominio.endswith(f".{d.lower()}") for d in permitidos
    )


def _auditar_falha(
    email: str, *, motivo: str, usuario_id: uuid.UUID | None, correlation_id: uuid.UUID
) -> None:
    """Record the failure in its own committed transaction.

    The request is about to raise, and the request's session will roll back —
    an audit row written in it would vanish along with the failure it records,
    leaving a trail containing only successes.

    Never the address itself: `lgpd.md` promises this table carries no personal
    data, and it can never be corrected (SPEC-0001 §8).
    """
    _, _, dominio = email.strip().lower().rpartition("@")
    record_standalone(
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario_id or uuid.UUID(int=0),
            acao="auth.falha",
            usuario_id=usuario_id,
            dados_anteriores={
                "motivo": motivo,
                "email_hmac": digest_secret(email).hex(),
                "dominio": dominio,
            },
        ),
        correlation_id=correlation_id,
    )
