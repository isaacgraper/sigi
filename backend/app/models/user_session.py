"""`SESSAO_FAMILIA` and `SESSAO` — server-side refresh state (SPEC-0001).

A refresh token that cannot be invalidated before its own expiry is not a
session, it is a seven-day bearer grant — so the state lives here rather than
only in the token (AC-0001-06/07).
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

REVOCATION_REASONS = (
    "rotacao",
    "logout",
    "replay",
    "desativacao",
    "lockout",
    "redefinicao",
)


class SessionFamily(Base):
    """One row per login. Binds a family to exactly one user (DB11).

    Without this, one family could span two users, and revoking it would revoke
    another person's sessions.
    """

    __tablename__ = "sessao_familia"

    family: Mapped[uuid.UUID] = mapped_column("familia", Uuid, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id"))
    criada_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    revogada_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("familia", "usuario_id", name="uq_sessao_familia_usuario"),)


class UserSession(Base):
    """One refresh token in a family. Only its HMAC is stored.

    `generation` replaces a `substituido_por_id` pointer, which was a second
    representation of what `family` already said and could disagree with it.
    """

    __tablename__ = "sessao"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    family: Mapped[uuid.UUID] = mapped_column("familia", Uuid)
    # Replaced a `substituido_por_id` self-reference, which was a second
    # representation of what `family` already carried and could disagree with
    # it. Family revocation never walks a chain — it is one UPDATE.
    generation: Mapped[int] = mapped_column("geracao", SmallInteger)
    refresh_token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    emitido_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    expira_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    revogado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    # Not cosmetic: `revogado_em` alone cannot tell the replay handler whether
    # it is looking at a rotated token or a logged-out one, and SPEC-0001 §8's
    # `auth.refresh_replay` row has no reason field to write without it.
    revogado_motivo: Mapped[str | None] = mapped_column(String(20))

    __table_args__ = (
        UniqueConstraint("familia", "geracao", name="uq_sessao_geracao"),
        ForeignKeyConstraint(
            ["familia", "usuario_id"],
            ["sessao_familia.familia", "sessao_familia.usuario_id"],
            name="fk_sessao_familia",
        ),
        CheckConstraint("expira_em > emitido_em", name="ck_sessao_expira"),
        CheckConstraint(
            "revogado_em IS NULL OR revogado_em >= emitido_em", name="ck_sessao_revogado"
        ),
        CheckConstraint(
            "revogado_motivo IN"
            " ('rotacao', 'logout', 'replay', 'desativacao', 'lockout', 'redefinicao')",
            name="ck_sessao_motivo_valor",
        ),
        CheckConstraint(
            "(revogado_em IS NULL) = (revogado_motivo IS NULL)",
            name="ck_sessao_motivo_par",
        ),
        # Serves the family kill of AC-0001-07.
        Index(
            "ix_sessao_familia_ativa",
            "familia",
            postgresql_where="revogado_em IS NULL",
        ),
        # Serves block and deactivate (AC-0001-08/12).
        Index(
            "ix_sessao_usuario_ativa",
            "usuario_id",
            postgresql_where="revogado_em IS NULL",
        ),
        Index("ix_sessao_expira", "expira_em"),
    )
