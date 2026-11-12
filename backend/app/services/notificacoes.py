"""The ATA notices: the daily check and the bell (SPEC-0008 AC-0008-01 to -05).

Raised once per ATA and reason (AC-0008-02), the same for every perfil
(AC-0008-03). The e-mail summary is `resumo`'s.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.constants.notas_empenho import ZERO
from app.constants.notificacoes import (
    ACAO_CRIADA,
    ACAO_LIDA,
    ACAO_TODAS_LIDAS,
    ENTIDADE,
    MOTIVO_ROTULO,
    REAJUSTE,
    SALDO_80,
    SALDO_ESGOTADO,
    VAI_VENCER,
    VENCEU,
)
from app.core.clock import local_date
from app.models.ata import Ata
from app.models.notificacao import Notificacao
from app.models.user import User
from app.repositories import ata as ata_repo
from app.repositories import notificacao as repo
from app.services import atas as atas_service
from app.services import saldo as saldo_service
from app.services.audit import Event, record
from app.services.errors import NotificacaoNotFound


@dataclass(frozen=True)
class Aviso:
    """A notice as one member reads it."""

    notificacao: Notificacao
    ata: Ata
    lida: bool

    @property
    def rotulo(self) -> str:
        """The reason in pt-BR."""
        return MOTIVO_ROTULO[self.notificacao.motivo]


@dataclass(frozen=True)
class AvisoPage:
    """A page of notices, the total and how many this member has not read."""

    items: Sequence[Aviso]
    total: int
    nao_lidas: int


# ── The daily check (AC-0008-01, -02) ───────────────────────────────────────


@dataclass(frozen=True)
class Alerta:
    """A reason that holds for an ATA now, with the key it is raised under (AC-0008-01)."""

    ata: Ata
    motivo: str
    chave: str
    dados: dict[str, Any]


def alertas(session: Session, *, at: datetime.datetime) -> list[Alerta]:
    """Every reason that holds now, ATA by ATA; the summary reads the same list (AC-0008-06)."""
    today = local_date(at)
    found: list[Alerta] = []
    for ata in ata_repo.vigentes(session):
        fim = ata.vigencia_fim.isoformat()
        if ata.vigencia_fim < today:
            found.append(Alerta(ata, VENCEU, fim, {"vigencia_fim": fim}))
        saldo = saldo_service.compute(session, ata, at=at)
        contratado = str(saldo.valor_contratado)
        if saldo.valor_contratado > ZERO and saldo.saldo_disponivel <= ZERO:
            found.append(Alerta(ata, SALDO_ESGOTADO, contratado, {"valor_contratado": contratado}))
        elif saldo.alto_consumo:
            percentual = str(saldo.comprometimento_percentual)
            found.append(
                Alerta(ata, SALDO_80, contratado, {"comprometimento_percentual": percentual})
            )
    for alert in atas_service.renewal_alert(session, at=at):
        if alert.days_remaining >= 0:
            fim = alert.view.ata.vigencia_fim.isoformat()
            found.append(Alerta(alert.view.ata, VAI_VENCER, fim, {"vigencia_fim": fim}))
    for alert in atas_service.reajuste_alert(session, at=at):
        data = alert.view.data_reajuste.isoformat()
        found.append(Alerta(alert.view.ata, REAJUSTE, data, {"data_reajuste": data}))
    return found


def check(session: Session, *, at: datetime.datetime, correlation_id: uuid.UUID) -> int:
    """Raise every notice whose reason holds now and was not raised for its key yet."""
    created = 0
    for alerta in alertas(session, at=at):
        notice = repo.raise_once(
            session,
            ata_id=alerta.ata.id,
            motivo=alerta.motivo,
            chave=alerta.chave,
            dados=alerta.dados,
            at=at,
        )
        if notice is None:
            continue
        created += 1
        record(
            session,
            Event(
                entidade_tipo=ENTIDADE,
                entidade_id=notice.id,
                acao=ACAO_CRIADA,
                user_id=None,
                # Not prior values: what the notice was raised about.
                dados_anteriores={
                    "ata_id": str(alerta.ata.id),
                    "motivo": alerta.motivo,
                    "chave": alerta.chave,
                },
            ),
            correlation_id=correlation_id,
            at=at,
        )
    return created


# ── The bell (AC-0008-04, -05) ──────────────────────────────────────────────


def page(session: Session, *, actor: User, page: int, size: int) -> AvisoPage:
    """The notices newest first, read or not for this member, and the unread count."""
    rows, total, unread = repo.page(
        session, usuario_id=actor.id, offset=(page - 1) * size, limit=size
    )
    return AvisoPage(
        items=[Aviso(notificacao=n, ata=a, lida=lida_em is not None) for n, a, lida_em in rows],
        total=total,
        nao_lidas=unread,
    )


def mark_read(
    session: Session,
    *,
    actor: User,
    notificacao_id: uuid.UUID,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> None:
    """This member read this notice; nobody else's count changes."""
    if repo.by_id(session, notificacao_id) is None:
        raise NotificacaoNotFound()
    if repo.mark_read(session, notificacao_ids=[notificacao_id], usuario_id=actor.id, at=at):
        record(
            session,
            Event(
                entidade_tipo=ENTIDADE, entidade_id=notificacao_id, acao=ACAO_LIDA, user_id=actor.id
            ),
            correlation_id=correlation_id,
            at=at,
        )


def mark_all_read(
    session: Session, *, actor: User, at: datetime.datetime, correlation_id: uuid.UUID
) -> None:
    """This member read every notice they had not."""
    ids = repo.unread_ids(session, usuario_id=actor.id)
    if repo.mark_read(session, notificacao_ids=ids, usuario_id=actor.id, at=at):
        record(
            session,
            Event(
                entidade_tipo=ENTIDADE,
                entidade_id=actor.id,
                acao=ACAO_TODAS_LIDAS,
                user_id=actor.id,
                dados_anteriores={"lidas": len(ids)},
            ),
            correlation_id=correlation_id,
            at=at,
        )
