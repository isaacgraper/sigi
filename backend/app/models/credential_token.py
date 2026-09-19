"""`TOKEN_CREDENCIAL` — invitations and password resets (SPEC-0001).

One table for both, because they are the same object: a hashed, single-use,
expiring grant to set a credential. What differs is where it came from, how long
it lives, and what the e-mail says.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

TYPES = ("convite", "redefinicao")


class CredentialToken(Base):
    """An invitation or a password reset. Only the HMAC of the token is stored.

    One table with a `tipo` rather than two: both are a hashed grant, single
    use and expirable, and what differs is origin, deadline and the text that
    delivers it.
    """

    __tablename__ = "token_credencial"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    # Only the hash. A leaked database must not yield a usable grant.
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    # Null for a self-service reset, which has no other actor (AC-0001-30).
    criado_por: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("usuario.id"))
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    expira_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    utilizado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("tipo IN ('convite', 'redefinicao')", name="ck_token_tipo"),
        CheckConstraint("expira_em > criado_em", name="ck_token_expira"),
        # The 72-hour / 1-hour rule as the database can state it. Not written as
        # `expira_em <= criado_em + interval` because `timestamptz + interval`
        # is STABLE, not IMMUTABLE, and PostgreSQL rejects it in a CHECK.
        CheckConstraint(
            "utilizado_em IS NULL OR utilizado_em <= expira_em",
            name="ck_token_uso_dentro_do_prazo",
        ),
        CheckConstraint(
            "tipo <> 'convite' OR criado_por IS NOT NULL",
            name="ck_token_convite_tem_autor",
        ),
        # One outstanding grant per user per type. `cancelado_em` is what
        # makes reissue possible: an expired-unredeemed grant still matches
        # `utilizado_em IS NULL`, and now() cannot appear in an index predicate.
        Index(
            "ux_token_credencial_aberto",
            "usuario_id",
            "tipo",
            unique=True,
            postgresql_where="utilizado_em IS NULL AND cancelado_em IS NULL",
        ),
    )
