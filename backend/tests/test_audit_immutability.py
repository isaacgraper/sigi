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

SQLSTATE_PRIVILEGIO = "42501"
SQLSTATE_IMUTAVEL = "SI001"
SQLSTATE_SEM_PARTICAO = "23514"


def _semear(admin: psycopg.Connection, app: psycopg.Connection) -> uuid.UUID:
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


def test_ac_0001_27_aplicacao_consegue_inserir(
    conexao_admin: psycopg.Connection, conexao_app: psycopg.Connection
) -> None:
    """The guard must not be so tight that the trail cannot be written."""
    uid = _semear(conexao_admin, conexao_app)
    linha = conexao_app.execute(
        "SELECT count(*) FROM historico_movimentacao WHERE usuario_id = %s", (uid,)
    ).fetchone()
    assert linha is not None
    assert linha[0] == 1


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
def test_ac_0001_27_aplicacao_nao_reescreve(
    conexao_admin: psycopg.Connection, conexao_app: psycopg.Connection, sql: str
) -> None:
    """Privileges stop the application, on the parent *and* on a named partition.

    The partition cases are the ones worth having: privileges are per-partition
    rather than inherited, so a `GRANT ... ON ALL TABLES IN SCHEMA public` in
    somebody's convenience script would open exactly these holes.
    """
    _semear(conexao_admin, conexao_app)
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_app.execute(sql)
    assert exc.value.sqlstate == SQLSTATE_PRIVILEGIO


def test_ac_0001_27_dono_tambem_e_recusado(
    conexao_admin: psycopg.Connection, conexao_app: psycopg.Connection
) -> None:
    """The owner has the privilege, so only the trigger can refuse it.

    This is the case that makes two roles necessary rather than decorative: if
    the application connected as the owner, the privilege half of ADR-0004
    would be doing nothing at all.
    """
    _semear(conexao_admin, conexao_app)
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_admin.execute("UPDATE historico_movimentacao SET acao = 'x.y'")
    assert exc.value.sqlstate == SQLSTATE_IMUTAVEL


def test_ac_0001_27_replica_nao_desliga_o_trigger(
    conexao_admin: psycopg.Connection, conexao_app: psycopg.Connection
) -> None:
    """`session_replication_role = 'replica'` is the documented way to bypass a
    trigger. `ENABLE ALWAYS` is why it does not work here."""
    _semear(conexao_admin, conexao_app)
    conexao_admin.execute("SET session_replication_role = 'replica'")
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_admin.execute("UPDATE historico_movimentacao SET acao = 'x.y'")
    assert exc.value.sqlstate == SQLSTATE_IMUTAVEL


def test_ac_0001_27_linha_sobrevive_a_todas_as_tentativas(
    conexao_admin: psycopg.Connection, conexao_app: psycopg.Connection
) -> None:
    uid = _semear(conexao_admin, conexao_app)
    consulta = "SELECT id, acao, usuario_id FROM historico_movimentacao WHERE usuario_id = %s"
    before = conexao_app.execute(consulta, (uid,)).fetchone()
    for tentativa in (
        "UPDATE historico_movimentacao SET acao = 'x.y'",
        "DELETE FROM historico_movimentacao",
    ):
        with pytest.raises(psycopg.errors.Error):
            conexao_app.execute(tentativa)
    after = conexao_app.execute(consulta, (uid,)).fetchone()
    assert before == after
    assert after is not None and after[2] == uid


def test_ano_sem_particao_falha_de_forma_conhecida(
    conexao_app: psycopg.Connection,
) -> None:
    """The January outage, asserted rather than discovered.

    Nothing creates next year's partition, and every write in SIGI records its
    history row in the same transaction — so an unpartitioned year means every
    write endpoint returns 500. Partitions run to 2032; this test pins the
    failure mode so the day someone extends the range, they know what they are
    preventing.
    """
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_app.execute(
            "INSERT INTO historico_movimentacao"
            " (ocorrido_em, entidade_tipo, entidade_id, acao, correlation_id)"
            " VALUES ('2033-06-01T00:00:00Z', 'usuario', gen_random_uuid(),"
            " 'auth.login', gen_random_uuid())"
        )
    assert exc.value.sqlstate == SQLSTATE_SEM_PARTICAO
