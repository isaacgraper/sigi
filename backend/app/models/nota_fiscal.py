"""`NOTA_FISCAL` and `ITEM_NOTA_FISCAL` (SPEC-0005)."""

from __future__ import annotations

import datetime
import decimal
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotaFiscal(Base):
    """The fornecedor's invoice against an issued NE, and its conferência.

    It reaches its ATA only through the NE (RN02). `fornecedor_id` is the NE's
    ATA's, copied so that the número is unique per fornecedor as the document is.
    """

    __tablename__ = "nota_fiscal"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    numero: Mapped[str] = mapped_column(String(20))
    issued_on: Mapped[datetime.date] = mapped_column("data_emissao", Date)
    value: Mapped[decimal.Decimal] = mapped_column("valor", Numeric(15, 2))
    nota_empenho_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("nota_empenho.id"))
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("fornecedor.id"))
    owner_id: Mapped[uuid.UUID] = mapped_column("responsavel_id", Uuid, ForeignKey("usuario.id"))
    status: Mapped[str] = mapped_column(String(20), server_default="aguardando")
    return_reason: Mapped[str | None] = mapped_column("justificativa_devolucao", Text)
    quarentena: Mapped[bool] = mapped_column(Boolean, server_default="false")
    motivo_quarentena: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('aguardando', 'em_conferencia', 'aprovada', 'devolvida')",
            name="ck_nota_fiscal_status",
        ),
        CheckConstraint("numero ~ '^[A-Za-z0-9]{1,20}$'", name="ck_nota_fiscal_numero"),
        CheckConstraint("valor > 0", name="ck_nota_fiscal_valor"),
        CheckConstraint(
            "status <> 'devolvida' OR justificativa_devolucao IS NOT NULL",
            name="ck_nota_fiscal_devolucao_justificada",
        ),
        CheckConstraint(
            "quarentena = (motivo_quarentena IS NOT NULL)",
            name="ck_nota_fiscal_quarentena_motivada",
        ),
        UniqueConstraint("numero", "fornecedor_id", name="uq_nota_fiscal_numero_fornecedor"),
        Index("ix_nota_fiscal_nota_empenho_id", "nota_empenho_id"),
    )


class ItemNotaFiscal(Base):
    """How much of one NE line an NF delivers."""

    __tablename__ = "item_nota_fiscal"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    nota_fiscal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("nota_fiscal.id"))
    item_nota_empenho_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("item_nota_empenho.id")
    )
    quantity: Mapped[decimal.Decimal] = mapped_column("quantidade", Numeric(15, 3))

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_item_nota_fiscal_quantidade"),
        UniqueConstraint("nota_fiscal_id", "item_nota_empenho_id", name="uq_item_nota_fiscal_item"),
        Index("ix_item_nota_fiscal_item_nota_empenho_id", "item_nota_empenho_id"),
    )
