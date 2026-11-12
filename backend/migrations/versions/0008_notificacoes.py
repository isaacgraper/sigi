"""Notificações: notificacao, notificacao_leitura and preferencia_email.

SPEC-0008 v1.1. A notice is raised once per ATA, reason and key, which the
unique constraint guarantees even if two runs of the daily check overlap. Who
read it is a row per member, so one member's reading never hides it from
another; every perfil is told the same. Each member's e-mail summary follows
their own choice, kept with the instant of their last summary.

Revision ID: 0008_notificacoes
Revises: 0007_notas_fiscais
Create Date: 2026-11-12
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import get_settings

revision: str = "0008_notificacoes"
down_revision: str | None = "0007_notas_fiscais"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the notices and who read them."""
    op.execute("""
        CREATE TABLE notificacao (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          ata_id      UUID        NOT NULL REFERENCES ata (id),
          motivo      VARCHAR(20) NOT NULL,
          chave       VARCHAR(40) NOT NULL,
          dados       JSONB       NOT NULL DEFAULT '{}',
          criada_em   TIMESTAMPTZ NOT NULL,
          CONSTRAINT uq_notificacao_ata_motivo_chave UNIQUE (ata_id, motivo, chave),
          CONSTRAINT ck_notificacao_motivo CHECK (
            motivo IN ('vai_vencer', 'venceu', 'saldo_80', 'saldo_esgotado', 'reajuste')
          )
        )
    """)
    op.execute("CREATE INDEX ix_notificacao_criada_em ON notificacao (criada_em)")
    op.execute("""
        CREATE TABLE notificacao_leitura (
          notificacao_id  UUID        NOT NULL REFERENCES notificacao (id),
          usuario_id      UUID        NOT NULL REFERENCES usuario (id),
          lida_em         TIMESTAMPTZ NOT NULL,
          PRIMARY KEY (notificacao_id, usuario_id)
        )
    """)
    op.execute("""
        CREATE TABLE preferencia_email (
          usuario_id       UUID PRIMARY KEY REFERENCES usuario (id),
          frequencia       VARCHAR(10) NOT NULL,
          dia_semana       SMALLINT    NOT NULL,
          ultimo_envio_em  TIMESTAMPTZ,
          atualizada_em    TIMESTAMPTZ NOT NULL,
          CONSTRAINT ck_preferencia_email_frequencia
            CHECK (frequencia IN ('diario', 'semanal', 'nenhum')),
          CONSTRAINT ck_preferencia_email_dia CHECK (dia_semana BETWEEN 1 AND 7)
        )
    """)
    papel = get_settings().db_app_role
    op.execute(f"GRANT SELECT, INSERT ON notificacao TO {papel}")
    op.execute(f"GRANT SELECT, INSERT ON notificacao_leitura TO {papel}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON preferencia_email TO {papel}")


def downgrade() -> None:
    """Drop the three tables, and with them every notice, who read it and every choice."""
    op.execute("DROP TABLE preferencia_email")
    op.execute("DROP TABLE notificacao_leitura")
    op.execute("DROP TABLE notificacao")
