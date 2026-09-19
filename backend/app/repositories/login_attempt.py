"""Data access for `tentativa_login`. The policy lives in the service."""

from __future__ import annotations

import datetime

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.login_attempt import LoginAttempt


def by_hmac(session: Session, email_hmac: bytes) -> LoginAttempt | None:
    """Find the counter row for an address HMAC, or None."""
    return session.get(LoginAttempt, email_hmac)


def count_attempt(
    session: Session, *, email_hmac: bytes, now: datetime.datetime, janela: datetime.timedelta
) -> int:
    """Count one failure and return the running total.

    One statement, because two concurrent failures on the same address must not
    both read "3" and both write "4". `ON CONFLICT DO UPDATE` takes the row lock
    that makes the increment atomic; a read-then-write here would let an
    attacker escape the ceiling simply by sending the guesses in parallel.

    The window decays by inactivity: a failure whose predecessor is older than
    `janela` starts a new count rather than continuing the old one. Without the
    timestamp the column would express "five failures ever", which locks an
    address out over failures spread across months.
    """
    dentro_da_janela = LoginAttempt.ultima_em > now - janela
    statement = (
        insert(LoginAttempt)
        .values(email_hmac=email_hmac, attempts=1, ultima_em=now)
        .on_conflict_do_update(
            index_elements=[LoginAttempt.email_hmac],
            set_={
                "tentativas": case((dentro_da_janela, LoginAttempt.attempts + 1), else_=1),
                "ultima_em": now,
                # A lock whose window has decayed is gone, not merely expired:
                # leaving it set would make the next failure look like the
                # sixth of a series that ended fifteen minutes ago.
                "bloqueado_ate": case((dentro_da_janela, LoginAttempt.blocked_until), else_=None),
            },
        )
        .returning(LoginAttempt.attempts)
    )
    return int(session.execute(statement).scalar_one())


def block(session: Session, *, email_hmac: bytes, until: datetime.datetime) -> None:
    """Mark an address blocked until the given instant."""
    row = session.get(LoginAttempt, email_hmac)
    if row is not None:
        row.blocked_until = until
    session.flush()


def clear(session: Session, email_hmac: bytes) -> None:
    """Drop the counter row, which is how a successful login resets it."""
    session.execute(delete(LoginAttempt).where(LoginAttempt.email_hmac == email_hmac))
    session.flush()


def count(session: Session, email_hmac: bytes) -> int:
    """How many failures the address currently carries."""
    value = session.scalar(
        select(LoginAttempt.attempts).where(LoginAttempt.email_hmac == email_hmac)
    )
    return int(value or 0)
