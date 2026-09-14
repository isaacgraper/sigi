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
from app.core.segredos import digest_secret
from app.core.seguranca import generate_refresh_token, issue_access_token
from app.repositories import sessao as repo
from app.services.auditoria import Evento, registrar, standalone_transaction
from app.services.erros import RefreshInvalido


@dataclass(frozen=True)
class ParDeTokens:
    access_token: str
    refresh_token: str
    expira_em: datetime.datetime


def _agora() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def abrir(
    sessao: Session,
    *,
    usuario_id: uuid.UUID,
    perfil: str,
    correlation_id: uuid.UUID,
    mecanismo: str,
) -> ParDeTokens:
    cfg = get_settings()
    now = _agora()
    familia = repo.create_familia(sessao, usuario_id)
    valor, token_hash = generate_refresh_token()
    expira = now + datetime.timedelta(days=cfg.refresh_token_ttl_dias)
    repo.criar(
        sessao,
        usuario_id=usuario_id,
        familia=familia,
        geracao=1,
        token_hash=token_hash,
        expira_em=expira,
    )
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario_id,
            acao="auth.login",
            usuario_id=usuario_id,
            dados_anteriores={"mecanismo": mecanismo},
        ),
        correlation_id=correlation_id,
    )
    return ParDeTokens(
        access_token=issue_access_token(usuario_id=usuario_id, perfil=perfil, now=now),
        refresh_token=valor,
        expira_em=expira,
    )


def rotacionar(
    sessao: Session, *, refresh_token: str, perfil_de: PerfilResolver, correlation_id: uuid.UUID
) -> ParDeTokens:
    """Exchange a refresh token for a new pair, or detect a replay.

    The lookup deliberately does not filter out revoked rows: a replayed token
    has to be *found* for the replay to be recognised. Filtering in SQL would
    yield "not found", a plain 401 and no family revocation — the criterion
    silently unmet behind a response that looks right.
    """
    cfg = get_settings()
    now = _agora()
    atual = repo.by_hash(sessao, digest_secret(refresh_token))
    if atual is None:
        raise RefreshInvalido()

    if atual.revogado_em is not None:
        # Someone is using a token that was already rotated, logged out or
        # revoked. Whoever holds the live one may be the thief, so the whole
        # family goes — that is what turns theft into a detectable event.
        _derrubar_familia_apos_replay(
            familia=atual.familia,
            usuario_id=atual.usuario_id,
            sessao_id=atual.id,
            at=now,
            correlation_id=correlation_id,
        )
        raise RefreshInvalido()

    if atual.expira_em <= now:
        raise RefreshInvalido()

    perfil = perfil_de(atual.usuario_id)
    valor, token_hash = generate_refresh_token()
    atual.revogado_em = now
    atual.revogado_motivo = "rotacao"
    nova = repo.criar(
        sessao,
        usuario_id=atual.usuario_id,
        familia=atual.familia,
        geracao=repo.next_geracao(sessao, atual.familia),
        token_hash=token_hash,
        expira_em=now + datetime.timedelta(days=cfg.refresh_token_ttl_dias),
    )
    return ParDeTokens(
        access_token=issue_access_token(usuario_id=atual.usuario_id, perfil=perfil, now=now),
        refresh_token=valor,
        expira_em=nova.expira_em,
    )


def encerrar(sessao: Session, *, refresh_token: str, correlation_id: uuid.UUID) -> None:
    """Log out: revoke the whole family, not just the presented token.

    Revoking one generation would leave every other device logged in, which is
    not what anyone means by "sair".
    """
    now = _agora()
    atual = repo.by_hash(sessao, digest_secret(refresh_token))
    if atual is None:
        # Nothing to revoke, and saying so would confirm which tokens exist.
        return
    repo.revoke_familia(sessao, atual.familia, motivo="logout", at=now)
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=atual.usuario_id,
            acao="auth.logout",
            usuario_id=atual.usuario_id,
        ),
        correlation_id=correlation_id,
    )


def _derrubar_familia_apos_replay(
    *,
    familia: uuid.UUID,
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
        revoked = repo.revoke_familia(own_session, familia, motivo="replay", at=at)
        registrar(
            own_session,
            Evento(
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


class PerfilResolver:
    """Callable that answers "what perfil does this usuario have *now*".

    A protocol rather than a repository import, so this module stays unaware of
    how a usuario is loaded — and so the refreshed access token carries the
    current perfil rather than the one minted at login.
    """

    def __call__(self, usuario_id: uuid.UUID) -> str:  # pragma: no cover - protocol
        raise NotImplementedError
