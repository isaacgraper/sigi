"""The per-address lockout of AC-0001-03.

Keyed on an HMAC of the **submitted** address, never on a usuario. That is the
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
from app.core.segredos import digerir
from app.repositories import tentativa as repo
from app.services.auditoria import Evento, registrar
from app.services.erros import TentativasExcedidas


def verificar(sessao: Session, *, email: str, agora: datetime.datetime) -> None:
    """Refuse a locked address **before** the password is even looked at.

    AC-0001-03 says the sixth attempt is refused "even with the correct
    password": a lockout that a correct guess walks through would tell an
    attacker the moment they guessed right, which is the one thing the counter
    exists to hide.
    """
    linha = repo.por_hmac(sessao, digerir(email))
    if linha is None or linha.bloqueado_ate is None or linha.bloqueado_ate <= agora:
        return
    restante = (linha.bloqueado_ate - agora).total_seconds()
    raise TentativasExcedidas(minutos=max(1, math.ceil(restante / 60)))


def contabilizar_falha(
    sessao: Session,
    *,
    email: str,
    agora: datetime.datetime,
    usuario_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
) -> int:
    """Count the failure, lock the address on the fifth, and audit the lock.

    Caller's session on purpose, and the caller is expected to hand it a
    transaction that **commits** — five failures that all roll back never reach
    five, which is a lockout that never locks.
    """
    cfg = get_settings()
    hmac = digerir(email)
    tentativas = repo.contabilizar(
        sessao,
        email_hmac=hmac,
        agora=agora,
        janela=datetime.timedelta(minutes=cfg.janela_tentativas_minutos),
    )
    if tentativas < cfg.max_tentativas_login:
        return tentativas

    repo.bloquear(
        sessao,
        email_hmac=hmac,
        ate=agora + datetime.timedelta(minutes=cfg.bloqueio_minutos),
    )
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            # AC-0001-21 and this path both produce rows for callers with no
            # account; SPEC-0001 §8 allows an audit row with no actor.
            entidade_id=usuario_id or uuid.UUID(int=0),
            acao="auth.bloqueio_tentativas",
            usuario_id=usuario_id,
            dados_anteriores={"tentativas": tentativas},
        ),
        correlation_id=correlation_id,
        momento=agora,
    )
    return tentativas


def limpar(sessao: Session, *, email: str) -> None:
    """A successful authentication resets the count for that address."""
    repo.limpar(sessao, digerir(email))
