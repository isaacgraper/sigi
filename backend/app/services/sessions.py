"""Opening, rotating and ending a session (AC-0001-01, -06, -07).

A refresh token that cannot be invalidated before its own expiry is not a
session, it is a seven-day bearer grant. So the state lives in the database and
this is where it is manipulated.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.secrets_hmac import digest_secret
from app.core.security import generate_refresh_token, issue_access_token
from app.repositories import session as repo
from app.services.audit import Event, record, standalone_transaction
from app.services.errors import InvalidRefresh


@dataclass(frozen=True)
class TokenPair:
    """An access token and the refresh token issued with it."""

    access_token: str
    refresh_token: str
    expira_em: datetime.datetime


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def open_session(
    session: Session,
    *,
    usuario_id: uuid.UUID,
    role: str,
    correlation_id: uuid.UUID,
    mecanismo: str,
) -> TokenPair:
    """Open a session: a new family, generation one, and a token pair.

    The refresh token is returned to the caller and stored only as its HMAC,
    so a leaked database yields nothing that can be replayed.
    """
    cfg = get_settings()
    now = _now()
    family = repo.create_familia(session, usuario_id)
    value, token_hash = generate_refresh_token()
    expires = now + datetime.timedelta(days=cfg.refresh_token_ttl_dias)
    repo.create(
        session,
        usuario_id=usuario_id,
        family=family,
        generation=1,
        token_hash=token_hash,
        expira_em=expires,
    )
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=usuario_id,
            acao="auth.login",
            usuario_id=usuario_id,
            dados_anteriores={"mecanismo": mecanismo},
        ),
        correlation_id=correlation_id,
    )
    return TokenPair(
        access_token=issue_access_token(usuario_id=usuario_id, role=role, now=now),
        refresh_token=value,
        expira_em=expires,
    )


def rotate(
    session: Session, *, refresh_token: str, perfil_de: RoleResolver, correlation_id: uuid.UUID
) -> TokenPair:
    """Exchange a refresh token for a new pair, or detect a replay.

    The lookup deliberately does not filter out revoked rows: a replayed token
    has to be *found* for the replay to be recognised. Filtering in SQL would
    yield "not found", a plain 401 and no family revocation — the criterion
    silently unmet behind a response that looks right.
    """
    cfg = get_settings()
    now = _now()
    current = repo.by_hash(session, digest_secret(refresh_token))
    if current is None:
        raise InvalidRefresh()

    if current.revogado_em is not None:
        # Someone is using a token that was already rotated, logged out or
        # revoked. Whoever holds the live one may be the thief, so the whole
        # family goes — that is what turns theft into a detectable event.
        _revoke_familia_after_replay(
            family=current.family,
            usuario_id=current.usuario_id,
            sessao_id=current.id,
            at=now,
            correlation_id=correlation_id,
        )
        raise InvalidRefresh()

    if current.expira_em <= now:
        raise InvalidRefresh()

    role = perfil_de(current.usuario_id)
    value, token_hash = generate_refresh_token()
    current.revogado_em = now
    current.revogado_motivo = "rotacao"
    nova = repo.create(
        session,
        usuario_id=current.usuario_id,
        family=current.family,
        generation=repo.next_geracao(session, current.family),
        token_hash=token_hash,
        expira_em=now + datetime.timedelta(days=cfg.refresh_token_ttl_dias),
    )
    return TokenPair(
        access_token=issue_access_token(usuario_id=current.usuario_id, role=role, now=now),
        refresh_token=value,
        expira_em=nova.expira_em,
    )


def close(session: Session, *, refresh_token: str, correlation_id: uuid.UUID) -> None:
    """Log out: revoke the whole family, not just the presented token.

    Revoking one generation would leave every other device logged in, which is
    not what anyone means by "sair".
    """
    now = _now()
    current = repo.by_hash(session, digest_secret(refresh_token))
    if current is None:
        # Nothing to revoke, and saying so would confirm which tokens exist.
        return
    repo.revoke_familia(session, current.family, reason="logout", at=now)
    record(
        session,
        Event(
            entidade_tipo="usuario",
            entidade_id=current.usuario_id,
            acao="auth.logout",
            usuario_id=current.usuario_id,
        ),
        correlation_id=correlation_id,
    )


def _revoke_familia_after_replay(
    *,
    family: uuid.UUID,
    usuario_id: uuid.UUID,
    sessao_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> None:
    """Revoke the family and record the replay, in a transaction of their own.

    Both have to outlive the request, and the request is about to raise: written
    in the caller's session they would roll back with it, leaving the stolen
    family alive and the theft unrecorded — the detection reduced to a 401 that
    looks identical to a typo.
    """
    with standalone_transaction() as own_session:
        revoked = repo.revoke_familia(own_session, family, reason="replay", at=at)
        record(
            own_session,
            Event(
                entidade_tipo="usuario",
                entidade_id=usuario_id,
                acao="auth.refresh_replay",
                usuario_id=usuario_id,
                dados_anteriores={
                    "sessao_id": str(sessao_id),
                    "sessoes_derrubadas": revoked,
                },
            ),
            correlation_id=correlation_id,
        )


class RoleResolver:
    """Callable that answers "what role does this user have *now*".

    A protocol rather than a repository import, so this module stays unaware of
    how a user is loaded — and so the refreshed access token carries the
    current role rather than the one minted at login.
    """

    def __call__(self, usuario_id: uuid.UUID) -> str:  # pragma: no cover - protocol
        """Return the role, or raise if the user may no longer hold one."""
        raise NotImplementedError
