"""The ATA notices: the daily check, the bell and the digest (SPEC-0008).

Raised once per ATA and reason (AC-0008-02), the same for every perfil
(AC-0008-03), and gathered once a day in one e-mail at the address each member
signs in with (AC-0008-06). There is no queue: the next run is the retry
(AC-0008-08).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

from sqlalchemy.orm import Session

from app.constants.notas_empenho import ZERO
from app.constants.notificacoes import (
    ACAO_CRIADA,
    ACAO_ENVIADA,
    ACAO_ENVIO_FALHOU,
    ACAO_LIDA,
    ACAO_TODAS_LIDAS,
    DATE_FORMAT,
    DIGEST_DETAIL,
    DIGEST_FOOTER,
    DIGEST_GREETING,
    DIGEST_GREETING_UNNAMED,
    DIGEST_INTRO,
    DIGEST_LINE,
    DIGEST_SUBJECT,
    ENTIDADE,
    MOTIVO_ROTULO,
    MOTIVOS,
    REAJUSTE,
    SALDO_80,
    SALDO_ESGOTADO,
    VAI_VENCER,
    VENCEU,
)
from app.core.clock import local_date
from app.core.config import get_settings
from app.models.ata import Ata
from app.models.notificacao import Notificacao
from app.models.user import User
from app.repositories import ata as ata_repo
from app.repositories import notificacao as repo
from app.repositories import user as user_repo
from app.services import atas as atas_service
from app.services import saldo as saldo_service
from app.services.audit import Event, record
from app.services.errors import NotificacaoNotFound
from app.services.mail import NotificationSender


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


@dataclass(frozen=True)
class CheckResult:
    """What one run of the daily check did."""

    criadas: int
    enviadas: int
    falhou: bool


# ── The daily check (AC-0008-01, -02) ───────────────────────────────────────


def check(session: Session, *, at: datetime.datetime, correlation_id: uuid.UUID) -> int:
    """Raise every notice whose reason holds now and was not raised for its key yet."""
    today = local_date(at)
    created = 0

    def raise_for(ata: Ata, motivo: str, chave: str, dados: dict[str, Any]) -> None:
        nonlocal created
        notice = repo.raise_once(
            session, ata_id=ata.id, motivo=motivo, chave=chave, dados=dados, at=at
        )
        if notice is None:
            return
        created += 1
        record(
            session,
            Event(
                entidade_tipo=ENTIDADE,
                entidade_id=notice.id,
                acao=ACAO_CRIADA,
                user_id=None,
                # Not prior values: what the notice was raised about.
                dados_anteriores={"ata_id": str(ata.id), "motivo": motivo, "chave": chave},
            ),
            correlation_id=correlation_id,
            at=at,
        )

    for ata in ata_repo.vigentes(session):
        fim = ata.vigencia_fim.isoformat()
        if ata.vigencia_fim < today:
            raise_for(ata, VENCEU, fim, {"vigencia_fim": fim})
        saldo = saldo_service.compute(session, ata, at=at)
        contratado = str(saldo.valor_contratado)
        if saldo.valor_contratado > ZERO and saldo.saldo_disponivel <= ZERO:
            raise_for(ata, SALDO_ESGOTADO, contratado, {"valor_contratado": contratado})
        elif saldo.alto_consumo:
            raise_for(
                ata,
                SALDO_80,
                contratado,
                {"comprometimento_percentual": str(saldo.comprometimento_percentual)},
            )
    for alert in atas_service.renewal_alert(session, at=at):
        if alert.days_remaining >= 0:
            fim = alert.view.ata.vigencia_fim.isoformat()
            raise_for(alert.view.ata, VAI_VENCER, fim, {"vigencia_fim": fim})
    for alert in atas_service.reajuste_alert(session, at=at):
        data = alert.view.data_reajuste.isoformat()
        raise_for(alert.view.ata, REAJUSTE, data, {"data_reajuste": data})
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


# ── The digest (AC-0008-06 to -09) ──────────────────────────────────────────


def digest(
    session: Session,
    *,
    sender: NotificationSender,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[int, bool]:
    """One e-mail per active member listing the notices not sent yet; (sent, failed).

    A failure keeps every notice unsent, so tomorrow's digest carries them again.
    """
    pending = repo.not_sent(session)
    if not pending:
        return 0, False
    members = user_repo.active_with_email(session)
    lines = _lines(pending)
    sent = 0
    failure: str | None = None
    for member in members:
        try:
            sender.send(_message(member, lines, len(pending)))
            sent += 1
        except OSError as exc:
            failure = type(exc).__name__
            break
    ids = [notice.id for notice, _ in pending]
    if failure is None:
        repo.mark_sent(session, ids, at)
    record(
        session,
        Event(
            entidade_tipo=ENTIDADE,
            entidade_id=uuid.uuid4(),
            acao=ACAO_ENVIO_FALHOU if failure else ACAO_ENVIADA,
            user_id=None,
            # No address and no name (AC-0008-09): how many, and what failed.
            dados_anteriores={"avisos": len(ids), "destinatarios": sent, "erro": failure},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return sent, failure is not None


def run(
    session: Session,
    *,
    sender: NotificationSender,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> CheckResult:
    """The daily check, then the digest, as the scheduled command runs them."""
    created = check(session, at=at, correlation_id=correlation_id)
    sent, failed = digest(session, sender=sender, at=at, correlation_id=correlation_id)
    return CheckResult(criadas=created, enviadas=sent, falhou=failed)


def _lines(pending: Sequence[tuple[Notificacao, Ata]]) -> list[str]:
    base = get_settings().frontend_base_url.rstrip("/")
    lines: list[str] = []
    for motivo in MOTIVOS:
        group = [(n, a) for n, a in pending if n.motivo == motivo]
        if not group:
            continue
        lines.append("")
        lines.append(MOTIVO_ROTULO[motivo])
        for notice, ata in group:
            lines.append(
                DIGEST_LINE.format(
                    numero=ata.number,
                    detalhe=_detail(notice),
                    link=f"{base}/atas/{ata.id}",
                )
            )
    return lines


def _detail(notice: Notificacao) -> str:
    dados = notice.dados or {}
    return DIGEST_DETAIL[notice.motivo].format(
        fim=_day(dados.get("vigencia_fim")),
        data=_day(dados.get("data_reajuste")),
        percentual=str(decimal.Decimal(dados.get("comprometimento_percentual", "0"))).replace(
            ".", ","
        ),
    )


def _day(iso: str | None) -> str:
    return datetime.date.fromisoformat(iso).strftime(DATE_FORMAT) if iso else ""


def _message(member: User, lines: list[str], count: int) -> EmailMessage:
    """The digest for one member, naming nobody but them (AC-0008-09)."""
    assert member.email is not None  # active_with_email selects only these
    message = EmailMessage()
    message["Subject"] = DIGEST_SUBJECT.format(count=count)
    message["From"] = get_settings().smtp_from
    message["To"] = member.email
    greeting = DIGEST_GREETING.format(name=member.nome) if member.nome else DIGEST_GREETING_UNNAMED
    message.set_content("\n".join([greeting, "", DIGEST_INTRO, *lines, "", DIGEST_FOOTER]))
    return message
