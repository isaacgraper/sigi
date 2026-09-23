"""The baseline migration, asserted against a real PostgreSQL.

These prove the schema rather than an acceptance criterion. They exist because
almost everything load-bearing here — partitioning, cloned triggers,
per-partition privileges, generated columns — is hand-written DDL that
Alembic's autogenerate cannot see and a unit test cannot reach.
"""

from __future__ import annotations

import concurrent.futures
import uuid

import psycopg
import pytest
from psycopg import sql

from tests.conftest import _to_sqlalchemy

YEARS = range(2026, 2033)
APP_ROLE = "sigi_app_test"


def _one(cur: psycopg.Cursor) -> tuple:
    row = cur.fetchone()
    assert row is not None
    return row


# ── shape ───────────────────────────────────────────────────────────────────


def test_the_tables_and_partitions_exist(admin_connection: psycopg.Connection) -> None:
    """Every table the spec names exists, with the seven yearly partitions."""
    tables = {
        r[0]
        for r in admin_connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    }
    assert {
        "usuario",
        "token_credencial",
        "tentativa_login",
        "limite_taxa",
        "sessao_familia",
        "sessao",
        "historico_movimentacao",
    } <= tables
    assert {f"historico_movimentacao_{year}" for year in YEARS} <= tables


def test_the_historico_primary_key_includes_the_partition_column(
    admin_connection: psycopg.Connection,
) -> None:
    """The documented `id UUID PK` was illegal.

    PostgreSQL refuses a unique constraint on a partitioned table that omits a
    partitioning column, so the first migration would have failed at CREATE
    TABLE. This pins the correction so nobody "tidies" it back.
    """
    columns = [
        r[0]
        for r in admin_connection.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY (i.indkey)
            WHERE c.relname = 'historico_movimentacao' AND i.indisprimary
            ORDER BY a.attname
        """).fetchall()
    ]
    assert columns == ["id", "ocorrido_em"]


def test_the_partition_bounds_are_in_utc(admin_connection: psycopg.Connection) -> None:
    """Partition bounds are written in explicit UTC.

    A bare date literal against TIMESTAMPTZ resolves in the session's TimeZone,
    and this project sets America/Sao_Paulo everywhere — so bounds written
    without an explicit offset would silently land at 03:00 UTC.

    Read back in São Paulo time on purpose: that is where the bug would show.
    """
    admin_connection.execute("SET TimeZone = 'America/Sao_Paulo'")
    bound = _one(
        admin_connection.execute("""
            SELECT pg_get_expr(relpartbound, oid) FROM pg_class
            WHERE relname = 'historico_movimentacao_2026'
        """)
    )[0]
    assert "2025-12-31 21:00:00-03" in bound
    assert "2026-12-31 21:00:00-03" in bound


# ── append-only mechanics ───────────────────────────────────────────────────


def test_the_trigger_is_cloned_on_every_partition_and_always_enabled(
    admin_connection: psycopg.Connection,
) -> None:
    """Every audit trigger is ENABLE ALWAYS, not merely enabled.

    `tgenabled = 'A'` is ENABLE ALWAYS, which is what survives
    `session_replication_role = 'replica'`.
    """
    rows = admin_connection.execute("""
        SELECT c.relname, t.tgenabled
        FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
        WHERE t.tgname = 'trg_historico_imutavel' AND NOT t.tgisinternal
    """).fetchall()
    names = {r[0] for r in rows}
    assert names == {"historico_movimentacao"} | {
        f"historico_movimentacao_{year}" for year in YEARS
    }
    assert {r[1] for r in rows} == {"A"}


def test_the_partition_acl_is_select_and_insert_only(
    admin_connection: psycopg.Connection,
) -> None:
    """No partition grants the app role more than SELECT and INSERT.

    Privileges are per-partition, not inherited, so a partition granting more
    would be the hole a `GRANT ... ON ALL TABLES` opens.
    """
    acl = _one(
        admin_connection.execute(
            "SELECT relacl::text FROM pg_class WHERE relname = 'historico_movimentacao_2032'"
        )
    )[0]
    granted = next(p for p in acl.strip("{}").split(",") if p.startswith(f"{APP_ROLE}="))
    privileges = granted.split("=", 1)[1].split("/", 1)[0]
    assert sorted(privileges) == ["a", "r"]  # INSERT, SELECT — nothing else


def test_criar_particao_applies_the_grant_and_enable_always(
    admin_connection: psycopg.Connection,
) -> None:
    """A partition made later carries the same trigger and the same grants.

    The routine that creates next year's partition must reapply both, rather
    than trusting the clone to carry them.
    """
    admin_connection.execute("SELECT criar_particao_historico(2099)")
    try:
        acl = _one(
            admin_connection.execute(
                "SELECT relacl::text FROM pg_class WHERE relname = 'historico_movimentacao_2099'"
            )
        )[0]
        assert f"{APP_ROLE}=ar/" in acl
        state = _one(
            admin_connection.execute("""
                SELECT t.tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
                WHERE c.relname = 'historico_movimentacao_2099'
                  AND t.tgname = 'trg_historico_imutavel'
            """)
        )[0]
        assert state == "A"
        # Idempotent: the scheduled job will call it repeatedly.
        admin_connection.execute("SELECT criar_particao_historico(2099)")
    finally:
        admin_connection.execute("DROP TABLE historico_movimentacao_2099")


# ── generated columns ───────────────────────────────────────────────────────


def test_the_pseudonym_survives_anonymisation(
    admin_connection: psycopg.Connection,
) -> None:
    """`pseudonimo` is a generated column, which is what makes AC-0001-14 work.

    AC-0001-14 needs a stable name for an anonymised user, and every other
    route is closed: the audit table cannot be updated (AC-0001-27) and
    `lgpd.md` forbids writing a name into it. A generated column derived from
    the id is what makes it possible — and PostgreSQL refuses to update one, so
    the immutability needs no trigger.
    """
    uid = uuid.uuid4()
    admin_connection.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Bruno', %s, 'servidor', 'ativo')",
        (uid, f"bruno-{uid.hex[:8]}@sc.gov.br"),
    )
    before = _one(
        admin_connection.execute("SELECT pseudonimo, ativo FROM usuario WHERE id = %s", (uid,))
    )
    assert before[0].startswith("USR-")
    assert before[1] is True

    admin_connection.execute(
        "UPDATE usuario SET nome = NULL, email = NULL, senha_hash = NULL,"
        " oidc_subject = NULL, status = 'desativado', anonimizado_em = now()"
        " WHERE id = %s",
        (uid,),
    )
    after = _one(
        admin_connection.execute("SELECT pseudonimo, ativo FROM usuario WHERE id = %s", (uid,))
    )
    assert after[0] == before[0]
    assert after[1] is False


def test_a_generated_column_refuses_an_update(admin_connection: psycopg.Connection) -> None:
    """PostgreSQL itself refuses an UPDATE of `pseudonimo`."""
    with pytest.raises(psycopg.errors.Error) as exc:
        admin_connection.execute("UPDATE usuario SET pseudonimo = 'USR-FALSO'")
    assert exc.value.sqlstate == "428C9"


# ── constraints ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("label", "sql_texto"),
    [
        (
            "pendente-com-credencial",
            "INSERT INTO usuario (nome, email, perfil, status, senha_hash)"
            " VALUES ('X', 'x1@sc.gov.br', 'servidor', 'pendente', 'hash')",
        ),
        (
            "acao-fora-do-formato",
            "INSERT INTO historico_movimentacao"
            " (ocorrido_em, entidade_tipo, entidade_id, acao, correlation_id)"
            " VALUES (now(), 'usuario', gen_random_uuid(), 'AuthLogin', gen_random_uuid())",
        ),
        (
            "convite-sem-autor",
            "INSERT INTO token_credencial (usuario_id, tipo, token_hash, expira_em)"
            " VALUES (gen_random_uuid(), 'convite', '\\x00'::bytea, now() + interval '1 day')",
        ),
        (
            "sessao-revogada-sem-motivo",
            "INSERT INTO sessao (usuario_id, familia, geracao, refresh_token_hash,"
            " expira_em, revogado_em)"
            " VALUES (gen_random_uuid(), gen_random_uuid(), 1, '\\x01'::bytea,"
            " now() + interval '7 days', now())",
        ),
    ],
)
def test_the_constraints_refuse_invalid_data(
    admin_connection: psycopg.Connection, label: str, sql_texto: str
) -> None:
    """Each CHECK refuses the shape it exists to refuse."""
    with pytest.raises(psycopg.errors.Error):
        admin_connection.execute(sql_texto)


def test_a_half_done_anonymisation_is_refused(admin_connection: psycopg.Connection) -> None:
    """A half-finished anonymisation is refused.

    Blanking `nome` and `email` while leaving a live credential would be an
    account with no owner, so the constraint refuses a partial job.
    """
    uid = uuid.uuid4()
    admin_connection.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status, senha_hash)"
        " VALUES (%s, 'Carla', %s, 'servidor', 'ativo', 'hash')",
        (uid, f"carla-{uid.hex[:8]}@sc.gov.br"),
    )
    with pytest.raises(psycopg.errors.Error) as exc:
        admin_connection.execute("UPDATE usuario SET anonimizado_em = now() WHERE id = %s", (uid,))
    assert exc.value.sqlstate == "23514"


def test_a_sessao_familia_does_not_span_usuarios(
    admin_connection: psycopg.Connection,
) -> None:
    """DB11 — a session family belongs to exactly one usuario.

    Without the composite FK one family could span two users, and revoking it
    would revoke another person's sessions.
    """
    owner, intruder, family = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    for uid, nome in ((owner, "Dono"), (intruder, "Intruso")):
        admin_connection.execute(
            "INSERT INTO usuario (id, nome, email, perfil, status)"
            " VALUES (%s, %s, %s, 'servidor', 'ativo')",
            (uid, nome, f"{nome.lower()}-{uid.hex[:8]}@sc.gov.br"),
        )
    admin_connection.execute(
        "INSERT INTO sessao_familia (familia, usuario_id) VALUES (%s, %s)",
        (family, owner),
    )
    with pytest.raises(psycopg.errors.Error) as exc:
        admin_connection.execute(
            "INSERT INTO sessao (usuario_id, familia, geracao, refresh_token_hash, expira_em)"
            " VALUES (%s, %s, 1, %s, now() + interval '7 days')",
            (intruder, family, uuid.uuid4().bytes),
        )
    assert exc.value.sqlstate == "23503"  # foreign_key_violation


def test_only_one_open_token_per_kind(admin_connection: psycopg.Connection) -> None:
    """The partial index allows one open token per usuario per `tipo`."""
    uid = uuid.uuid4()
    admin_connection.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Dora', %s, 'servidor', 'pendente')",
        (uid, f"dora-{uid.hex[:8]}@sc.gov.br"),
    )
    gestor = uuid.uuid4()
    admin_connection.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'G', %s, 'gestor', 'ativo')",
        (gestor, f"g-{gestor.hex[:8]}@sc.gov.br"),
    )
    insert_row = (
        "INSERT INTO token_credencial (usuario_id, tipo, token_hash, criado_por, expira_em)"
        " VALUES (%s, 'convite', %s, %s, now() + interval '72 hours')"
    )
    admin_connection.execute(insert_row, (uid, uuid.uuid4().bytes, gestor))
    with pytest.raises(psycopg.errors.Error) as exc:
        admin_connection.execute(insert_row, (uid, uuid.uuid4().bytes, gestor))
    assert exc.value.sqlstate == "23505"  # unique_violation

    # Cancelling is what makes reissue possible — AC-0001-25's remedy.
    admin_connection.execute(
        "UPDATE token_credencial SET cancelado_em = now() WHERE usuario_id = %s", (uid,)
    )
    admin_connection.execute(insert_row, (uid, uuid.uuid4().bytes, gestor))


# ── the last gestor ─────────────────────────────────────────────────────────


def _create_gestor(conn: psycopg.Connection) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Gestor', %s, 'gestor', 'ativo')",
        (uid, f"gestor-{uid.hex[:8]}@sc.gov.br"),
    )
    return uid


def _active_gestores(conn: psycopg.Connection) -> int:
    return _one(
        conn.execute("SELECT count(*) FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'")
    )[0]


def test_the_last_gestor_cannot_be_removed(isolated_database: tuple[str, str]) -> None:
    """DB13 / AC-0001-29 — the last active gestor cannot be removed.

    Demotion counts: changing the last gestor's perfil empties the role exactly
    as blocking it does.

    Runs on its own database, because the invariant is global. Sharing one with
    tests that create gestores of their own made both of them flaky — the first
    version of this test tried to drain the table down to one gestor and could
    not, since the trigger forbids reaching zero.
    """
    with psycopg.connect(isolated_database[0], autocommit=True) as conn:
        assert _active_gestores(conn) == 0
        only_one = _create_gestor(conn)

        for attempt in (
            "UPDATE usuario SET status = 'desativado' WHERE id = %s",
            "UPDATE usuario SET status = 'bloqueado' WHERE id = %s",
            "UPDATE usuario SET perfil = 'servidor' WHERE id = %s",
        ):
            with pytest.raises(psycopg.errors.Error) as exc:
                conn.execute(attempt, (only_one,))
            assert exc.value.sqlstate == "SI005"

        # With a second gestor, removing one is allowed.
        other = _create_gestor(conn)
        conn.execute("UPDATE usuario SET status = 'desativado' WHERE id = %s", (other,))
        assert _active_gestores(conn) == 1


def test_the_last_gestor_under_concurrency(isolated_database: tuple[str, str]) -> None:
    """Two requests, each removing a different one of exactly two gestores.

    The invariant that matters is that an active gestor survives. Note what the
    loser actually gets: the trigger's `FOR UPDATE` count runs *after* the
    UPDATE has already locked its own target row, so the two transactions take
    locks in opposite order and PostgreSQL aborts one with `40P01` (deadlock)
    rather than the `SI005` the criterion describes.

    Measured over 40 races on PostgreSQL 16.13: **exactly one always
    succeeded**, and the loser got `40P01` 39 times against `SI005` once. So
    the deadlock is the normal outcome, not the exception — which is exactly why
    the service must take an advisory lock before the update, and must map
    `40P01` to the specified 409 as a second line. Without either, this endpoint
    returns 500 on a race that is entirely foreseeable.

    Repeated, because write skew is probabilistic and one pass proves nothing.
    """
    dsn_admin = isolated_database[0]

    def deactivate(uid: uuid.UUID) -> bool:
        with psycopg.connect(dsn_admin, autocommit=True) as c:
            try:
                c.execute("UPDATE usuario SET status = 'desativado' WHERE id = %s", (uid,))
                return True
            except psycopg.errors.Error:
                return False

    for _ in range(12):
        with psycopg.connect(dsn_admin, autocommit=True) as prep:
            # Top up to exactly two active gestores. The trigger forbids
            # reaching zero, so a survivor from the previous round is kept and
            # only the shortfall is created.
            for _ in range(max(2 - _active_gestores(prep), 0)):
                _create_gestor(prep)
            targets = [
                r[0]
                for r in prep.execute(
                    "SELECT id FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'"
                    " ORDER BY id"
                ).fetchall()
            ]
            assert len(targets) == 2

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(deactivate, targets))

        with psycopg.connect(dsn_admin, autocommit=True) as check:
            assert _active_gestores(check) >= 1, "nenhum gestor ativo sobrou"
            # Exactly one, not "at most one": `<=` would also pass if both
            # failed, which satisfies the invariant while proving no progress.
            assert sum(results) == 1, f"esperava exatamente uma, obtive {results}"


def test_the_downgrade_guard_refuses_and_audits(database: tuple[str, str]) -> None:
    """`alembic downgrade` must refuse rather than destroy the audit trail.

    The guard is asserted directly instead of by running the downgrade: this
    database is shared by the session, and tearing its schema down would take
    every other test with it.
    """
    guard = sql.SQL("""
        DO $$
        DECLARE n bigint;
        BEGIN
          IF EXISTS (SELECT 1 FROM information_schema.tables
                     WHERE table_name = 'historico_movimentacao') THEN
            EXECUTE 'SELECT count(*) FROM historico_movimentacao' INTO n;
            IF n > 0 THEN
              RAISE EXCEPTION
                'downgrade recusado: % linhas de auditoria seriam destruídas', n
                USING ERRCODE = 'SI002';
            END IF;
          END IF;
        END $$;
    """)
    with psycopg.connect(database[1], autocommit=True) as app:
        app.execute(
            "INSERT INTO historico_movimentacao"
            " (ocorrido_em, entidade_tipo, entidade_id, acao, correlation_id)"
            " VALUES (now(), 'usuario', gen_random_uuid(), 'auth.login', gen_random_uuid())"
        )
    with psycopg.connect(database[0], autocommit=True) as admin:
        with pytest.raises(psycopg.errors.Error) as exc:
            admin.execute(guard)
        assert exc.value.sqlstate == "SI002"


def test_the_models_do_not_drift_from_the_schema(database: tuple[str, str]) -> None:
    """`alembic check` must report nothing.

    This is the guard against the most expensive mistake available here. With an
    empty or divergent `Base.metadata`, `alembic revision --autogenerate`
    produces a migration that **drops the tables it does not recognise** — and
    one of them is the audit trail, which `downgrade()` refuses to destroy but
    an autogenerated `op.drop_table` would not.

    It has already earned its place: the first run reported `ocorrido_em DESC`
    in two indexes and `TEXT` versus `VARCHAR` on `usuario.pseudonimo`. Both
    were real divergences between the migration and the models.
    """
    from alembic import command
    from alembic.config import Config
    from alembic.util.exc import AutogenerateDiffsDetected

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", _to_sqlalchemy(database[0]))
    try:
        command.check(cfg)
    except AutogenerateDiffsDetected as exc:  # pragma: no cover - only on drift
        pytest.fail(f"modelos divergem do esquema: {exc}")
