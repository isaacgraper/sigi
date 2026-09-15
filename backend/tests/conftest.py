"""Test harness.

The database-backed tests need a real PostgreSQL: the substrate under test —
partitioning, triggers, generated columns, per-role privileges — has no
equivalent in SQLite, so asserting it there would prove nothing.

Two ways to get one, tried in this order:

1. `TEST_DATABASE_URL_ADMIN` names an already-running server. Use this when a
   local PostgreSQL is available and Docker is not, which is the case in some
   sandboxes.
2. Otherwise `testcontainers` starts `postgres:16`, which is what CI does.

Each session gets a throwaway database and provisions the application role,
mirroring `infra/postgres/init/01-roles.sh`. That mirroring matters: a test
running as the owner cannot prove AC-0001-27, whose entire point is what the
*application* role is unable to do.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql

from app.main import create_app

PAPEL_APP = "sigi_app_test"
SENHA_APP = "sigi_app_test"


@pytest.fixture
def client() -> TestClient:
    """A client over a freshly built application.

    Built per test rather than per session so that a test changing
    configuration cannot leak that change into the next one.
    """
    return TestClient(create_app())


@pytest.fixture(scope="session")
def servidor_postgres() -> Iterator[str]:
    """A libpq connection string for a superuser on a running PostgreSQL."""
    externo = os.environ.get("TEST_DATABASE_URL_ADMIN")
    if externo:
        yield externo
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        yield (
            f"host={pg.get_container_host_ip()} port={pg.get_exposed_port(5432)} "
            f"user={pg.username} password={pg.password} dbname={pg.dbname}"
        )


def _sem_dbname(dsn: str) -> str:
    return " ".join(p for p in dsn.split() if not p.startswith("dbname="))


@contextmanager
def _banco_novo(servidor_postgres: str) -> Iterator[tuple[str, str]]:
    """Create a throwaway database with the schema applied, and drop it after.

    Yields `(dsn_admin, dsn_app)` — the owner and the restricted role, which
    the privilege tests need to hold at the same time.
    """
    nome = f"sigi_test_{uuid.uuid4().hex[:12]}"
    base = _sem_dbname(servidor_postgres)

    # DDL takes no bind parameters in PostgreSQL, so identifiers and literals
    # are composed rather than interpolated.
    with psycopg.connect(servidor_postgres, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))

    dsn_admin = f"{base} dbname={nome}"
    hostinfo = " ".join(p for p in base.split() if p.startswith(("host=", "port=")))
    dsn_app = f"{hostinfo} user={PAPEL_APP} password={SENHA_APP} dbname={nome}"

    try:
        with psycopg.connect(dsn_admin, autocommit=True) as c:
            papel = sql.Identifier(PAPEL_APP)
            existe = c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (PAPEL_APP,)).fetchone()
            if existe is None:
                c.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOINHERIT").format(
                        papel, sql.Literal(SENHA_APP)
                    )
                )
            c.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(nome), papel)
            )
            c.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(papel))
            c.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(papel))
            c.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

        _aplicar_migracoes(dsn_admin)
        yield dsn_admin, dsn_app
    finally:
        with psycopg.connect(servidor_postgres, autocommit=True) as c:
            c.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nome))
            )


def _aplicar_migracoes(dsn_admin: str) -> None:
    """Run Alembic against the throwaway database.

    The application role name is passed through the environment because the
    migration reads it from settings — it is what the migration grants to, and
    what it refuses to run without.
    """
    anterior = os.environ.get("DB_APP_ROLE")
    os.environ["DB_APP_ROLE"] = PAPEL_APP
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        cfg.set_main_option("sqlalchemy.url", _para_sqlalchemy(dsn_admin))
        command.upgrade(cfg, "head")
    finally:
        if anterior is None:
            os.environ.pop("DB_APP_ROLE", None)
        else:
            os.environ["DB_APP_ROLE"] = anterior
        from app.core.config import get_settings

        get_settings.cache_clear()


def _para_sqlalchemy(dsn: str) -> str:
    partes = dict(p.split("=", 1) for p in dsn.split() if "=" in p)
    senha = f":{partes['password']}" if "password" in partes else ""
    return (
        f"postgresql+psycopg://{partes['user']}{senha}"
        f"@{partes['host']}:{partes.get('port', '5432')}/{partes['dbname']}"
    )


@pytest.fixture(scope="session")
def banco(servidor_postgres: str) -> Iterator[tuple[str, str]]:
    """One database for the whole session.

    Cheap, and enough for tests whose assertions are scoped to rows they
    created themselves.
    """
    with _banco_novo(servidor_postgres) as dsns:
        yield dsns


@pytest.fixture
def banco_isolado(servidor_postgres: str) -> Iterator[tuple[str, str]]:
    """A database of its own, for tests of a *global* invariant.

    "At least one active gestor exists" is a property of the whole table, so a
    test asserting it cannot share a database with tests that create gestores
    of their own — they would interfere in both directions. Paying for a fresh
    schema is cheaper than making every other test clean up after itself.
    """
    with _banco_novo(servidor_postgres) as dsns:
        yield dsns


@pytest.fixture
def conexao_admin(banco: tuple[str, str]) -> Iterator[psycopg.Connection]:
    """Owner connection. Can do DDL; the triggers still refuse it."""
    with psycopg.connect(banco[0], autocommit=True) as c:
        yield c


@pytest.fixture
def conexao_app(banco: tuple[str, str]) -> Iterator[psycopg.Connection]:
    """Application connection. What production actually runs as."""
    with psycopg.connect(banco[1], autocommit=True) as c:
        yield c
