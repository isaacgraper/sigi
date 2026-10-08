"""Add `usuario.registro_funcional` and extend the anonymisation check.

SPEC-0001 v1.7 (AC-0001-45, AC-0001-14). The invitation now carries the
member's registration, which is personal data, so DB12 has to cover it: an
account is anonymised completely or not at all.

Revision ID: 0002_registro_funcional
Revises: 0001_baseline
Create Date: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_registro_funcional"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column and widen `ck_usuario_anonimizado` to include it."""
    # Nullable on purpose: accounts created before v1.7, the development seed
    # among them, have none, and there is no format or uniqueness to enforce
    # because neither is known (OQ-41).
    op.execute("ALTER TABLE usuario ADD COLUMN registro_funcional VARCHAR(32)")
    op.execute("ALTER TABLE usuario DROP CONSTRAINT ck_usuario_anonimizado")
    op.execute("""
        ALTER TABLE usuario ADD CONSTRAINT ck_usuario_anonimizado
          CHECK (anonimizado_em IS NULL
                 OR (nome IS NULL AND email IS NULL AND registro_funcional IS NULL
                     AND senha_hash IS NULL AND oidc_subject IS NULL))
    """)


def downgrade() -> None:
    """Drop the column and restore the v1.6 check."""
    op.execute("ALTER TABLE usuario DROP CONSTRAINT ck_usuario_anonimizado")
    op.execute("ALTER TABLE usuario DROP COLUMN registro_funcional")
    op.execute("""
        ALTER TABLE usuario ADD CONSTRAINT ck_usuario_anonimizado
          CHECK (anonimizado_em IS NULL
                 OR (nome IS NULL AND email IS NULL
                     AND senha_hash IS NULL AND oidc_subject IS NULL))
    """)
