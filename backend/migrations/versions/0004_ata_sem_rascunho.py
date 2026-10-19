"""ATAs without `rascunho`, and the alphanumeric CNPJ.

SPEC-0002 v1.2. An ATA is registered after the gestor reviews it, so it is
vigente from the start and `rascunho` leaves the vocabulary. Any `rascunho` ATA
becomes `vigente`. No deployment holds data yet, so those rows get no audit
entry: they are development and test data, and writing a history row for a
migration nobody performed would record an act that did not happen.

The CNPJ may now carry uppercase letters in its first twelve characters (IN RFB
nº 2.229/2024); the check digits stay numeric.

Revision ID: 0004_ata_sem_rascunho
Revises: 0003_atas
Create Date: 2026-10-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_ata_sem_rascunho"
down_revision: str | None = "0003_atas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move drafts to vigente, drop `rascunho`, widen the CNPJ."""
    op.execute("UPDATE ata SET status = 'vigente' WHERE status = 'rascunho'")
    op.execute("ALTER TABLE ata DROP CONSTRAINT ck_ata_status")
    op.execute("""
        ALTER TABLE ata ADD CONSTRAINT ck_ata_status
          CHECK (status IN ('vigente', 'suspensa', 'encerrada', 'cancelada'))
    """)
    op.execute("ALTER TABLE ata ALTER COLUMN status SET DEFAULT 'vigente'")
    op.execute("ALTER TABLE fornecedor DROP CONSTRAINT ck_fornecedor_cnpj")
    op.execute("""
        ALTER TABLE fornecedor ADD CONSTRAINT ck_fornecedor_cnpj
          CHECK (cnpj ~ '^[0-9A-Z]{12}[0-9]{2}$')
    """)


def downgrade() -> None:
    """Restore the 0003 constraints; fails while an alphanumeric CNPJ exists."""
    op.execute("ALTER TABLE fornecedor DROP CONSTRAINT ck_fornecedor_cnpj")
    op.execute("""
        ALTER TABLE fornecedor ADD CONSTRAINT ck_fornecedor_cnpj
          CHECK (cnpj ~ '^[0-9]{14}$')
    """)
    op.execute("ALTER TABLE ata ALTER COLUMN status SET DEFAULT 'rascunho'")
    op.execute("ALTER TABLE ata DROP CONSTRAINT ck_ata_status")
    op.execute("""
        ALTER TABLE ata ADD CONSTRAINT ck_ata_status
          CHECK (status IN ('rascunho', 'vigente', 'suspensa', 'encerrada', 'cancelada'))
    """)
