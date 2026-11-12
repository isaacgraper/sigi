"""The e-mail summary — SPEC-0008 v1.1, AC-0008-06 to -11.

A fixed template with the system's data of that day, sent daily, weekly on the
member's weekday, or never, as each member chose. The database is shared by
the suite, so each test looks at its own member and its own ATAs.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable
from email.message import EmailMessage
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import Settings
from app.models.audit_log import AuditLog
from app.models.notificacao import PreferenciaEmail
from app.models.user import User
from app.services import mail
from app.services import resumo as service
from app.services.resumo import Preferencia
from tests.catalogue import login, make_ata
from tests.test_notas_empenho import open_ne, setup_ata, to_stage
from tests.test_notas_fiscais import error, launched, moved

PREFS = "/api/v1/preferencias/email"
THURSDAY = datetime.datetime(2026, 11, 12, 12, 0, tzinfo=datetime.UTC)


class Collected:
    """A sender that keeps what it was given, or refuses everything."""

    def __init__(self, refuse: bool = False) -> None:
        """Start empty; `refuse` makes every send fail as an SMTP outage would."""
        self.messages: list[EmailMessage] = []
        self.refuse = refuse

    def send(self, message: EmailMessage) -> None:
        """Keep the message, or fail."""
        if self.refuse:
            raise ConnectionRefusedError("SMTP fora do ar")
        self.messages.append(message)

    def to(self, address: str | None) -> list[EmailMessage]:
        """The messages sent to one address."""
        return [m for m in self.messages if m["To"] == address]


def day(days: int) -> str:
    """A date `days` from today in São Paulo, as the API reads it."""
    return (clock.local_date(clock.now()) + datetime.timedelta(days=days)).isoformat()


def member_with(
    application: TestClient, create_user: Callable[..., User], frequencia: str, dia: int = 1
) -> tuple[dict[str, str], User]:
    """A signed-in member who chose this e-mail."""
    headers, user = login(application, create_user, "servidor")
    response = application.put(
        PREFS, json={"frequencia": frequencia, "dia_semana": dia}, headers=headers
    )
    assert response.status_code == 200, response.text
    return headers, user


def send(db_session: Session, sender: Collected, at: datetime.datetime | None = None) -> None:
    """One run's summaries, kept."""
    service.send_due(db_session, sender=sender, at=at or clock.now(), correlation_id=uuid.uuid4())
    db_session.commit()


# ── AC-0008-06, -11 — the summary ───────────────────────────────────────────


def test_AC_0008_06_AC_0008_11_the_day_on_a_fixed_template(
    application: TestClient,
    create_user: Callable[..., User],
    db_session: Session,
) -> None:
    """ATAs that need attention, NEs per etapa and NFs waiting, to the member alone."""
    gestor = login(application, create_user, "gestor")[0]
    ata = make_ata(application, gestor, vigencia_fim=day(30))
    stocked, items = setup_ata(application, gestor, [("1000", "10")])
    created = open_ne(application, gestor, stocked["id"], [(items[0]["id"], "100")])
    assert created.status_code == 201, created.text
    ne = to_stage(application, gestor, created.json()["id"], "ne_emitida")
    nf = launched(application, gestor, ne, "10", "100.00")
    moved(application, gestor, nf["id"], "enviar")
    _, member = member_with(application, create_user, "diario")
    sender = Collected()

    send(db_session, sender)

    [summary] = sender.to(member.email)
    body = summary.get_content()
    assert summary["Subject"].startswith("SIGI: resumo de ")
    assert body.startswith("Olá, Pessoa de Teste.")
    assert f"- ATA {ata['number']}: vence em" in body and f"/atas/{ata['id']}" in body
    assert "Notas de empenho" in body and "- NE emitida: " in body
    assert "- Avançaram de etapa desde o último resumo: " in body
    assert "Notas fiscais" in body and "- Em conferência: " in body
    assert "/configuracoes" in body
    others = {m["To"] for m in sender.messages} - {member.email}
    assert not any(address in body for address in others)


# ── AC-0008-07 — each member's choice ───────────────────────────────────────


