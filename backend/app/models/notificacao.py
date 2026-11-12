"""`NOTIFICACAO` and `NOTIFICACAO_LEITURA` — the ATA notices (SPEC-0008)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notificacao(Base):
    """One notice, raised once per ATA, reason and key (AC-0008-02).

    The key is what the reason depends on: the end of the vigência, the valor
    contratado or the reajuste date. A new aditivo changes it, and so lets the
    reason be raised again.
    """

    __tablename__ = "notificacao"
    __table_args__ = (
        UniqueConstraint("ata_id", "motivo", "chave", name="uq_notificacao_ata_motivo_chave"),
        Index("ix_notificacao_criada_em", "criada_em"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    ata_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ata.id"))
    motivo: Mapped[str] = mapped_column(String(20))
    chave: Mapped[str] = mapped_column(String(40))
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    criada_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    # Set once the daily digest carried it; a failed send leaves it empty (AC-0008-08).
    enviada_em: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class NotificacaoLeitura(Base):
    """That one member read one notice; another member's reading is not theirs (AC-0008-05)."""

    __tablename__ = "notificacao_leitura"

    notificacao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notificacao.id"), primary_key=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), primary_key=True)
    lida_em: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
