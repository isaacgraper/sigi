"""Alembic environment.

``compare_type=True`` in both modes on purpose: without it Alembic ignores a
column whose type changed, and a `NUMERIC(15,2)` quietly becoming something
else is the kind of divergence this project cannot afford to autogenerate past.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings

# Import the package, not just `base`: it is the package's __init__ that
# registers every model on `Base.metadata`. With an empty registry, autogenerate
# sees the existing tables as unknown and proposes dropping them.
from app.models import Base

config = context.config
# Alembic runs as the owner, not as the application role. The application role
# deliberately has no DDL, and the migration grants privileges *to* it — see
# ADR-0004 and `infra/postgres/init/01-roles.sh`.
#
# A caller that already set the URL wins: the test harness points each run at
# its own throwaway database, and having to juggle environment variables to do
# that is how a migration ends up untested.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", get_settings().database_url_admin)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(
    obj: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Hide the audit partitions from autogenerate.

    `historico_movimentacao` is partitioned by year and its partitions are
    created by hand-written DDL, so SQLAlchemy's metadata does not know them.
    Without this filter the next `--autogenerate` sees them as unknown tables
    and proposes dropping every one — which would delete the audit trail while
    looking like a routine migration.
    """
    return not (
        type_ == "table" and name is not None and name.startswith("historico_movimentacao_")
    )


def run_migrations_offline() -> None:
    """Emit SQL without connecting, for review before it is applied."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
