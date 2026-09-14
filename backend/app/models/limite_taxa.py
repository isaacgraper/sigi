"""`LIMITE_TAXA` — the per-source, per-route throttle of AC-0001-33 / RNF16.

`chave` is an HMAC of the source, never the address: an IP identifies a person
closely enough to sit in `lgpd.md`'s inventory, and this table is read on every
authentication request.
"""

from __future__ import annotations

import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LimiteTaxa(Base):
    __tablename__ = "limite_taxa"

    chave: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    rota: Mapped[str] = mapped_column(String(120), primary_key=True)
    janela_inicio: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    contador: Mapped[int] = mapped_column(Integer, server_default="0")

    __table_args__ = (
        CheckConstraint("contador >= 0", name="ck_limite_contador"),
        # For the purge job. This table grows with traffic and nothing keeps it
        # healthy except that job — ADR-0012 records it as a follow-up.
        Index("ix_limite_taxa_janela", "janela_inicio"),
    )
