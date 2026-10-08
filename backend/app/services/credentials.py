"""The grant that lets someone set a credential (SPEC-0001).

An invitation and a password reset are the same object: a hashed, single-use,
expiring permission to write a password. What differs is where it came from, how
long it lives, and what the message says. So the mechanics live here once, and
both `members.py` (AC-0001-10/11/25/26) and the reset flow (AC-0001-30 to -32)
call it.

Only the HMAC is stored. That is what makes "the link cannot be recovered after
the response that carried it" a property of the schema rather than a promise
about the code, which AC-0001-10 depends on.
"""

from __future__ import annotations

import datetime
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.secrets_hmac import digest_secret
from app.models.credential_token import CredentialToken
from app.repositories import credential_token as repo
from app.services.errors import (
    DomainError,
    InviteAlreadyUsed,
    InviteExpired,
    WeakPassword,
)

INVITE = "convite"
RESET = "redefinicao"

# 256 bits from a CSPRNG. The grant is looked up by equality on an indexed
# column, so its security rests entirely on being unguessable.
TOKEN_BYTES = 32


@dataclass(frozen=True)
class IssuedGrant:
    """A freshly issued grant, and the only moment its value exists."""

    token: CredentialToken
    value: str
    """The raw token. Never stored, never logged, never returned twice."""

    def link(self, path: str) -> str:
        """Build the URL the person opens to use this grant."""
        base = get_settings().frontend_base_url.rstrip("/")
        return f"{base}{path}?token={self.value}"


def issue(
    session: Session,
    *,
    user_id: uuid.UUID,
    kind: str,
    at: datetime.datetime,
    created_by: uuid.UUID | None,
) -> IssuedGrant:
    """Issue a grant, cancelling any earlier one of the same type.

    Cancelling first is not tidiness: `ux_token_credencial_aberto` permits one
    open grant per usuario per type, so a second invitation would hit a unique
    violation instead of superseding the first.
    """
    cfg = get_settings()
    hours = cfg.invite_ttl_hours if kind == INVITE else cfg.reset_ttl_hours
    repo.cancel_open(session, user_id=user_id, kind=kind, at=at)

    value = secrets.token_urlsafe(TOKEN_BYTES)
    row = repo.create(
        session,
        user_id=user_id,
        kind=kind,
        token_hash=digest_secret(value),
        expires_at=at + datetime.timedelta(hours=hours),
        created_by=created_by,
    )
    return IssuedGrant(token=row, value=value)


def redeem(
    session: Session,
    *,
    value: str,
    kind: str,
    at: datetime.datetime,
    already_used: Callable[[], DomainError] = InviteAlreadyUsed,
    expired: Callable[[], DomainError] = InviteExpired,
) -> CredentialToken:
    """Validate a grant and return it, or raise. Does **not** spend it.

    The error classes are parameters because an invitation and a reset are the
    same object with different codes: AC-0001-25 wants INVITE_*, AC-0001-31
    wants RESET_*, and one shared default would report the wrong one.

    Spending is separate because AC-0001-26 requires a rejected password to
    leave the grant usable: a typo must not burn an invitation and force the
    gestor to issue another. So the caller validates the password first and
    calls `consume` only once it is going to succeed.
    """
    row = repo.by_hash(session, digest_secret(value))
    if row is None or row.kind != kind:
        # Same answer for "no such token" and "a token of the other kind":
        # distinguishing them would say which grants exist.
        raise already_used()
    if row.utilizado_em is not None:
        raise already_used()
    if row.cancelado_em is not None or row.expires_at <= at:
        # A superseded grant reads as expired, which is what it is from the
        # holder's point of view: the gestor issued a newer one.
        raise expired()
    return row


def consume(session: Session, token: CredentialToken, *, at: datetime.datetime) -> None:
    """Spend the grant. Single use is enforced here and by the unique index."""
    repo.mark_used(session, token, at=at)


def require_strong_password(password: str) -> None:
    """Enforce the password policy (AC-0001-26).

    Length only, deliberately. Composition rules (a digit, a symbol, mixed case)
    push people towards `Senha@2026` and are weaker in practice than length;
    NIST dropped them for that reason. If the entity's own policy demands them,
    that is a spec change, not something to add here quietly.
    """
    minimum = get_settings().password_min_length
    if len(password) < minimum:
        raise WeakPassword(minimum)
