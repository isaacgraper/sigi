"""Data access for the audit trail. No business logic — see `CLAUDE.md`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.historico import HistoricoMovimentacao


def inserir(sessao: Session, linha: HistoricoMovimentacao) -> None:
    """Append one row, in the caller's transaction.

    `flush` rather than leaving it to the commit: a constraint violation should
    surface where the offending call is, not at the end of the request when the
    stack no longer says who wrote it.
    """
    sessao.add(linha)
    sessao.flush()
