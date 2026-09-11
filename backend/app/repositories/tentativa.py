"""Data access for `tentativa_login`. The policy lives in the service."""

from __future__ import annotations

import datetime

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.tentativa_login import TentativaLogin


def por_hmac(sessao: Session, email_hmac: bytes) -> TentativaLogin | None:
    return sessao.get(TentativaLogin, email_hmac)


def contabilizar(
    sessao: Session, *, email_hmac: bytes, agora: datetime.datetime, janela: datetime.timedelta
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
    dentro_da_janela = TentativaLogin.ultima_em > agora - janela
    declaracao = (
        insert(TentativaLogin)
        .values(email_hmac=email_hmac, tentativas=1, ultima_em=agora)
        .on_conflict_do_update(
            index_elements=[TentativaLogin.email_hmac],
            set_={
                "tentativas": case((dentro_da_janela, TentativaLogin.tentativas + 1), else_=1),
                "ultima_em": agora,
                # A lock whose window has decayed is gone, not merely expired:
                # leaving it set would make the next failure look like the
                # sixth of a series that ended fifteen minutes ago.
                "bloqueado_ate": case((dentro_da_janela, TentativaLogin.bloqueado_ate), else_=None),
            },
        )
        .returning(TentativaLogin.tentativas)
    )
    return int(sessao.execute(declaracao).scalar_one())


def bloquear(sessao: Session, *, email_hmac: bytes, ate: datetime.datetime) -> None:
    linha = sessao.get(TentativaLogin, email_hmac)
    if linha is not None:
        linha.bloqueado_ate = ate
    sessao.flush()


def limpar(sessao: Session, email_hmac: bytes) -> None:
    sessao.execute(delete(TentativaLogin).where(TentativaLogin.email_hmac == email_hmac))
    sessao.flush()


def contagem(sessao: Session, email_hmac: bytes) -> int:
    valor = sessao.scalar(
        select(TentativaLogin.tentativas).where(TentativaLogin.email_hmac == email_hmac)
    )
    return int(valor or 0)
