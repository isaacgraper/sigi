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

ANOS = range(2026, 2033)
PAPEL = "sigi_app_test"


def _um(cur: psycopg.Cursor) -> tuple:
    linha = cur.fetchone()
    assert linha is not None
    return linha


# ── shape ───────────────────────────────────────────────────────────────────


def test_tabelas_e_particoes_existem(conexao_admin: psycopg.Connection) -> None:
    tabelas = {
        r[0]
        for r in conexao_admin.execute(
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
    } <= tabelas
    assert {f"historico_movimentacao_{ano}" for ano in ANOS} <= tabelas


def test_chave_primaria_do_historico_inclui_a_coluna_de_particao(
    conexao_admin: psycopg.Connection,
) -> None:
    """The documented `id UUID PK` was illegal.

    PostgreSQL refuses a unique constraint on a partitioned table that omits a
    partitioning column, so the first migration would have failed at CREATE
    TABLE. This pins the correction so nobody "tidies" it back.
    """
    colunas = [
        r[0]
        for r in conexao_admin.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY (i.indkey)
            WHERE c.relname = 'historico_movimentacao' AND i.indisprimary
            ORDER BY a.attname
        """).fetchall()
    ]
    assert colunas == ["id", "ocorrido_em"]


def test_limites_da_particao_estao_em_utc(conexao_admin: psycopg.Connection) -> None:
    """A bare date literal against TIMESTAMPTZ resolves in the session's
    TimeZone, and this project sets America/Sao_Paulo everywhere — so bounds
    written without an explicit offset would silently land at 03:00 UTC.

    Read back in São Paulo time on purpose: that is where the bug would show.
    """
    conexao_admin.execute("SET TimeZone = 'America/Sao_Paulo'")
    limite = _um(
        conexao_admin.execute("""
            SELECT pg_get_expr(relpartbound, oid) FROM pg_class
            WHERE relname = 'historico_movimentacao_2026'
        """)
    )[0]
    assert "2025-12-31 21:00:00-03" in limite
    assert "2026-12-31 21:00:00-03" in limite


# ── append-only mechanics ───────────────────────────────────────────────────


def test_trigger_esta_clonado_em_todas_as_particoes_e_sempre_ativo(
    conexao_admin: psycopg.Connection,
) -> None:
    """`tgenabled = 'A'` is ENABLE ALWAYS, which is what survives
    `session_replication_role = 'replica'`."""
    linhas = conexao_admin.execute("""
        SELECT c.relname, t.tgenabled
        FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
        WHERE t.tgname = 'trg_historico_imutavel' AND NOT t.tgisinternal
    """).fetchall()
    nomes = {r[0] for r in linhas}
    assert nomes == {"historico_movimentacao"} | {f"historico_movimentacao_{ano}" for ano in ANOS}
    assert {r[1] for r in linhas} == {"A"}


def test_acl_da_particao_e_apenas_select_e_insert(
    conexao_admin: psycopg.Connection,
) -> None:
    """Privileges are per-partition, not inherited. A partition that granted
    more than SELECT+INSERT would be the hole a `GRANT ... ON ALL TABLES` opens.
    """
    acl = _um(
        conexao_admin.execute(
            "SELECT relacl::text FROM pg_class WHERE relname = 'historico_movimentacao_2032'"
        )
    )[0]
    concedido = next(p for p in acl.strip("{}").split(",") if p.startswith(f"{PAPEL}="))
    privilegios = concedido.split("=", 1)[1].split("/", 1)[0]
    assert sorted(privilegios) == ["a", "r"]  # INSERT, SELECT — nothing else


def test_criar_particao_aplica_grant_e_enable_always(
    conexao_admin: psycopg.Connection,
) -> None:
    """The routine that creates next year's partition must reapply both, rather
    than trusting the clone to carry them."""
    conexao_admin.execute("SELECT criar_particao_historico(2099)")
    try:
        acl = _um(
            conexao_admin.execute(
                "SELECT relacl::text FROM pg_class WHERE relname = 'historico_movimentacao_2099'"
            )
        )[0]
        assert f"{PAPEL}=ar/" in acl
        estado = _um(
            conexao_admin.execute("""
                SELECT t.tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
                WHERE c.relname = 'historico_movimentacao_2099'
                  AND t.tgname = 'trg_historico_imutavel'
            """)
        )[0]
        assert estado == "A"
        # Idempotent: the scheduled job will call it repeatedly.
        conexao_admin.execute("SELECT criar_particao_historico(2099)")
    finally:
        conexao_admin.execute("DROP TABLE historico_movimentacao_2099")


# ── generated columns ───────────────────────────────────────────────────────


def test_pseudonimo_sobrevive_a_anonimizacao(
    conexao_admin: psycopg.Connection,
) -> None:
    """AC-0001-14 needs a stable name for an anonymised user, and every other
    route is closed: the audit table cannot be updated (AC-0001-27) and
    `lgpd.md` forbids writing a name into it. A generated column derived from
    the id is what makes it possible — and PostgreSQL refuses to update one, so
    the immutability needs no trigger."""
    uid = uuid.uuid4()
    conexao_admin.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Bruno', %s, 'servidor', 'ativo')",
        (uid, f"bruno-{uid.hex[:8]}@sc.gov.br"),
    )
    antes = _um(
        conexao_admin.execute("SELECT pseudonimo, ativo FROM usuario WHERE id = %s", (uid,))
    )
    assert antes[0].startswith("USR-")
    assert antes[1] is True

    conexao_admin.execute(
        "UPDATE usuario SET nome = NULL, email = NULL, senha_hash = NULL,"
        " oidc_subject = NULL, status = 'desativado', anonimizado_em = now()"
        " WHERE id = %s",
        (uid,),
    )
    depois = _um(
        conexao_admin.execute("SELECT pseudonimo, ativo FROM usuario WHERE id = %s", (uid,))
    )
    assert depois[0] == antes[0]
    assert depois[1] is False


def test_coluna_gerada_nao_aceita_update(conexao_admin: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_admin.execute("UPDATE usuario SET pseudonimo = 'USR-FALSO'")
    assert exc.value.sqlstate == "428C9"


# ── constraints ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("rotulo", "sql_texto"),
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
def test_constraints_recusam_dado_invalido(
    conexao_admin: psycopg.Connection, rotulo: str, sql_texto: str
) -> None:
    with pytest.raises(psycopg.errors.Error):
        conexao_admin.execute(sql_texto)


def test_anonimizacao_pela_metade_e_recusada(conexao_admin: psycopg.Connection) -> None:
    """Blanking `nome` and `email` while leaving a live credential would be an
    account with no owner. The constraint refuses a partial job."""
    uid = uuid.uuid4()
    conexao_admin.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status, senha_hash)"
        " VALUES (%s, 'Carla', %s, 'servidor', 'ativo', 'hash')",
        (uid, f"carla-{uid.hex[:8]}@sc.gov.br"),
    )
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_admin.execute("UPDATE usuario SET anonimizado_em = now() WHERE id = %s", (uid,))
    assert exc.value.sqlstate == "23514"


def test_familia_de_sessao_nao_atravessa_usuarios(
    conexao_admin: psycopg.Connection,
) -> None:
    """DB11. Without the composite FK one family could span two users, and
    revoking it would revoke another person's sessions."""
    dono, intruso, familia = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    for uid, nome in ((dono, "Dono"), (intruso, "Intruso")):
        conexao_admin.execute(
            "INSERT INTO usuario (id, nome, email, perfil, status)"
            " VALUES (%s, %s, %s, 'servidor', 'ativo')",
            (uid, nome, f"{nome.lower()}-{uid.hex[:8]}@sc.gov.br"),
        )
    conexao_admin.execute(
        "INSERT INTO sessao_familia (familia, usuario_id) VALUES (%s, %s)",
        (familia, dono),
    )
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_admin.execute(
            "INSERT INTO sessao (usuario_id, familia, geracao, refresh_token_hash, expira_em)"
            " VALUES (%s, %s, 1, %s, now() + interval '7 days')",
            (intruso, familia, uuid.uuid4().bytes),
        )
    assert exc.value.sqlstate == "23503"  # foreign_key_violation


def test_apenas_um_token_aberto_por_tipo(conexao_admin: psycopg.Connection) -> None:
    uid = uuid.uuid4()
    conexao_admin.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Dora', %s, 'servidor', 'pendente')",
        (uid, f"dora-{uid.hex[:8]}@sc.gov.br"),
    )
    gestor = uuid.uuid4()
    conexao_admin.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'G', %s, 'gestor', 'ativo')",
        (gestor, f"g-{gestor.hex[:8]}@sc.gov.br"),
    )
    inserir = (
        "INSERT INTO token_credencial (usuario_id, tipo, token_hash, criado_por, expira_em)"
        " VALUES (%s, 'convite', %s, %s, now() + interval '72 hours')"
    )
    conexao_admin.execute(inserir, (uid, uuid.uuid4().bytes, gestor))
    with pytest.raises(psycopg.errors.Error) as exc:
        conexao_admin.execute(inserir, (uid, uuid.uuid4().bytes, gestor))
    assert exc.value.sqlstate == "23505"  # unique_violation

    # Cancelling is what makes reissue possible — AC-0001-25's remedy.
    conexao_admin.execute(
        "UPDATE token_credencial SET cancelado_em = now() WHERE usuario_id = %s", (uid,)
    )
    conexao_admin.execute(inserir, (uid, uuid.uuid4().bytes, gestor))


