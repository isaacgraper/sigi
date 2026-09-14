"""Local credential authentication (AC-0001-01 to -05, -08, -24).

The shape of this module is dictated by AC-0001-02: a wrong password, an
unknown address and an address outside the institutional domains must be
**indistinguishable**. That is why there is one exception class for all three,
why the lookup and the verification are not short-circuited, and why the failure
record is written outside the request's transaction.
"""

from __future__ import annotations

import datetime
import secrets
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.segredos import digest_secret
from app.core.senhas import check_senha, hash_senha
from app.models.usuario import Usuario
from app.repositories import usuario as repo
from app.services import bloqueio
from app.services.auditoria import Evento, record_standalone, registrar, standalone_transaction
from app.services.erros import CredenciaisInvalidas, RotaIndisponivel, UsuarioInativo

# Verified against when no account matches, so that "unknown address" costs the
# same ~300 ms as "wrong password". Without it the response time is an oracle
# that answers the question AC-0001-02 forbids answering.
_HASH_SENTINELA = hash_senha(secrets.token_urlsafe(32))


def autenticar_local(
    sessao: Session, *, email: str, senha: str, correlation_id: uuid.UUID
) -> Usuario:
    cfg = get_settings()
    if not cfg.local_login_enabled:
        # 404, not 403: a mechanism switched off should be indistinguishable
        # from one that was never built (AC-0001-24).
        raise RotaIndisponivel()

    now = datetime.datetime.now(datetime.UTC)
    # Before the password is looked at, not after: AC-0001-03 refuses the sixth
    # attempt "even with the correct password", and a lockout a correct guess
    # walks through announces the moment the attacker got it right.
    bloqueio.verificar(sessao, email=email, now=now)

    usuario = (
        repo.by_email(sessao, email)
        if _dominio_institucional(email, cfg.dominios_institucionais)
        else None
    )
    armazenado = usuario.senha_hash if usuario and usuario.senha_hash else _HASH_SENTINELA
    senha_confere = check_senha(senha, armazenado)

    if usuario is None or not senha_confere:
        _contabilizar_falha(
            email,
            motivo="credenciais_invalidas",
            usuario_id=usuario.id if usuario else None,
            correlation_id=correlation_id,
            now=now,
        )
        raise CredenciaisInvalidas()

    if not usuario.ativo:
        # The password was right, so this is a legitimate person whose account
        # was blocked or never activated — telling them so is a kindness, and it
        # reveals nothing to anyone who does not already hold the credential.
        # Deliberately **not** counted as a failed attempt: nobody is guessing,
        # and counting it would lock out the very person about to ask the gestor
        # to unblock them.
        _auditar_falha(
            email,
            motivo=f"status_{usuario.status}",
            usuario_id=usuario.id,
            correlation_id=correlation_id,
        )
        raise UsuarioInativo()

    # In the request's transaction, so it lands with the login it belongs to.
    bloqueio.limpar(sessao, email=email)
    return usuario


def _dominio_institucional(email: str, permitidos: list[str]) -> bool:
    _, _, dominio = email.strip().lower().rpartition("@")
    return bool(dominio) and any(
        dominio == d.lower() or dominio.endswith(f".{d.lower()}") for d in permitidos
    )


def _contabilizar_falha(
    email: str,
    *,
    motivo: str,
    usuario_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
    now: datetime.datetime,
) -> None:
    """Count the attempt and record it, together, in one committed transaction.

    Together because a counter that reached five and an audit trail that does
    not say so are worse than either alone — the lockout then looks, to whoever
    investigates it later, like the system malfunctioning.
    """
    with standalone_transaction() as own_session:
        bloqueio.count_failure(
            own_session,
            email=email,
            now=now,
            usuario_id=usuario_id,
            correlation_id=correlation_id,
        )
        registrar(
            own_session, _evento_de_falha(email, motivo, usuario_id), correlation_id=correlation_id
        )


def _auditar_falha(
    email: str, *, motivo: str, usuario_id: uuid.UUID | None, correlation_id: uuid.UUID
) -> None:
    """Record the failure in its own committed transaction, without counting it.

    The request is about to raise, and the request's session will roll back —
    an audit row written in it would vanish along with the failure it records,
    leaving a trail containing only successes.

    Never the address itself: `lgpd.md` promises this table carries no personal
    data, and it can never be corrected (SPEC-0001 §8).
    """
    record_standalone(_evento_de_falha(email, motivo, usuario_id), correlation_id=correlation_id)


def _evento_de_falha(email: str, motivo: str, usuario_id: uuid.UUID | None) -> Evento:
    _, _, dominio = email.strip().lower().rpartition("@")
    return Evento(
        entidade_tipo="usuario",
        entidade_id=usuario_id or uuid.UUID(int=0),
        acao="auth.falha",
        usuario_id=usuario_id,
        dados_anteriores={
            "motivo": motivo,
            "email_hmac": digest_secret(email).hex(),
            "dominio": dominio,
        },
    )