def test_AC_0008_07_a_member_who_never_chose_is_weekly_on_mondays(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """The default, read back."""
    headers = login(application, create_user, "auditor")[0]

    response = application.get(PREFS, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"frequencia": "semanal", "dia_semana": 1}


def test_AC_0008_07_the_choice_is_saved_and_recorded(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """Daily, read back, and the prior choice in the history."""
    headers, user = member_with(application, create_user, "diario", 5)

    assert application.get(PREFS, headers=headers).json() == {
        "frequencia": "diario",
        "dia_semana": 5,
    }
    row = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entidade_id == user.id, AuditLog.acao == "preferencia_email.alterada"
        )
    ).one()
    assert row.dados_anteriores == {"frequencia": "semanal", "dia_semana": 1}


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"frequencia": "mensal", "dia_semana": 1}, "frequencia"),
        ({"frequencia": "semanal", "dia_semana": 8}, "dia_semana"),
    ],
)
def test_AC_0008_07_an_invalid_choice_is_named(
    application: TestClient, create_user: Callable[..., User], body: dict, field: str
) -> None:
    """A frequency or a weekday that does not exist."""
    headers = login(application, create_user, "gestor")[0]

    response = application.put(PREFS, json=body, headers=headers)

    assert response.status_code == 422
    assert field in error(response)["fields"]


def test_AC_0008_07_none_stops_the_e_mail(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """A member who chose none receives nothing."""
    _, member = member_with(application, create_user, "nenhum")
    sender = Collected()

    send(db_session, sender)

    assert sender.to(member.email) == []


# ── AC-0008-08 — when an e-mail is due ──────────────────────────────────────


@pytest.mark.parametrize(
    ("frequencia", "dia", "last", "due"),
    [
        ("diario", 1, None, True),
        ("diario", 1, THURSDAY - datetime.timedelta(days=1), True),
        ("diario", 1, THURSDAY - datetime.timedelta(hours=1), False),
        ("semanal", 4, None, True),
        ("semanal", 1, None, False),
        ("semanal", 1, THURSDAY - datetime.timedelta(days=3), False),
        ("semanal", 1, THURSDAY - datetime.timedelta(days=10), True),
        ("nenhum", 4, None, False),
    ],
)
def test_AC_0008_08_when_a_summary_is_due(
    frequencia: str, dia: int, last: datetime.datetime | None, due: bool
) -> None:
    """Daily every day once; weekly on its weekday, or later once a week has passed."""
    assert service.is_due(Preferencia(frequencia, dia), last, THURSDAY) is due


def test_AC_0008_08_a_summary_sent_today_is_not_sent_twice(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """The second run of the day finds it sent."""
    _, member = member_with(application, create_user, "diario")
    send(db_session, Collected())
    sender = Collected()

    send(db_session, sender)

    assert sender.to(member.email) == []


# ── AC-0008-09 — no SMTP, no send ───────────────────────────────────────────


def test_AC_0008_09_outside_production_nothing_leaves_the_machine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host set outside production still writes to the folder, and opens no connection."""

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("an SMTP connection was opened")

    monkeypatch.setattr(mail.smtplib, "SMTP", refuse)
    settings = Settings(
        app_env="development", smtp_host="smtp.exemplo.gov.br", mail_folder=str(tmp_path)
    )
    message = EmailMessage()
    message["To"] = "pessoa@sc.gov.br"
    message.set_content("teste")

    sender = mail.sender_for(settings)
    sender.send(message)

    assert isinstance(sender, mail.FolderSender)
    assert len(list(tmp_path.glob("*.eml"))) == 1


def test_AC_0008_09_production_with_no_host_writes_to_the_folder(tmp_path: Path) -> None:
    """No SMTP configured, no send."""
    production = Settings(app_env="production", smtp_host=None, mail_folder=str(tmp_path))
    with_host = Settings(app_env="production", smtp_host="smtp.exemplo.gov.br")

    assert isinstance(mail.sender_for(production), mail.FolderSender)
    assert isinstance(mail.sender_for(with_host), mail.SmtpSender)


# ── AC-0008-10 — a failed send ──────────────────────────────────────────────


def test_AC_0008_10_a_failed_send_is_recorded_and_sent_by_the_next_run(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """The last summary is not moved, the failure is in the history, the next run sends it."""
    _, member = member_with(application, create_user, "diario")

    send(db_session, Collected(refuse=True))

    db_session.expire_all()
    assert db_session.get(PreferenciaEmail, member.id).ultimo_envio_em is None  # type: ignore[union-attr]
    row = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entidade_id == member.id, AuditLog.acao == "resumo.envio_falhou"
        )
    ).one()
    assert row.dados_anteriores == {"erro": "ConnectionRefusedError"}

    retried = Collected()
    send(db_session, retried)

    assert len(retried.to(member.email)) == 1
    db_session.expire_all()
    assert db_session.get(PreferenciaEmail, member.id).ultimo_envio_em is not None  # type: ignore[union-attr]
