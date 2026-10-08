"""Data access for the audit trail. No business logic — see `CLAUDE.md`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def insert_row(session: Session, row: AuditLog) -> None:
    """Append one row, in the caller's transaction.

    `flush` rather than leaving it to the commit: a constraint violation should
    surface where the offending call is, not at the end of the request when the
    stack no longer says who wrote it.
    """
    session.add(row)
    session.flush()