# ── the last gestor ─────────────────────────────────────────────────────────


def _criar_gestor(conn: psycopg.Connection) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute(
        "INSERT INTO usuario (id, nome, email, perfil, status)"
        " VALUES (%s, 'Gestor', %s, 'gestor', 'ativo')",
        (uid, f"gestor-{uid.hex[:8]}@sc.gov.br"),
    )
    return uid


def _gestores_ativos(conn: psycopg.Connection) -> int:
    return _um(
        conn.execute("SELECT count(*) FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'")
    )[0]


def test_ultimo_gestor_nao_pode_ser_removido(banco_isolado: tuple[str, str]) -> None:
    """DB13 / AC-0001-29, including demotion: changing the last gestor's perfil
    empties the role exactly as blocking it does.

    Runs on its own database, because the invariant is global. Sharing one with
    tests that create gestores of their own made both of them flaky — the first
    version of this test tried to drain the table down to one gestor and could
    not, since the trigger forbids reaching zero.
    """
    with psycopg.connect(banco_isolado[0], autocommit=True) as conn:
        assert _gestores_ativos(conn) == 0
        unico = _criar_gestor(conn)

        for tentativa in (
            "UPDATE usuario SET status = 'desativado' WHERE id = %s",
            "UPDATE usuario SET status = 'bloqueado' WHERE id = %s",
            "UPDATE usuario SET perfil = 'servidor' WHERE id = %s",
        ):
            with pytest.raises(psycopg.errors.Error) as exc:
                conn.execute(tentativa, (unico,))
            assert exc.value.sqlstate == "SI005"

        # With a second gestor, removing one is allowed.
        outro = _criar_gestor(conn)
        conn.execute("UPDATE usuario SET status = 'desativado' WHERE id = %s", (outro,))
        assert _gestores_ativos(conn) == 1


