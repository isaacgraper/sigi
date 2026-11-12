"""The e-mail summary on a fixed template (SPEC-0008 AC-0008-06 to -11).

Built on the application server with the system's data of that day: the ATAs
that need attention, the NEs per etapa and the NFs waiting on someone. Each
member receives it daily, weekly on their weekday, or never, as they chose
(AC-0008-07). There is no queue: a failed send leaves the member's last summary
where it was, and the next run sends it again (AC-0008-10).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.constants.notas_empenho import STAGE_LABEL, STAGES
from app.constants.notificacoes import (
    ACAO_PREFERENCIA,
    ACAO_RESUMO_ENVIADO,
    ACAO_RESUMO_FALHOU,
    ATA_DETAIL,
    ATA_LINE,
    DATE_FORMAT,
    DEFAULT_DIA_SEMANA,
    DEFAULT_FREQUENCIA,
    DIA_INVALIDO,
    DIARIO,
    FOOTER,
    FREQUENCIA_INVALIDA,
    FREQUENCIAS,
    GREETING,
    GREETING_UNNAMED,
    INTRO,
    MOTIVO_ROTULO,
    MOTIVOS,
    NE_ADVANCE_ACAO,
    NE_ADVANCED_LINE,
    NE_STAGE_LINE,
    NENHUM,
    NF_COUNTS,
    NF_LINE,
    NONE_LINE,
    PREFERENCIA_ENTIDADE,
    RESUMO_ENTIDADE,
    SECTION_ATAS,
    SECTION_NES,
    SECTION_NFS,
    SEMANAL,
    SUBJECT,
    WEEK_DAYS,
)
from app.core.clock import local_date
from app.core.config import get_settings
from app.models.user import User
from app.repositories import audit_log as audit_repo
from app.repositories import nota_empenho as ne_repo
from app.repositories import nota_fiscal as nf_repo
from app.repositories import preferencia_email as prefs_repo
from app.repositories import user as user_repo
from app.services import notificacoes
from app.services.audit import Event, record
from app.services.errors import InvalidData
from app.services.mail import NotificationSender


@dataclass(frozen=True)
class Preferencia:
    """A member's choice, the default when they never made one (AC-0008-07)."""

    frequencia: str
    dia_semana: int


@dataclass(frozen=True)
class Dia:
    """The system's data of one day, the same for every recipient (AC-0008-06)."""

    alertas: Sequence[notificacoes.Alerta]
    nes_por_etapa: dict[str, int]
    nfs: dict[str, int]


@dataclass(frozen=True)
class RunResult:
    """What one run of the scheduled command did."""

    criadas: int
    enviados: int
    falhas: int


# ── Each member's choice (AC-0008-07) ───────────────────────────────────────


def preference_of(session: Session, actor: User) -> Preferencia:
    """The member's choice, or weekly on Mondays when they never chose."""
    stored = prefs_repo.of(session, actor.id)
    if stored is None:
        return Preferencia(DEFAULT_FREQUENCIA, DEFAULT_DIA_SEMANA)
    return Preferencia(stored.frequencia, stored.dia_semana)


