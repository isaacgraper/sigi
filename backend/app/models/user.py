"""`USUARIO` — the actor every other spec assumes (SPEC-0001)."""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import CheckConstraint, Computed, DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

PERFIS = ("gestor", "servidor", "auditor")
STATUS = ("pendente", "ativo", "bloqueado", "desativado")


class User(Base):
    """A member of the entity. `ativo` and `pseudonimo` are generated columns.

    Generated rather than written: `ativo` stored as an ordinary boolean is the
    column that one day disagrees with `status`, and here it would disagree
    about who may manage members. `pseudonimo` cannot be the target of an
    UPDATE, which is what makes the anonymisation in AC-0001-14 stable without
    a trigger.
    """

    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    # Nullable because AC-0001-14 blanks them on anonymisation, and the CHECK
    # below is what stops that being a half-done job.
    nome: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    # Nullable on purpose: an invited account exists before it has a credential
    # (AC-0001-10), and an OIDC-only account never gets one.
    senha_hash: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column("perfil", String(20))
    status: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    anonimizado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    oidc_subject: Mapped[str | None] = mapped_column(String(255), unique=True)

    # Generated, so the database keeps them and refuses an UPDATE. `ativo` was a
    # plain boolean "derived convenience", which is the column that eventually
    # disagrees with `status` — here about who may manage members.
    ativo: Mapped[bool] = mapped_column(Computed("status = 'ativo'", persisted=True))
    # The only way AC-0001-14 works: the audit trail needs a stable name for an
    # anonymised user, and it cannot be written into the audit table (forbidden
    # by lgpd.md) nor updated there afterwards (forbidden by AC-0001-27).
    pseudonimo: Mapped[str] = mapped_column(
        Text,
        Computed(
            "'USR-' || upper(substr(encode(uuid_send(id), 'hex'), 1, 12))",
            persisted=True,
        ),
    )

    __table_args__ = (
        CheckConstraint("perfil IN ('gestor', 'servidor', 'auditor')", name="ck_usuario_perfil"),
        CheckConstraint(
            "status IN ('pendente', 'ativo', 'bloqueado', 'desativado')",
            name="ck_usuario_status",
        ),
        CheckConstraint(
            "status <> 'pendente' OR senha_hash IS NULL",
            name="ck_usuario_pendente_sem_credencial",
        ),
        CheckConstraint(
            "anonimizado_em IS NULL"
            " OR (nome IS NULL AND email IS NULL"
            " AND senha_hash IS NULL AND oidc_subject IS NULL)",
            name="ck_usuario_anonimizado",
        ),
        Index("ux_usuario_pseudonimo", "pseudonimo", unique=True),
    )