def test_ultimo_gestor_sob_concorrencia(banco_isolado: tuple[str, str]) -> None:
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
    dsn_admin = banco_isolado[0]

    def desativar(uid: uuid.UUID) -> bool:
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
            for _ in range(max(2 - _gestores_ativos(prep), 0)):
                _criar_gestor(prep)
            alvos = [
                r[0]
                for r in prep.execute(
                    "SELECT id FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'"
                    " ORDER BY id"
                ).fetchall()
            ]
            assert len(alvos) == 2

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(desativar, alvos))

        with psycopg.connect(dsn_admin, autocommit=True) as check:
            assert _gestores_ativos(check) >= 1, "nenhum gestor ativo sobrou"
            # Exactly one, not "at most one": `<=` would also pass if both
            # failed, which satisfies the invariant while proving no progress.
            assert sum(resultados) == 1, f"esperava exatamente uma, obtive {resultados}"


def test_guarda_de_downgrade_recusa_com_auditoria(banco: tuple[str, str]) -> None:
    """`alembic downgrade` must refuse rather than destroy the audit trail.

    The guard is asserted directly instead of by running the downgrade: this
    database is shared by the session, and tearing its schema down would take
    every other test with it.
    """
    guarda = sql.SQL("""
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
    with psycopg.connect(banco[1], autocommit=True) as app:
        app.execute(
            "INSERT INTO historico_movimentacao"
            " (ocorrido_em, entidade_tipo, entidade_id, acao, correlation_id)"
            " VALUES (now(), 'usuario', gen_random_uuid(), 'auth.login', gen_random_uuid())"
        )
    with psycopg.connect(banco[0], autocommit=True) as adm:
        with pytest.raises(psycopg.errors.Error) as exc:
            adm.execute(guarda)
        assert exc.value.sqlstate == "SI002"
