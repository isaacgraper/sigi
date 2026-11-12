"""`GRUPO_MATERIAL`, `INSUMO`, `ITEM_ATA` and the servidor's grupos (SPEC-0003)."""

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
    SmallInteger,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GrupoMaterial(Base):
    """One node of grupo → subgrupo → classificação (AC-0003-09).

    Never deleted nor moved: either would silently change the scope of every
    servidor who owns it (AC-0003-13, RN07).
    """

    __tablename__ = "grupo_material"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str] = mapped_column("nome", String(120))
    level: Mapped[int] = mapped_column("nivel", SmallInteger)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        "grupo_pai_id", Uuid, ForeignKey("grupo_material.id")
    )
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        CheckConstraint("nivel BETWEEN 1 AND 3", name="ck_grupo_material_nivel"),
        CheckConstraint(
            "(nivel = 1) = (grupo_pai_id IS NULL)", name="ck_grupo_material_raiz_sem_pai"
        ),
        # Siblings differ by name, ignoring case; a root's parent is NULL, which
        # an ordinary UNIQUE would treat as distinct from every other NULL.
        Index(
            "uq_grupo_material_nome",
            text("lower(nome)"),
            text("COALESCE(grupo_pai_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            unique=True,
        ),
    )


class Insumo(Base):
    """A catalogue entry, identified by its `sku` (RN14).

    No `ata_id`: the link to ATAs is `ITEM_ATA` (SPEC-0003 §2). No `ativo` flag:
    the situação is derived from `descontinuado_em` and `substituido_por_id`,
    which a flag beside them would only repeat (AC-0003-10).
    """

    __tablename__ = "insumo"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    codigo_doms: Mapped[str | None] = mapped_column(String(20), unique=True)
    external_code: Mapped[str | None] = mapped_column("codigo_externo", String(40))
    description: Mapped[str] = mapped_column("descricao", String(300))
    unit: Mapped[str] = mapped_column("unidade", String(20))
    grupo_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("grupo_material.id"))
    reference_quantity: Mapped[decimal.Decimal | None] = mapped_column(
        "quantidade_referencia", Numeric(15, 3)
    )
    substitute_id: Mapped[uuid.UUID | None] = mapped_column(
        "substituido_por_id", Uuid, ForeignKey("insumo.id")
    )
    discontinued_on: Mapped[datetime.date | None] = mapped_column("descontinuado_em", Date)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        # The characters of the default pattern; the letter it also asks for is
        # the service's (AC-0003-35). A deployment that widens `sku_pattern`
        # widens this in a migration of its own.
        CheckConstraint("sku ~ '^[A-Z0-9]+$'", name="ck_insumo_sku"),
        CheckConstraint("codigo_doms ~ '^[0-9]+$'", name="ck_insumo_codigo_doms"),
        CheckConstraint(
            "substituido_por_id IS NULL OR descontinuado_em IS NOT NULL",
            name="ck_insumo_substituto_descontinuado",
        ),
        CheckConstraint("substituido_por_id <> id", name="ck_insumo_substituto_outro"),
        CheckConstraint(
            "quantidade_referencia IS NULL OR quantidade_referencia >= 0",
            name="ck_insumo_quantidade_referencia",
        ),
        Index("ix_insumo_grupo_id", "grupo_id"),
    )


class ItemAta(Base):
    """What an ATA contracted of one insumo (AC-0003-20).

    `valor_unitario` keeps five places and nothing else does (ADR-0016). The
    item's value is derived, never stored (AC-0003-21). A removed item keeps its
    row with `removido_em`, so its history can name it (AC-0003-24).
    """

    __tablename__ = "item_ata"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default="gen_random_uuid()"
    )
    ata_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ata.id"))
    insumo_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("insumo.id"))
    # NULL means the ATA's own fornecedor (OQ-11).
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("fornecedor.id"))
    item_number: Mapped[str | None] = mapped_column("numero_item", String(20))
    quantity: Mapped[decimal.Decimal] = mapped_column("quantidade", Numeric(15, 3))
    unit_price: Mapped[decimal.Decimal] = mapped_column("valor_unitario", Numeric(15, 5))
    removed_at: Mapped[datetime.datetime | None] = mapped_column(
        "removido_em", DateTime(timezone=True)
    )
    criado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_item_ata_quantidade"),
        CheckConstraint("valor_unitario > 0", name="ck_item_ata_valor_unitario"),
        Index(
            "uq_item_ata_insumo",
            "ata_id",
            "insumo_id",
            unique=True,
            postgresql_where=text("removido_em IS NULL"),
        ),
        Index("ix_item_ata_insumo_id", "insumo_id"),
    )


class UsuarioGrupoMaterial(Base):
    """A grupo a servidor owns: what it may see of the catalogue (RN07, AC-0003-30)."""

    __tablename__ = "usuario_grupo_material"

    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), primary_key=True)
    grupo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("grupo_material.id"), primary_key=True
    )
