"""ATAs: fornecedor, ata, ata_aditivo and ata_reajuste.

SPEC-0002 v1.0. The first business tables. The application role gets rows and
no `DELETE` on any of them: an ATA is cancelled, never deleted (AC-0002-17), and
withholding the privilege is what makes that a fact about the schema rather than
a promise about the code.

Revision ID: 0003_atas
Revises: 0002_registro_funcional
Create Date: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings

revision: str = "0003_atas"
down_revision: str | None = "0002_registro_funcional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("fornecedor", "ata", "ata_aditivo", "ata_reajuste")


def upgrade() -> None:
    """Create the four tables and grant rows, never structure."""
    op.execute("""
        CREATE TABLE fornecedor (
          id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          cnpj         VARCHAR(14)  NOT NULL UNIQUE,
          razao_social VARCHAR(200) NOT NULL,
          email        VARCHAR(320),
          ativo        BOOLEAN      NOT NULL DEFAULT true,
          criado_em    TIMESTAMPTZ  NOT NULL DEFAULT now(),
          CONSTRAINT ck_fornecedor_cnpj CHECK (cnpj ~ '^[0-9]{14}$')
        )
    """)
    op.execute("""
        CREATE TABLE ata (
          id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          numero                    VARCHAR(60)   NOT NULL UNIQUE,
          objeto                    TEXT          NOT NULL,
          orgao                     VARCHAR(200)  NOT NULL,
          fornecedor_id             UUID          NOT NULL REFERENCES fornecedor (id),
          data_emissao              DATE,
          vigencia_inicio           DATE          NOT NULL,
          vigencia_fim              DATE          NOT NULL,
          valor_total               NUMERIC(15,2) NOT NULL,
          data_orcamento_planilhado DATE          NOT NULL,
          status                    VARCHAR(20)   NOT NULL DEFAULT 'rascunho',
          responsavel_id            UUID          NOT NULL REFERENCES usuario (id),
          criado_em                 TIMESTAMPTZ   NOT NULL DEFAULT now(),
          atualizado_em             TIMESTAMPTZ   NOT NULL DEFAULT now(),
          CONSTRAINT ck_ata_status
            CHECK (status IN ('rascunho', 'vigente', 'suspensa', 'encerrada', 'cancelada')),
          CONSTRAINT ck_ata_vigencia CHECK (vigencia_fim > vigencia_inicio),
          CONSTRAINT ck_ata_valor_positivo CHECK (valor_total > 0)
        )
    """)
    op.execute("CREATE INDEX ix_ata_status ON ata (status)")
    op.execute("CREATE INDEX ix_ata_vigencia_fim ON ata (vigencia_fim)")
    op.execute("""
        CREATE TABLE ata_aditivo (
          id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          ata_id            UUID          NOT NULL REFERENCES ata (id),
          tipo              VARCHAR(10)   NOT NULL,
          valor_acrescimo   NUMERIC(15,2),
          nova_vigencia_fim DATE,
          justificativa     TEXT          NOT NULL,
          criado_por        UUID          NOT NULL REFERENCES usuario (id),
          criado_em         TIMESTAMPTZ   NOT NULL DEFAULT now(),
          CONSTRAINT ck_ata_aditivo_tipo CHECK (tipo IN ('valor', 'prazo')),
          CONSTRAINT ck_ata_aditivo_campos
            CHECK ((tipo = 'valor' AND valor_acrescimo IS NOT NULL AND valor_acrescimo > 0
               AND nova_vigencia_fim IS NULL)
                OR (tipo = 'prazo' AND valor_acrescimo IS NULL AND nova_vigencia_fim IS NOT NULL))
        )
    """)
    op.execute("CREATE INDEX ix_ata_aditivo_ata_id ON ata_aditivo (ata_id)")
    op.execute("""
        CREATE TABLE ata_reajuste (
          id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          ata_id       UUID        NOT NULL REFERENCES ata (id),
          processo_sei VARCHAR(30) NOT NULL,
          solicitado_em DATE       NOT NULL,
          criado_por   UUID        NOT NULL REFERENCES usuario (id),
          criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_ata_reajuste_ata_id ON ata_reajuste (ata_id)")

    papel = get_settings().db_app_role
    for tabela in TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {tabela} TO {papel}")


def downgrade() -> None:
    """Drop the four tables, children first."""
    for tabela in reversed(TABLES):
        op.execute(f"DROP TABLE IF EXISTS {tabela}")
