"""AC-0001-27 — the history table refuses to be rewritten.

RN06 and RNF08, enforced per ADR-0004 twice over: privileges stop the
application, and a trigger stops whatever the privileges do not. Each test
below covers one way the guarantee could be false, because "append-only" is a
claim about what *cannot* happen and only the refusals prove it.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

SQLSTATE_PRIVILEGE = "42501"
SQLSTATE_IMMUTABLE = "SI001"
SQLSTATE_NO_PARTITION = "23514"


def _seed(admin: psycopg.Connection, app: psycopg.Connection) -> uuid.UUID:
    """Create one usuario and one audit row, and return the usuario's id.

    The e-mail is unique per call and every assertion below is scoped to the
    returned id, because the database is shared across the session and the
    audit table cannot be emptied between tests — which is the property under
    test, so cleaning up would defeat the point.

    Every test seeds. A `BEFORE ... FOR EACH ROW` trigger never fires when the
    statement matches no rows, so an UPDATE against an empty table would
    succeed vacuously and the test would pass for the wrong reason.
    """
    uid = uuid.uuid4()
    admin.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Ana', %s, 'gestor', 'ativo')",
        (uid, f"ana-{uid.hex[:8]}@sc.gov.br"),
    )
    app.execute(
        "INSERT INTO historico_movimentacao"
        " (ocorrido_em, entidade_tipo, entidade_id, acao, usuario_id, correlation_id)"
        " VALUES (now(), 'usuario', %s, 'auth.login', %s, gen_random_uuid())",
        (uid, uid),
    )
    return uid


def test_ac_0001_27_the_application_can_insert(
    admin_connection: psycopg.Connection, app_connection: psycopg.Connection
) -> None:
    """The guard must not be so tight that the trail cannot be written."""
    uid = _seed(admin_connection, app_connection)
    row = app_connection.execute(
        "SELECT count(*) FROM historico_movimentacao WHERE usuario_id = %s", (uid,)
    ).fetchone()
    assert row is not None
    assert row[0] == 1


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE historico_movimentacao SET acao = 'x.y'",
        "DELETE FROM historico_movimentacao",
        "UPDATE historico_movimentacao_2026 SET acao = 'x.y'",
        "DELETE FROM historico_movimentacao_2026",
        "TRUNCATE historico_movimentacao_2026",
        "DROP TABLE historico_movimentacao_2026",
    ],
    ids=[
        "update-no-pai",
        "delete-no-pai",
        "update-na-particao",
        "delete-na-particao",
        "truncate-na-particao",
        "drop-da-particao",
    ],
)
def test_ac_0001_27_the_application_cannot_rewrite(
    admin_connection: psycopg.Connection, app_connection: psycopg.Connection, sql: str
) -> None:
    """Privileges stop the application, on the parent *and* on a named partition.

    The partition cases are the ones worth having: privileges are per-partition
    rather than inherited, so a `GRANT ... ON ALL TABLES IN SCHEMA public` in
    somebody's convenience script would open exactly these holes.
    """
    _seed(admin_connection, app_connection)
    with pytest.raises(psycopg.errors.Error) as exc:
        app_connection.execute(sql)
    assert exc.value.sqlstate == SQLSTATE_PRIVILEGE


def test_ac_0001_27_the_owner_is_refused_too(
    admin_connection: psycopg.Connection, app_connection: psycopg.Connection
) -> None:
    """The owner has the privilege, so only the trigger can refuse it.

    This is the case that makes two roles necessary rather than decorative: if
    the application connected as the owner, the privilege half of ADR-0004
    would be doing nothing at all.
    """
    _seed(admin_connection, app_connection)
    with pytest.raises(psycopg.errors.Error) as exc:
        admin_connection.execute("UPDATE historico_movimentacao SET acao = 'x.y'")
    assert exc.value.sqlstate == SQLSTATE_IMMUTABLE


def test_ac_0001_27_replica_does_not_disable_the_trigger(
    admin_connection: psycopg.Connection, app_connection: psycopg.Connection
) -> None:
    """The documented way to bypass a trigger does not work here.

    `session_replication_role = 'replica'` is that documented way, and
    `ENABLE ALWAYS` is why it has no effect.
    """
    _seed(admin_connection, app_connection)
    admin_connection.execute("SET session_replication_role = 'replica'")
    with pytest.raises(psycopg.errors.Error) as exc:
        admin_connection.execute("UPDATE historico_movimentacao SET acao = 'x.y'")
    assert exc.value.sqlstate == SQLSTATE_IMMUTABLE


def test_ac_0001_27_the_row_survives_every_attempt(
    admin_connection: psycopg.Connection, app_connection: psycopg.Connection
) -> None:
    """AC-0001-27 — the row is still there, unchanged, after every attempt."""
    uid = _seed(admin_connection, app_connection)
    query = "SELECT id, acao, usuario_id FROM historico_movimentacao WHERE usuario_id = %s"
    before = app_connection.execute(query, (uid,)).fetchone()
    for attempt in (
        "UPDATE historico_movimentacao SET acao = 'x.y'",
        "DELETE FROM historico_movimentacao",
    ):
        with pytest.raises(psycopg.errors.Error):
            app_connection.execute(attempt)
    after = app_connection.execute(query, (uid,)).fetchone()
    assert before == after
    assert after is not None and after[2] == uid


def test_a_year_without_a_partition_fails_in_a_known_way(
    app_connection: psycopg.Connection,
) -> None:
    """The January outage, asserted rather than discovered.

    Nothing creates next year's partition, and every write in SIGI records its
    history row in the same transaction — so an unpartitioned year means every
    write endpoint returns 500. Partitions run to 2032; this test pins the
    failure mode so the day someone extends the range, they know what they are
    preventing.
    """
    with pytest.raises(psycopg.errors.Error) as exc:
        app_connection.execute(
            "INSERT INTO historico_movimentacao"
            " (ocorrido_em, entidade_tipo, entidade_id, acao, correlation_id)"
            " VALUES ('2033-06-01T00:00:00Z', 'usuario', gen_random_uuid(),"
            " 'auth.login', gen_random_uuid())"
        )
    assert exc.value.sqlstate == SQLSTATE_NO_PARTITION
