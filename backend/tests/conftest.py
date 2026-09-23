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
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.passwords import hash_password
from app.main import create_app
from app.models.user import User

APP_ROLE = "sigi_app_test"
APP_ROLE_PASSWORD = "sigi_app_test"


@pytest.fixture
def client() -> TestClient:
    """A client over a freshly built application.

    Built per test rather than per session so that a test changing
    configuration cannot leak that change into the next one.
    """
    return TestClient(create_app())


@pytest.fixture(scope="session")
def postgres_server() -> Iterator[str]:
    """A libpq connection string for a superuser on a running PostgreSQL."""
    foreign = os.environ.get("TEST_DATABASE_URL_ADMIN")
    if foreign:
        yield foreign
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        yield (
            f"host={pg.get_container_host_ip()} port={pg.get_exposed_port(5432)} "
            f"user={pg.username} password={pg.password} dbname={pg.dbname}"
        )


def _without_dbname(dsn: str) -> str:
    return " ".join(p for p in dsn.split() if not p.startswith("dbname="))


@contextmanager
def _new_database(postgres_server: str) -> Iterator[tuple[str, str]]:
    """Create a throwaway database with the schema applied, and drop it after.

    Yields `(dsn_admin, dsn_app)` — the owner and the restricted role, which
    the privilege tests need to hold at the same time.
    """
    dbname = f"sigi_test_{uuid.uuid4().hex[:12]}"
    base = _without_dbname(postgres_server)

    # DDL takes no bind parameters in PostgreSQL, so identifiers and literals
    # are composed rather than interpolated.
    with psycopg.connect(postgres_server, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))

    dsn_admin = f"{base} dbname={dbname}"
    hostinfo = " ".join(p for p in base.split() if p.startswith(("host=", "port=")))
    dsn_app = f"{hostinfo} user={APP_ROLE} password={APP_ROLE_PASSWORD} dbname={dbname}"

    try:
        with psycopg.connect(dsn_admin, autocommit=True) as c:
            db_role = sql.Identifier(APP_ROLE)
            exists = c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_ROLE,)).fetchone()
            if exists is None:
                c.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOINHERIT").format(
                        db_role, sql.Literal(APP_ROLE_PASSWORD)
                    )
                )
            c.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(dbname), db_role
                )
            )
            c.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(db_role))
            c.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(db_role))
            c.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

        _apply_migrations(dsn_admin)
        yield dsn_admin, dsn_app
    finally:
        with psycopg.connect(postgres_server, autocommit=True) as c:
            c.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(dbname))
            )


def _apply_migrations(dsn_admin: str) -> None:
    """Run Alembic against the throwaway database.

    The application role name is passed through the environment because the
    migration reads it from settings — it is what the migration grants to, and
    what it refuses to run without.
    """
    previous = os.environ.get("DB_APP_ROLE")
    os.environ["DB_APP_ROLE"] = APP_ROLE
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        cfg.set_main_option("sqlalchemy.url", _to_sqlalchemy(dsn_admin))
        command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("DB_APP_ROLE", None)
        else:
            os.environ["DB_APP_ROLE"] = previous
        from app.core.config import get_settings

        get_settings.cache_clear()


def _to_sqlalchemy(dsn: str) -> str:
    parts = dict(p.split("=", 1) for p in dsn.split() if "=" in p)
    password = f":{parts['password']}" if "password" in parts else ""
    return (
        f"postgresql+psycopg://{parts['user']}{password}"
        f"@{parts['host']}:{parts.get('port', '5432')}/{parts['dbname']}"
    )


@pytest.fixture(scope="session")
def database(postgres_server: str) -> Iterator[tuple[str, str]]:
    """One database for the whole session.

    Cheap, and enough for tests whose assertions are scoped to rows they
    created themselves.
    """
    with _new_database(postgres_server) as dsns:
        yield dsns


@pytest.fixture
def isolated_database(postgres_server: str) -> Iterator[tuple[str, str]]:
    """A database of its own, for tests of a *global* invariant.

    "At least one active gestor exists" is a property of the whole table, so a
    test asserting it cannot share a database with tests that create gestores
    of their own — they would interfere in both directions. Paying for a fresh
    schema is cheaper than making every other test clean up after itself.
    """
    with _new_database(postgres_server) as dsns:
        yield dsns


