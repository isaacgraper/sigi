"""Sending e-mail behind a port (SPEC-0008 AC-0008-07).

The transport is configuration: outside production, or with no SMTP host, a
message is written to a folder and no connection leaves the machine. The
entity's institutional SMTP is the expected one (OQ-13).
"""

from __future__ import annotations

import datetime
import smtplib
import uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from app.constants.notificacoes import MAIL_FILE_STAMP, PRODUCTION
from app.core.config import Settings, get_settings


class NotificationSender(Protocol):
    """Deliver one message, or raise `OSError` when the transport refuses it."""

    def send(self, message: EmailMessage) -> None:
        """Deliver the message."""


class FolderSender:
    """Write each message as an `.eml` file, for development and tests."""

    def __init__(self, folder: Path) -> None:
        """Write into this folder, creating it on the first message."""
        self.folder = folder

    def send(self, message: EmailMessage) -> None:
        """Write the message to the folder."""
        self.folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.UTC).strftime(MAIL_FILE_STAMP)
        (self.folder / f"{stamp}-{uuid.uuid4().hex}.eml").write_bytes(bytes(message))


class SmtpSender:
    """Send through an SMTP server, with STARTTLS unless told otherwise."""

    def __init__(self, settings: Settings) -> None:
        """Send with these settings' host, port and credentials."""
        self.settings = settings

    def send(self, message: EmailMessage) -> None:
        """Open a connection, send, close."""
        s = self.settings
        assert s.smtp_host is not None  # sender_for picks this only with a host
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_seconds) as client:
            if s.smtp_starttls:
                client.starttls()
            if s.smtp_username and s.smtp_password:
                client.login(s.smtp_username, s.smtp_password)
            client.send_message(message)


def sender_for(settings: Settings | None = None) -> NotificationSender:
    """SMTP in production with a host, the folder everywhere else (AC-0008-07)."""
    s = settings or get_settings()
    if s.app_env == PRODUCTION and s.smtp_host:
        return SmtpSender(s)
    return FolderSender(Path(s.mail_folder))
