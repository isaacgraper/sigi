"""Notas de empenho: nota_empenho and item_nota_empenho, with DB2, DB4 and DB7.

SPEC-0004 v1.1. The NE is a header and its items are the lines (ADR-0007). The
número of the nota de pré-empenho and of the NE are typed in as the financial
system issues them, at `pre_empenho` and at `ne_emitida` (AC-0004-28, -29).
`item_nota_empenho.valor` is the unit price times the quantity rounded once to
the centavo, and a `CHECK` holds it to that (ADR-0016). There is no saldo
column: saldo is summed from these lines on every read (ADR-0003).

The three triggers are the backstop of rules the service answers first with
their own codes: an item belongs to its NE's ATA (DB2), an ATA is not closed
with an NE in progress (DB4), an NE does not leave `demanda` empty (DB7).

Revision ID: 0006_notas_empenho
Revises: 0005_insumos
Create Date: 2026-10-27
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings

revision: str = "0006_notas_empenho"
down_revision: str | None = "0005_insumos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the NE header and lines and the three triggers."""
    op.execute(r"""
        CREATE TABLE nota_empenho (
          id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          numero             VARCHAR(20) UNIQUE,
          numero_pre_empenho VARCHAR(20) UNIQUE,
          processo_sei       VARCHAR(30) NOT NULL,
          status             VARCHAR(20) NOT NULL DEFAULT 'demanda',
          ata_id             UUID        NOT NULL REFERENCES ata (id),
          responsavel_id     UUID        NOT NULL REFERENCES usuario (id),
          data_emissao       DATE,
          criado_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
          atualizado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT ck_nota_empenho_status CHECK (status IN
            ('demanda', 'validacao_saldo', 'pre_empenho', 'envio_fornecedor',
             'ne_emitida', 'cancelada')),
          CONSTRAINT ck_nota_empenho_processo_sei
            CHECK (processo_sei ~ '^\d{5}\.\d{6}/\d{4}-\d{2}$'),
          CONSTRAINT ck_nota_empenho_numero CHECK (numero ~ '^[A-Za-z0-9]{1,20}$'),
          CONSTRAINT ck_nota_empenho_numero_pre_empenho
            CHECK (numero_pre_empenho ~ '^[A-Za-z0-9]{1,20}$'),
          CONSTRAINT ck_nota_empenho_pre_empenho_informado CHECK (
            status NOT IN ('pre_empenho', 'envio_fornecedor', 'ne_emitida')
            OR numero_pre_empenho IS NOT NULL),
          CONSTRAINT ck_nota_empenho_emitida_informada CHECK (
            status <> 'ne_emitida' OR (numero IS NOT NULL AND data_emissao IS NOT NULL))
        )
    """)
    op.execute("CREATE INDEX ix_nota_empenho_ata_status ON nota_empenho (ata_id, status)")
    op.execute("""
        CREATE TABLE item_nota_empenho (
          id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          nota_empenho_id UUID          NOT NULL REFERENCES nota_empenho (id),
          item_ata_id     UUID          NOT NULL REFERENCES item_ata (id),
          quantidade      NUMERIC(15,3) NOT NULL,
          valor_unitario  NUMERIC(15,5) NOT NULL,
          valor           NUMERIC(15,2) NOT NULL,
          CONSTRAINT ck_item_nota_empenho_quantidade CHECK (quantidade > 0),
          CONSTRAINT ck_item_nota_empenho_valor_unitario CHECK (valor_unitario > 0),
          CONSTRAINT ck_item_nota_empenho_valor
            CHECK (valor = round(quantidade * valor_unitario, 2)),
          CONSTRAINT uq_item_nota_empenho_item UNIQUE (nota_empenho_id, item_ata_id)
        )
    """)
    op.execute("CREATE INDEX ix_item_nota_empenho_item_ata_id ON item_nota_empenho (item_ata_id)")

    # DB2: an NE spanning two ATAs would make its saldo deduction unattributable.
    op.execute("""
        CREATE FUNCTION item_nota_empenho_da_mesma_ata() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF (SELECT ata_id FROM item_ata WHERE id = NEW.item_ata_id)
             IS DISTINCT FROM (SELECT ata_id FROM nota_empenho WHERE id = NEW.nota_empenho_id) THEN
            RAISE EXCEPTION 'item_nota_empenho de outra ATA' USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tg_item_nota_empenho_da_mesma_ata
          BEFORE INSERT OR UPDATE ON item_nota_empenho
          FOR EACH ROW EXECUTE FUNCTION item_nota_empenho_da_mesma_ata()
    """)
    # DB4: closing an ATA with an NE in progress would orphan the commitment.
    op.execute("""
        CREATE FUNCTION ata_sem_ne_pendente() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.status = 'encerrada' AND OLD.status <> 'encerrada' AND EXISTS (
               SELECT 1 FROM nota_empenho
               WHERE ata_id = NEW.id AND status NOT IN ('ne_emitida', 'cancelada')) THEN
            RAISE EXCEPTION 'ATA com NE pendente' USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tg_ata_sem_ne_pendente
          BEFORE UPDATE OF status ON ata
          FOR EACH ROW EXECUTE FUNCTION ata_sem_ne_pendente()
    """)
    # DB7: an NE committing nothing is not an administrative act (RN09).
    op.execute("""
        CREATE FUNCTION nota_empenho_com_itens() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status = 'demanda' AND NEW.status NOT IN ('demanda', 'cancelada')
             AND NOT EXISTS (SELECT 1 FROM item_nota_empenho WHERE nota_empenho_id = NEW.id) THEN
            RAISE EXCEPTION 'NE sem itens' USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tg_nota_empenho_com_itens
          BEFORE UPDATE OF status ON nota_empenho
          FOR EACH ROW EXECUTE FUNCTION nota_empenho_com_itens()
    """)

    papel = get_settings().db_app_role
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON nota_empenho TO {papel}")
    op.execute(f"GRANT SELECT, INSERT, DELETE ON item_nota_empenho TO {papel}")


def downgrade() -> None:
    """Drop the triggers and both tables, and with them every NE and its items.

    Their audit rows stay in `historico_movimentacao`.
    """
    op.execute("DROP TRIGGER IF EXISTS tg_ata_sem_ne_pendente ON ata")
    op.execute("DROP FUNCTION IF EXISTS ata_sem_ne_pendente()")
    op.execute("DROP TABLE IF EXISTS item_nota_empenho")
    op.execute("DROP FUNCTION IF EXISTS item_nota_empenho_da_mesma_ata()")
    op.execute("DROP TABLE IF EXISTS nota_empenho")
    op.execute("DROP FUNCTION IF EXISTS nota_empenho_com_itens()")
