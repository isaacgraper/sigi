"""`HISTORICO_MOVIMENTACAO` — the append-only audit trail (RN06, RNF08).

Three things about this table are **not** expressible in SQLAlchemy metadata and
live only in the migration: `PARTITION BY RANGE (ocorrido_em)`, the seven yearly
partitions, and the `BEFORE UPDATE OR DELETE` trigger that makes it append-only.
`migrations/env.py` filters the partitions out of autogenerate so it does not
propose dropping them — see the comment there, and ADR-0004.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HistoricoMovimentacao(Base):
    """The append-only audit trail, partitioned by year (RN06, ADR-0004).

    Never updated and never deleted, enforced in the database rather than here:
    a REVOKE for the application role and an ENABLE ALWAYS trigger for everyone
    else.
    """

    __tablename__ = "historico_movimentacao"

    # The primary key includes the partitioning column because PostgreSQL
    # refuses a unique constraint on a partitioned table that omits one. The
    # cost, stated rather than discovered: `id` alone is no longer
    # uniqueness-enforced.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    ocorrido_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    entidade_tipo: Mapped[str] = mapped_column(String(40))
    entidade_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    acao: Mapped[str] = mapped_column(String(60))
    # Nullable: AC-0001-20 and AC-0001-21 both audit callers with no account.
    # `ON DELETE` stays at NO ACTION, which is what makes invariant I4 a
    # database fact rather than a promise.
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("usuario.id"))
    dados_anteriores: Mapped[dict | None] = mapped_column(JSONB)
    justificativa: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid)

    __table_args__ = (
        # In a table that can never be corrected, a typo ("Usuario" for
        # "usuario") is permanent and silently breaks every later filter. The
        # constraint is on shape, not on the value set — each new spec adds
        # values, so an enum would be wrong.
        CheckConstraint(r"acao ~ '^[a-z_]+\.[a-z_]+$'", name="ck_hist_acao_forma"),
        CheckConstraint("entidade_tipo ~ '^[a-z_]+$'", name="ck_hist_entidade_forma"),
        Index("ix_hist_entidade_tipo", "entidade_tipo", "entidade_id", "ocorrido_em"),
        Index("ix_hist_usuario_id", "usuario_id", "ocorrido_em"),
        # "Everything that happened in one request" — a query the auditor wants
        # and which AC-0007-08's two indexes do not serve.
        Index("ix_hist_correlation_id", "correlation_id"),
    )