def set_preference(
    session: Session,
    *,
    actor: User,
    frequencia: str,
    dia_semana: int,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> Preferencia:
    """Save the member's choice, effective from the next run."""
    fields: dict[str, str] = {}
    if frequencia not in FREQUENCIAS:
        fields["frequencia"] = FREQUENCIA_INVALIDA
    if not 1 <= dia_semana <= WEEK_DAYS:
        fields["dia_semana"] = DIA_INVALIDO
    if fields:
        raise InvalidData(fields)
    before = preference_of(session, actor)
    prefs_repo.save(
        session, usuario_id=actor.id, frequencia=frequencia, dia_semana=dia_semana, at=at
    )
    record(
        session,
        Event(
            entidade_tipo=PREFERENCIA_ENTIDADE,
            entidade_id=actor.id,
            acao=ACAO_PREFERENCIA,
            user_id=actor.id,
            dados_anteriores={"frequencia": before.frequencia, "dia_semana": before.dia_semana},
        ),
        correlation_id=correlation_id,
        at=at,
    )
    return Preferencia(frequencia, dia_semana)


def is_due(preferencia: Preferencia, last: datetime.datetime | None, at: datetime.datetime) -> bool:
    """Whether a member's summary goes out on this run (AC-0008-08)."""
    today = local_date(at)
    if last is not None and local_date(last) == today:
        return False
    if preferencia.frequencia == DIARIO:
        return True
    if preferencia.frequencia == SEMANAL:
        if today.isoweekday() == preferencia.dia_semana:
            return True
        # Any later day once the last one is over a week old: that is what
        # retries a weekly summary whose day failed.
        return last is not None and (today - local_date(last)).days > WEEK_DAYS
    return False


# ── The day's data and the template (AC-0008-06, -11) ───────────────────────


def day_of(session: Session, *, at: datetime.datetime) -> Dia:
    """What the summary says about the system today."""
    by_status = ne_repo.count_by_status(session)
    nfs: dict[str, int] = {}
    for key, _ in NF_COUNTS:
        _, total = nf_repo.page(
            session,
            status=None if key == "quarentena" else key,
            nota_empenho_id=None,
            quarentena=True if key == "quarentena" else None,
            offset=0,
            limit=1,
        )
        nfs[key] = total
    return Dia(
        alertas=notificacoes.alertas(session, at=at),
        nes_por_etapa={stage: by_status.get(stage, 0) for stage in STAGES},
        nfs=nfs,
    )


def message(member: User, dia: Dia, *, advanced: int, at: datetime.datetime) -> EmailMessage:
    """One member's summary, naming nobody but them (AC-0008-11)."""
    assert member.email is not None  # active_with_email selects only these
    base = get_settings().frontend_base_url.rstrip("/")
    today = local_date(at).strftime(DATE_FORMAT)
    lines = [
        GREETING.format(name=member.nome) if member.nome else GREETING_UNNAMED,
        "",
        INTRO.format(dia=today),
        "",
        SECTION_ATAS,
    ]
    for motivo in MOTIVOS:
        group = [a for a in dia.alertas if a.motivo == motivo]
        lines.append(f"{MOTIVO_ROTULO[motivo]}:")
        if not group:
            lines.append(NONE_LINE)
        for alerta in group:
            lines.append(
                ATA_LINE.format(
                    numero=alerta.ata.number,
                    detalhe=_detail(alerta),
                    link=f"{base}/atas/{alerta.ata.id}",
                )
            )
    lines += ["", SECTION_NES]
    lines += [
        NE_STAGE_LINE.format(etapa=STAGE_LABEL[stage], count=count)
        for stage, count in dia.nes_por_etapa.items()
    ]
    lines.append(NE_ADVANCED_LINE.format(count=advanced))
    lines += ["", SECTION_NFS]
    lines += [NF_LINE.format(rotulo=rotulo, count=dia.nfs[key]) for key, rotulo in NF_COUNTS]
    lines += ["", FOOTER.format(link=f"{base}/configuracoes")]

    email = EmailMessage()
    email["Subject"] = SUBJECT.format(dia=today)
    email["From"] = get_settings().smtp_from
    email["To"] = member.email
    email.set_content("\n".join(lines))
    return email


def _detail(alerta: notificacoes.Alerta) -> str:
    dados = alerta.dados
    return ATA_DETAIL[alerta.motivo].format(
        fim=_day(dados.get("vigencia_fim")),
        data=_day(dados.get("data_reajuste")),
        percentual=str(decimal.Decimal(dados.get("comprometimento_percentual", "0"))).replace(
            ".", ","
        ),
    )


def _day(iso: str | None) -> str:
    return datetime.date.fromisoformat(iso).strftime(DATE_FORMAT) if iso else ""


# ── The send (AC-0008-08 to -10) ────────────────────────────────────────────


def send_due(
    session: Session,
    *,
    sender: NotificationSender,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> tuple[int, int]:
    """Send every summary due on this run; (sent, failed)."""
    members = user_repo.active_with_email(session)
    stored = prefs_repo.of_members(session, {member.id for member in members})
    dia: Dia | None = None
    sent = failed = 0
    for member in members:
        row = stored.get(member.id)
        preferencia = (
            Preferencia(row.frequencia, row.dia_semana)
            if row
            else Preferencia(DEFAULT_FREQUENCIA, DEFAULT_DIA_SEMANA)
        )
        if preferencia.frequencia == NENHUM:
            continue
        last = row.ultimo_envio_em if row else None
        if not is_due(preferencia, last, at):
            continue
        dia = dia or day_of(session, at=at)
        since = last or at - datetime.timedelta(
            days=1 if preferencia.frequencia == DIARIO else WEEK_DAYS
        )
        advanced = audit_repo.count_acao_since(session, acao=NE_ADVANCE_ACAO, since=since)
        try:
            sender.send(message(member, dia, advanced=advanced, at=at))
        except OSError as exc:
            failed += 1
            _record(session, member, ACAO_RESUMO_FALHOU, type(exc).__name__, at, correlation_id)
            continue
        sent += 1
        prefs_repo.mark_sent(
            session,
            usuario_id=member.id,
            at=at,
            frequencia=preferencia.frequencia,
            dia_semana=preferencia.dia_semana,
        )
        _record(session, member, ACAO_RESUMO_ENVIADO, None, at, correlation_id)
    return sent, failed


def _record(
    session: Session,
    member: User,
    acao: str,
    erro: str | None,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> None:
    # The member by id only: no address in the history (AC-0008-11).
    record(
        session,
        Event(
            entidade_tipo=RESUMO_ENTIDADE,
            entidade_id=member.id,
            acao=acao,
            user_id=None,
            dados_anteriores={"erro": erro} if erro else None,
        ),
        correlation_id=correlation_id,
        at=at,
    )


def run(
    session: Session,
    *,
    sender: NotificationSender,
    at: datetime.datetime,
    correlation_id: uuid.UUID,
) -> RunResult:
    """The daily check, then the summaries due, as the scheduled command runs them."""
    created = notificacoes.check(session, at=at, correlation_id=correlation_id)
    sent, failed = send_due(session, sender=sender, at=at, correlation_id=correlation_id)
    return RunResult(criadas=created, enviados=sent, falhas=failed)