@pytest.fixture
def admin_connection(database: tuple[str, str]) -> Iterator[psycopg.Connection]:
    """Owner connection. Can do DDL; the triggers still refuse it."""
    with psycopg.connect(database[0], autocommit=True) as c:
        yield c


@pytest.fixture
def app_connection(database: tuple[str, str]) -> Iterator[psycopg.Connection]:
    """Application connection. What production actually runs as."""
    with psycopg.connect(database[1], autocommit=True) as c:
        yield c


@pytest.fixture
def db_session(database: tuple[str, str]) -> Iterator[Session]:
    """A SQLAlchemy session as the *application* role.

    Not autocommit: the point of most of these tests is what happens at the
    transaction boundary, so the boundary has to be real.
    """
    engine = create_engine(_to_sqlalchemy(database[1]))
    try:
        with sessionmaker(bind=engine, expire_on_commit=False)() as s:
            yield s
    finally:
        engine.dispose()


@pytest.fixture
def application(database: tuple[str, str], monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A `TestClient` whose application really talks to the test database.

    The engine is pointed at the restricted role rather than the dependency
    being overridden, because two writers bypass any override: the failure-path
    audit (`record_standalone`) and the replay revocation each open a session of
    their own, by design — an override would leave them pointing at whatever
    `DATABASE_URL` happens to say, which in CI is a database that does not exist.
    """
    from app.core.config import get_settings
    from app.core.db import reset_engine
    from app.core.security import reset_keys

    monkeypatch.setenv("DATABASE_URL", _to_sqlalchemy(database[1]))
    monkeypatch.setenv("DB_APP_ROLE", APP_ROLE)
    get_settings.cache_clear()
    reset_engine()
    reset_keys()

    # AC-0001-33 counts per source, and every test in the suite shares one
    # source and one database, so without this each test inherits the traffic of
    # all the ones before it and the throttle fires on whichever happens to run
    # late. That is an artifact of the harness, not a property of the system:
    # tests are independent scenarios, not one long session. Clearing the
    # counters is the honest fix — raising the ceilings until the suite passes
    # would be weakening the feature to suit the test runner.
    with psycopg.connect(database[0], autocommit=True) as cleanup:
        cleanup.execute("DELETE FROM limite_taxa")

    try:
        with TestClient(create_app()) as c:
            yield c
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        reset_engine()
        reset_keys()


@pytest.fixture
def create_user(db_session: Session) -> Callable[..., User]:
    """Insert a usuario directly.

    Member management is a later step (AC-0001-10 onwards); until it exists the
    only honest way to arrange "given an ativo usuario" is to write the row.
    """

    def create(
        *,
        email: str | None = None,
        password: str | None = "SenhaCorreta-12345",
        perfil: str = "servidor",
        status: str = "ativo",
        name: str = "Pessoa de Teste",
    ) -> User:
        user = User(
            nome=name,
            email=email or f"{uuid.uuid4().hex[:10]}@sc.gov.br",
            senha_hash=hash_password(password) if password else None,
            role=perfil,
            status=status,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return create


def cookie_from(response: object, name: str) -> str | None:
    """Read a Set-Cookie value from the raw headers.

    Not `response.cookies`: the refresh cookie is `Secure` (AC-0001-01) and the
    test client speaks plain http, so the cookie jar discards it — the flag
    under test would make the test that checks it unable to see it.
    """
    for raw in response.headers.get_list("set-cookie"):  # type: ignore[attr-defined]
        attribute, _, rest = raw.partition("=")
        if attribute.strip() == name:
            return rest.split(";")[0]
    return None


def use_refresh(client: TestClient, value: str) -> None:
    """Put a refresh token in the client's jar.

    Necessary because the cookie the application sets is `Secure` and the test
    client speaks plain http, so the jar drops it on arrival — the flag under
    test would otherwise make every flow that uses the cookie untestable.
    """
    client.cookies.set("sigi_refresh", value)
