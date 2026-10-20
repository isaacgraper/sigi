"""Insumos: grupo_material, insumo, item_ata, usuario_grupo_material, aditivo de quantidade.

SPEC-0003 v1.1. The application role gets rows and no `DELETE` on the
catalogue and the items: an insumo is discontinued and an item is removed by a
date, never deleted (AC-0003-10, -24). The one exception is
`usuario_grupo_material`, a set a gestor replaces whole (AC-0003-30), whose prior
contents the audit row keeps.

`item_ata.valor_unitario` is `NUMERIC(15,5)` (ADR-0016).

Revision ID: 0005_insumos
Revises: 0004_ata_sem_rascunho
Create Date: 2026-10-20
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings

revision: str = "0005_insumos"
down_revision: str | None = "0004_ata_sem_rascunho"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("grupo_material", "insumo", "item_ata")


def upgrade() -> None:
    """Create the catalogue, the items and the scope, and admit the aditivo de quantidade."""
    op.execute("""
        CREATE TABLE grupo_material (
          id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          nome         VARCHAR(120) NOT NULL,
          nivel        SMALLINT     NOT NULL,
          grupo_pai_id UUID REFERENCES grupo_material (id),
          criado_em    TIMESTAMPTZ  NOT NULL DEFAULT now(),
          CONSTRAINT ck_grupo_material_nivel CHECK (nivel BETWEEN 1 AND 3),
          CONSTRAINT ck_grupo_material_raiz_sem_pai CHECK ((nivel = 1) = (grupo_pai_id IS NULL))
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_grupo_material_nome ON grupo_material
          (lower(nome), COALESCE(grupo_pai_id, '00000000-0000-0000-0000-000000000000'::uuid))
    """)
    op.execute("""
        CREATE TABLE insumo (
          id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          sku                   VARCHAR(40)   NOT NULL UNIQUE,
          codigo_doms           VARCHAR(20)   UNIQUE,
          codigo_externo        VARCHAR(40),
          descricao             VARCHAR(300)  NOT NULL,
          unidade               VARCHAR(20)   NOT NULL,
          grupo_id              UUID          NOT NULL REFERENCES grupo_material (id),
          quantidade_referencia NUMERIC(15,3),
          substituido_por_id    UUID          REFERENCES insumo (id),
          descontinuado_em      DATE,
          criado_em             TIMESTAMPTZ   NOT NULL DEFAULT now(),
          atualizado_em         TIMESTAMPTZ   NOT NULL DEFAULT now(),
          CONSTRAINT ck_insumo_sku CHECK (sku ~ '^[A-Z0-9]+$'),
          CONSTRAINT ck_insumo_codigo_doms CHECK (codigo_doms ~ '^[0-9]+$'),
          CONSTRAINT ck_insumo_substituto_descontinuado
            CHECK (substituido_por_id IS NULL OR descontinuado_em IS NOT NULL),
          CONSTRAINT ck_insumo_substituto_outro CHECK (substituido_por_id <> id),
          CONSTRAINT ck_insumo_quantidade_referencia
            CHECK (quantidade_referencia IS NULL OR quantidade_referencia >= 0)
        )
    """)
    op.execute("CREATE INDEX ix_insumo_grupo_id ON insumo (grupo_id)")
    op.execute("""
        CREATE TABLE item_ata (
          id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          ata_id         UUID          NOT NULL REFERENCES ata (id),
          insumo_id      UUID          NOT NULL REFERENCES insumo (id),
          fornecedor_id  UUID          REFERENCES fornecedor (id),
          numero_item    VARCHAR(20),
          quantidade     NUMERIC(15,3) NOT NULL,
          valor_unitario NUMERIC(15,5) NOT NULL,
          removido_em    TIMESTAMPTZ,
          criado_em      TIMESTAMPTZ   NOT NULL DEFAULT now(),
          atualizado_em  TIMESTAMPTZ   NOT NULL DEFAULT now(),
          CONSTRAINT ck_item_ata_quantidade CHECK (quantidade > 0),
          CONSTRAINT ck_item_ata_valor_unitario CHECK (valor_unitario > 0)
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_item_ata_insumo ON item_ata (ata_id, insumo_id)
          WHERE removido_em IS NULL
    """)
    op.execute("CREATE INDEX ix_item_ata_insumo_id ON item_ata (insumo_id)")
    op.execute("""
        CREATE TABLE usuario_grupo_material (
          usuario_id UUID NOT NULL REFERENCES usuario (id),
          grupo_id   UUID NOT NULL REFERENCES grupo_material (id),
          PRIMARY KEY (usuario_id, grupo_id)
        )
    """)

    op.execute("ALTER TABLE ata_aditivo ADD COLUMN item_ata_id UUID REFERENCES item_ata (id)")
    op.execute("ALTER TABLE ata_aditivo ADD COLUMN quantidade_acrescimo NUMERIC(15,3)")
    op.execute("CREATE INDEX ix_ata_aditivo_item_ata_id ON ata_aditivo (item_ata_id)")
    op.execute("ALTER TABLE ata_aditivo DROP CONSTRAINT ck_ata_aditivo_tipo")
    op.execute("""
        ALTER TABLE ata_aditivo ADD CONSTRAINT ck_ata_aditivo_tipo
          CHECK (tipo IN ('valor', 'prazo', 'quantidade'))
    """)
    op.execute("ALTER TABLE ata_aditivo DROP CONSTRAINT ck_ata_aditivo_campos")
    op.execute("""
        ALTER TABLE ata_aditivo ADD CONSTRAINT ck_ata_aditivo_campos
          CHECK ((tipo = 'valor' AND valor_acrescimo IS NOT NULL AND valor_acrescimo > 0
                  AND nova_vigencia_fim IS NULL AND item_ata_id IS NULL
                  AND quantidade_acrescimo IS NULL)
              OR (tipo = 'prazo' AND valor_acrescimo IS NULL AND nova_vigencia_fim IS NOT NULL
                  AND item_ata_id IS NULL AND quantidade_acrescimo IS NULL)
              OR (tipo = 'quantidade' AND valor_acrescimo IS NULL AND nova_vigencia_fim IS NULL
                  AND item_ata_id IS NOT NULL AND quantidade_acrescimo IS NOT NULL
                  AND quantidade_acrescimo > 0))
    """)

    papel = get_settings().db_app_role
    for tabela in TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {tabela} TO {papel}")
    op.execute(f"GRANT SELECT, INSERT, DELETE ON usuario_grupo_material TO {papel}")


def downgrade() -> None:
    """Restore the 0004 aditivo checks and drop the new tables; fails while a quantity aditivo exists."""
    op.execute("ALTER TABLE ata_aditivo DROP CONSTRAINT ck_ata_aditivo_campos")
    op.execute("""
        ALTER TABLE ata_aditivo ADD CONSTRAINT ck_ata_aditivo_campos
          CHECK ((tipo = 'valor' AND valor_acrescimo IS NOT NULL AND valor_acrescimo > 0
                  AND nova_vigencia_fim IS NULL)
              OR (tipo = 'prazo' AND valor_acrescimo IS NULL AND nova_vigencia_fim IS NOT NULL))
    """)
    op.execute("ALTER TABLE ata_aditivo DROP CONSTRAINT ck_ata_aditivo_tipo")
    op.execute("""
        ALTER TABLE ata_aditivo ADD CONSTRAINT ck_ata_aditivo_tipo CHECK (tipo IN ('valor', 'prazo'))
    """)
    op.execute("DROP INDEX IF EXISTS ix_ata_aditivo_item_ata_id")
    op.execute("ALTER TABLE ata_aditivo DROP COLUMN quantidade_acrescimo")
    op.execute("ALTER TABLE ata_aditivo DROP COLUMN item_ata_id")
    op.execute("DROP TABLE IF EXISTS usuario_grupo_material")
    for tabela in reversed(TABLES):
        op.execute(f"DROP TABLE IF EXISTS {tabela}")
