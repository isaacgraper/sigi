"""Notas fiscais: nota_fiscal and item_nota_fiscal, with DB1, DB6 and DB14.

SPEC-0005 v1.0. An NF binds to an NE and never to an ATA (RN02), so neither
table carries `ata_id`. Its lines name lines of that NE, which is what lets
`quantidade_faltante` be counted per item. The número is unique per fornecedor,
the way the document itself is.

The three triggers are the backstop of rules the service answers first with
their own codes: an NF binds only to an issued NE (DB1), the NFs of an NE,
`devolvida` excluded, never exceed its value (DB6, RN12), and a line names a line
of the NF's own NE (DB14).

Revision ID: 0007_notas_fiscais
Revises: 0006_notas_empenho
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings

revision: str = "0007_notas_fiscais"
down_revision: str | None = "0006_notas_empenho"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the NF header and lines and the three triggers."""
    op.execute("""
        CREATE TABLE nota_fiscal (
          id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          numero                  VARCHAR(20)   NOT NULL,
          data_emissao            DATE          NOT NULL,
          valor                   NUMERIC(15,2) NOT NULL,
          nota_empenho_id         UUID          NOT NULL REFERENCES nota_empenho (id),
          fornecedor_id           UUID          NOT NULL REFERENCES fornecedor (id),
          responsavel_id          UUID          NOT NULL REFERENCES usuario (id),
          status                  VARCHAR(20)   NOT NULL DEFAULT 'aguardando',
          justificativa_devolucao TEXT,
          quarentena              BOOLEAN       NOT NULL DEFAULT false,
          motivo_quarentena       TEXT,
          criado_em               TIMESTAMPTZ   NOT NULL DEFAULT now(),
          atualizado_em           TIMESTAMPTZ   NOT NULL DEFAULT now(),
          CONSTRAINT ck_nota_fiscal_status CHECK (status IN
            ('aguardando', 'em_conferencia', 'aprovada', 'devolvida')),
          CONSTRAINT ck_nota_fiscal_numero CHECK (numero ~ '^[A-Za-z0-9]{1,20}$'),
          CONSTRAINT ck_nota_fiscal_valor CHECK (valor > 0),
          CONSTRAINT ck_nota_fiscal_devolucao_justificada CHECK (
            status <> 'devolvida' OR justificativa_devolucao IS NOT NULL),
          CONSTRAINT ck_nota_fiscal_quarentena_motivada CHECK (
            quarentena = (motivo_quarentena IS NOT NULL)),
          CONSTRAINT uq_nota_fiscal_numero_fornecedor UNIQUE (numero, fornecedor_id)
        )
    """)
    op.execute("CREATE INDEX ix_nota_fiscal_nota_empenho_id ON nota_fiscal (nota_empenho_id)")
    op.execute("""
        CREATE TABLE item_nota_fiscal (
          id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          nota_fiscal_id       UUID          NOT NULL REFERENCES nota_fiscal (id),
          item_nota_empenho_id UUID          NOT NULL REFERENCES item_nota_empenho (id),
          quantidade           NUMERIC(15,3) NOT NULL,
          CONSTRAINT ck_item_nota_fiscal_quantidade CHECK (quantidade > 0),
          CONSTRAINT uq_item_nota_fiscal_item UNIQUE (nota_fiscal_id, item_nota_empenho_id)
        )
    """)
    op.execute(
        "CREATE INDEX ix_item_nota_fiscal_item_nota_empenho_id"
        " ON item_nota_fiscal (item_nota_empenho_id)"
    )

    # DB1: an NF against an NE not yet issued bills a commitment that does not exist.
    op.execute("""
        CREATE FUNCTION nota_fiscal_de_ne_emitida() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF (SELECT status FROM nota_empenho WHERE id = NEW.nota_empenho_id)
             IS DISTINCT FROM 'ne_emitida' THEN
            RAISE EXCEPTION 'NF de NE nao emitida' USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tg_nota_fiscal_de_ne_emitida
          BEFORE INSERT OR UPDATE OF nota_empenho_id ON nota_fiscal
          FOR EACH ROW EXECUTE FUNCTION nota_fiscal_de_ne_emitida()
    """)
    # DB6: billing past the empenho is paying for what was never committed (RN12).
    op.execute("""
        CREATE FUNCTION nota_fiscal_dentro_do_empenho() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.status <> 'devolvida' AND (
               SELECT coalesce(sum(valor), 0) FROM nota_fiscal
               WHERE nota_empenho_id = NEW.nota_empenho_id AND status <> 'devolvida')
             > (SELECT coalesce(sum(valor), 0) FROM item_nota_empenho
                WHERE nota_empenho_id = NEW.nota_empenho_id) THEN
            RAISE EXCEPTION 'NF acima do empenho' USING ERRCODE = 'check_violation';
          END IF;
          RETURN NULL;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tg_nota_fiscal_dentro_do_empenho
          AFTER INSERT OR UPDATE OF valor, status, nota_empenho_id ON nota_fiscal
          FOR EACH ROW EXECUTE FUNCTION nota_fiscal_dentro_do_empenho()
    """)
    # DB14: a line of another NE would count a delivery against the wrong empenho.
    op.execute("""
        CREATE FUNCTION item_nota_fiscal_do_mesmo_empenho() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF (SELECT nota_empenho_id FROM item_nota_empenho WHERE id = NEW.item_nota_empenho_id)
             IS DISTINCT FROM (SELECT nota_empenho_id FROM nota_fiscal
                               WHERE id = NEW.nota_fiscal_id) THEN
            RAISE EXCEPTION 'item_nota_fiscal de outra NE' USING ERRCODE = 'check_violation';
          END IF;
          RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER tg_item_nota_fiscal_do_mesmo_empenho
          BEFORE INSERT OR UPDATE ON item_nota_fiscal
          FOR EACH ROW EXECUTE FUNCTION item_nota_fiscal_do_mesmo_empenho()
    """)

    papel = get_settings().db_app_role
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON nota_fiscal TO {papel}")
    op.execute(f"GRANT SELECT, INSERT, DELETE ON item_nota_fiscal TO {papel}")


def downgrade() -> None:
    """Drop the triggers and both tables, and with them every NF and its lines.

    Their audit rows stay in `historico_movimentacao`.
    """
    op.execute("DROP TABLE IF EXISTS item_nota_fiscal")
    op.execute("DROP FUNCTION IF EXISTS item_nota_fiscal_do_mesmo_empenho()")
    op.execute("DROP TABLE IF EXISTS nota_fiscal")
    op.execute("DROP FUNCTION IF EXISTS nota_fiscal_dentro_do_empenho()")
    op.execute("DROP FUNCTION IF EXISTS nota_fiscal_de_ne_emitida()")
