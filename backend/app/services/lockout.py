"""The per-address lockout of AC-0001-03.

Keyed on an HMAC of the **submitted** address, never on a user. That is the
whole design: v0.3 kept the counter on the account, so an address with no
account had no counter and answered 401 for ever while a real one switched to
429 — six requests told an attacker which addresses exist, which is exactly what
AC-0001-02 forbids.

This is not the rate limiting of AC-0001-33. That one is keyed on the source and
guards every auth route; this one is keyed on the address and guards guessing a
password. An attacker rotating addresses defeats this and hits that; an attacker
rotating source addresses defeats that and hits this.
"""

from __future__ import annotations

import datetime
import math
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.secrets_hmac import digest_secret
from app.repositories import login_attempt as repo
from app.services.audit import Event, record
from app.services.errors import TentativasExcedidas


def verificar(session: Session, *, email: str, now: datetime.datetime) -> None:
    """Refuse a locked address **before** the password is even looked at.

    AC-0001-03 says the sixth attempt is refused "even with the correct
    password": a lockout that a correct guess walks through would tell an
    attacker the moment they guessed right, which is the one thing the counter
    exists to hide.
    """
    row = repo.by_hmac(session, digest_secret(email))
    if row is None or row.blocked_until is None or row.blocked_until <= now:
        return
    remaining = (row.blocked_until - now).total_seconds()
    raise TentativasExcedidas(minutes=max(1, math.ceil(remaining / 60)))


def count_failure(
    session: Session,
    *,
    email: str,
    now: datetime.datetime,
    usuario_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
) -> int:
    """Count the failure, lock the address on the fifth, and audit the lock.

    Caller's session on purpose, and the caller is expected to hand it a
    transaction that **commits** — five failures that all roll back never reach
    five, which is a lockout that never locks.
    """
    cfg = get_settings()
    hmac = digest_secret(email)
    attempts = repo.count_attempt(
        session,
        email_hmac=hmac,
        now=now,
        janela=datetime.timedelta(minutes=cfg.janela_tentativas_minutos),
    )
    if attempts < cfg.max_tentativas_login:
        return attempts

    repo.block(
        session,
        email_hmac=hmac,
        until=now + datetime.timedelta(minutes=cfg.bloqueio_minutos),
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            # AC-0001-21 and this path both produce rows for callers with no
            # account; SPEC-0001 §8 allows an audit row with no actor.
            entidade_id=usuario_id or uuid.UUID(int=0),
            acao="auth.bloqueio_tentativas",
            usuario_id=usuario_id,
            dados_anteriores={"tentativas": attempts},
        ),
        correlation_id=correlation_id,
        at=now,
    )
    return attempts


def clear(session: Session, *, email: str) -> None:
    """A successful authentication resets the count for that address."""
    repo.clear(session, digest_secret(email))
