"""`ATA`, `ATA_ADITIVO` and `ATA_REAJUSTE` (SPEC-0002)."""

from __future__ import annotations

import datetime
import decimal
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ATA_STATUS = ("rascunho", "vigente", "suspensa", "encerrada", "cancelada")
ADITIVO_KINDS = ("valor", "prazo")


class Ata(Base):
    """An ata de registro de preços: the root of every supply cycle.

    `situacao_vigencia`, the reajuste date and `valor_contratado` are not columns.
    A date that follows another date goes stale the moment nobody runs the job
    that refreshes it, so each is derived on read (SPEC-0002 §2, AC-0002-18).
    """

    __tablename__ = "ata"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    number: Mapped[str] = mapped_column("numero", String(60), unique=True)
    subject: Mapped[str] = mapped_column("objeto", Text)
    organ: Mapped[str] = mapped_column("orgao", String(200))
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("fornecedor.id"))
    issued_on: Mapped[datetime.date | None] = mapped_column("data_emissao", Date)
    vigencia_inicio: Mapped[datetime.date] = mapped_column(Date)
    vigencia_fim: Mapped[datetime.date] = mapped_column(Date)
    total_value: Mapped[decimal.Decimal] = mapped_column("valor_total", Numeric(15, 2))
    budget_date: Mapped[datetime.date] = mapped_column("data_orcamento_planilhado", Date)
    status: Mapped[str] = mapped_column(String(20), server_default="rascunho")
    owner_id: Mapped[uuid.UUID] = mapped_column("responsavel_id", Uuid, ForeignKey("usuario.id"))
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('rascunho', 'vigente', 'suspensa', 'encerrada', 'cancelada')",
            name="ck_ata_status",
        ),
        # Expressed in the database as well as in the service: a constraint
        # only Python knows about is one a second writer can bypass.
        CheckConstraint("vigencia_fim > vigencia_inicio", name="ck_ata_vigencia"),
        CheckConstraint("valor_total > 0", name="ck_ata_valor_positivo"),
        Index("ix_ata_status", "status"),
        Index("ix_ata_vigencia_fim", "vigencia_fim"),
    )


class AtaAditivo(Base):
    """An aditivo of value or of prazo, with its justification (AC-0002-13)."""

    __tablename__ = "ata_aditivo"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    ata_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ata.id"))
    kind: Mapped[str] = mapped_column("tipo", String(10))
    valor_acrescimo: Mapped[decimal.Decimal | None] = mapped_column(Numeric(15, 2))
    nova_vigencia_fim: Mapped[datetime.date | None] = mapped_column(Date)
    justification: Mapped[str] = mapped_column("justificativa", Text)
    created_by: Mapped[uuid.UUID] = mapped_column("criado_por", Uuid, ForeignKey("usuario.id"))
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        CheckConstraint("tipo IN ('valor', 'prazo')", name="ck_ata_aditivo_tipo"),
        # Each kind carries its own figure and not the other's.
        CheckConstraint(
            "(tipo = 'valor' AND valor_acrescimo IS NOT NULL AND valor_acrescimo > 0"
            " AND nova_vigencia_fim IS NULL)"
            " OR (tipo = 'prazo' AND valor_acrescimo IS NULL AND nova_vigencia_fim IS NOT NULL)",
            name="ck_ata_aditivo_campos",
        ),
        Index("ix_ata_aditivo_ata_id", "ata_id"),
    )


class AtaReajuste(Base):
    """A reajuste request filed through SEI: that it was filed, and under which process.

    Nothing else. The outcome, the index and the approver are unknown (OQ-08),
    and recording a request changes no price (AC-0002-21).
    """

    __tablename__ = "ata_reajuste"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    ata_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ata.id"))
    processo_sei: Mapped[str] = mapped_column(String(30))
    requested_on: Mapped[datetime.date] = mapped_column("solicitado_em", Date)
    created_by: Mapped[uuid.UUID] = mapped_column("criado_por", Uuid, ForeignKey("usuario.id"))
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (Index("ix_ata_reajuste_ata_id", "ata_id"),)
