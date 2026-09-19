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
from app.core.passwords import check_password, hash_password
from app.core.secrets_hmac import digest_secret
from app.models.user import User
from app.repositories import user as repo
from app.services import lockout
from app.services.audit import Event, record, record_standalone, standalone_transaction
from app.services.errors import InactiveUser, InvalidCredentials, RouteUnavailable

# Verified against when no account matches, so that "unknown address" costs the
# same ~300 ms as "wrong password". Without it the response time is an oracle
# that answers the question AC-0001-02 forbids answering.
_HASH_SENTINEL = hash_password(secrets.token_urlsafe(32))


def authenticate_local(
    session: Session, *, email: str, password: str, correlation_id: uuid.UUID
) -> User:
    """Verify an e-mail and password, or raise.

    Wrong password, unknown e-mail and an address off the allowlist all raise
    the same error with the same shape: AC-0001-02 wants the three responses
    indistinguishable, so six attempts cannot tell an attacker which addresses
    exist.
    """
    cfg = get_settings()
    if not cfg.local_login_enabled:
        # 404, not 403: a mechanism switched off should be indistinguishable
        # from one that was never built (AC-0001-24).
        raise RouteUnavailable()

    now = datetime.datetime.now(datetime.UTC)
    # Before the password is looked at, not after: AC-0001-03 refuses the sixth
    # attempt "even with the correct password", and a lockout a correct guess
    # walks through announces the moment the attacker got it right.
    lockout.verificar(session, email=email, now=now)

    user = (
        repo.by_email(session, email)
        if _institutional_domain(email, cfg.dominios_institucionais)
        else None
    )
    armazenado = user.senha_hash if user and user.senha_hash else _HASH_SENTINEL
    senha_confere = check_password(password, armazenado)

    if user is None or not senha_confere:
        _record_failure(
            email,
            reason="credenciais_invalidas",
            usuario_id=user.id if user else None,
            correlation_id=correlation_id,
            now=now,
        )
        raise InvalidCredentials()

    if not user.ativo:
        # The password was right, so this is a legitimate person whose account
        # was blocked or never activated — telling them so is a kindness, and it
        # reveals nothing to anyone who does not already hold the credential.
        # Deliberately **not** counted as a failed attempt: nobody is guessing,
        # and counting it would lock out the very person about to ask the gestor
        # to unblock them.
        _audit_failure(
            email,
            reason=f"status_{user.status}",
            usuario_id=user.id,
            correlation_id=correlation_id,
        )
        raise InactiveUser()

    # In the request's transaction, so it lands with the login it belongs to.
    lockout.clear(session, email=email)
    return user


def _institutional_domain(email: str, permitidos: list[str]) -> bool:
    _, _, dominio = email.strip().lower().rpartition("@")
    return bool(dominio) and any(
        dominio == d.lower() or dominio.endswith(f".{d.lower()}") for d in permitidos
    )


def _record_failure(
    email: str,
    *,
    reason: str,
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
        lockout.count_failure(
            own_session,
            email=email,
            now=now,
            usuario_id=usuario_id,
            correlation_id=correlation_id,
        )
        record(
            own_session, _failure_event(email, reason, usuario_id), correlation_id=correlation_id
        )


def _audit_failure(
    email: str, *, reason: str, usuario_id: uuid.UUID | None, correlation_id: uuid.UUID
) -> None:
    """Record the failure in its own committed transaction, without counting it.

    The request is about to raise, and the request's session will roll back —
    an audit row written in it would vanish along with the failure it records,
    leaving a trail containing only successes.

    Never the address itself: `lgpd.md` promises this table carries no personal
    data, and it can never be corrected (SPEC-0001 §8).
    """
    record_standalone(_failure_event(email, reason, usuario_id), correlation_id=correlation_id)


def _failure_event(email: str, reason: str, usuario_id: uuid.UUID | None) -> Event:
    _, _, dominio = email.strip().lower().rpartition("@")
    return Event(
        entidade_tipo="usuario",
        entidade_id=usuario_id or uuid.UUID(int=0),
        acao="auth.falha",
        usuario_id=usuario_id,
        dados_anteriores={
            "motivo": reason,
            "email_hmac": digest_secret(email).hex(),
            "dominio": dominio,
        },
    )
