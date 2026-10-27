"""`NOTA_EMPENHO` and `ITEM_NOTA_EMPENHO` (SPEC-0004)."""

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
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotaEmpenho(Base):
    """The header of an empenho: the document that moves through the five stages.

    Its value is not a column: it is the sum of its lines, for the same reason
    saldo is not one (ADR-0003, ADR-0007). Both números are issued outside SIGI
    and typed in as they arrive, so they stay empty until their stage (§9).
    """

    __tablename__ = "nota_empenho"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    numero: Mapped[str | None] = mapped_column(String(20), unique=True)
    numero_pre_empenho: Mapped[str | None] = mapped_column(String(20), unique=True)
    processo_sei: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), server_default="demanda")
    ata_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ata.id"))
    owner_id: Mapped[uuid.UUID] = mapped_column("responsavel_id", Uuid, ForeignKey("usuario.id"))
    issued_on: Mapped[datetime.date | None] = mapped_column("data_emissao", Date)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('demanda', 'validacao_saldo', 'pre_empenho', 'envio_fornecedor',"
            " 'ne_emitida', 'cancelada')",
            name="ck_nota_empenho_status",
        ),
        CheckConstraint(
            r"processo_sei ~ '^\d{5}\.\d{6}/\d{4}-\d{2}$'", name="ck_nota_empenho_processo_sei"
        ),
        CheckConstraint("numero ~ '^[A-Za-z0-9]{1,20}$'", name="ck_nota_empenho_numero"),
        CheckConstraint(
            "numero_pre_empenho ~ '^[A-Za-z0-9]{1,20}$'",
            name="ck_nota_empenho_numero_pre_empenho",
        ),
        CheckConstraint(
            "status NOT IN ('pre_empenho', 'envio_fornecedor', 'ne_emitida')"
            " OR numero_pre_empenho IS NOT NULL",
            name="ck_nota_empenho_pre_empenho_informado",
        ),
        CheckConstraint(
            "status <> 'ne_emitida' OR (numero IS NOT NULL AND data_emissao IS NOT NULL)",
            name="ck_nota_empenho_emitida_informada",
        ),
        Index("ix_nota_empenho_ata_status", "ata_id", "status"),
    )


class ItemNotaEmpenho(Base):
    """One insumo an NE commits: its quantity and the price fixed when it was opened.

    `valor_unitario` is copied from the ITEM_ATA, so a later reajuste never
    reaches an empenho already sent (I5). `valor` is that price times the
    quantity rounded once, and the database holds it to that (ADR-0016).
    """

    __tablename__ = "item_nota_empenho"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    nota_empenho_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("nota_empenho.id"))
    item_ata_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("item_ata.id"))
    quantity: Mapped[decimal.Decimal] = mapped_column("quantidade", Numeric(15, 3))
    unit_price: Mapped[decimal.Decimal] = mapped_column("valor_unitario", Numeric(15, 5))
    value: Mapped[decimal.Decimal] = mapped_column("valor", Numeric(15, 2))

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_item_nota_empenho_quantidade"),
        CheckConstraint("valor_unitario > 0", name="ck_item_nota_empenho_valor_unitario"),
        CheckConstraint(
            "valor = round(quantidade * valor_unitario, 2)", name="ck_item_nota_empenho_valor"
        ),
        UniqueConstraint("nota_empenho_id", "item_ata_id", name="uq_item_nota_empenho_item"),
        Index("ix_item_nota_empenho_item_ata_id", "item_ata_id"),
    )
