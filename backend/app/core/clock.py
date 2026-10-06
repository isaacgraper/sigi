"""The one place the application reads the time.

A function in a module, not a call to `datetime.now()` scattered about, so a
test freezes it with `monkeypatch.setattr("app.core.clock.now", ...)` and never
touches the system clock. AC-0002-15 and -20 need three dates against the same
rows with no write in between, and that is not testable any other way.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

# Timestamps are stored UTC and presented in America/Sao_Paulo (CLAUDE.md), and a
# vigência ends on a calendar day of the entity, not of Greenwich.
LOCAL = ZoneInfo("America/Sao_Paulo")


def now() -> datetime.datetime:
    """The current instant, in UTC."""
    return datetime.datetime.now(datetime.UTC)


def local_date(at: datetime.datetime) -> datetime.date:
    """The calendar day an instant falls on in the entity's time zone."""
    return at.astimezone(LOCAL).date()
