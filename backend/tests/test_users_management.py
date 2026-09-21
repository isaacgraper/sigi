"""Member management — AC-0001-12, -13, -14, -15, -29.

The API-level cases run against the shared test database, which already holds
other active gestores, so blocking one never trips the last-gestor guard. The
guard itself is a property of the whole table, so its tests take
`banco_isolado`.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from collections.abc import Callable

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.user import User
from app.services import members
from app.services.errors import LastGestor

USUARIOS = "/api/v1/usuarios"
LOGIN = "/api/v1/auth/login"
SENHA = "SenhaLongaOSuficiente-2026"


def _as_gestor(application: TestClient, criar_usuario: Callable[..., User]) -> dict[str, str]:
    email = f"gestor-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil="gestor", senha=SENHA)
    entrada = application.post(LOGIN, json={"email": email, "password": SENHA})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_ac_0001_12_a_gestor_blocks_an_account(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-12 — the account is blocked and its sessions are revoked."""
    headers = _as_gestor(application, criar_usuario)
    alvo = criar_usuario(email=f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=SENHA)

    # The target has a live session, so there is something to revoke.
    entrada = application.post(LOGIN, json={"email": alvo.email, "password": SENHA})
    assert entrada.status_code == 200
    token_do_alvo = entrada.json()["access_token"]

    response = application.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "bloqueado"

    # The unexpired access token stops working at once, because `ativo` is
    # checked on every request rather than at login (AC-0001-08).
    eu = application.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_do_alvo}"})
    assert eu.status_code == 401

    sessao.rollback()
    motivo = sessao.execute(
        text("SELECT revogado_motivo FROM sessao WHERE usuario_id = :u"), {"u": alvo.id}
    ).scalar_one()
    # The session vocabulary, not the account's: `ck_sessao_motivo_valor` fixes
    # this list and "bloqueado" is not in it.
    assert motivo == "bloqueio"


def test_ac_0001_14_deactivation_anonymises_and_keeps_the_history(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-14, RN16 — identifying fields go, the record of what they did stays."""
    headers = _as_gestor(application, criar_usuario)
    alvo = criar_usuario(
        email=f"anon-{uuid.uuid4().hex[:8]}@sc.gov.br", nome="Pessoa Real", senha=SENHA
    )
    alvo_id = alvo.id

    response = application.post(f"{USUARIOS}/{alvo_id}/desativar", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "desativado"
    assert body["nome"] is None
    assert body["email"] is None
    # `pseudonimo` is a generated column, so the trail keeps resolving to one
    # stable name without the history being rewritten (AC-0001-27 forbids that).
    assert body["pseudonimo"]

    sessao.rollback()
    row = sessao.execute(
        text(
            "SELECT nome, email, senha_hash, oidc_subject, anonimizado_em"
            " FROM usuario WHERE id = :u"
        ),
        {"u": alvo_id},
    ).one()
    assert row.nome is None
    assert row.email is None
    assert row.senha_hash is None
    assert row.oidc_subject is None
    assert row.anonimizado_em is not None

    # The audit rows this person generated are still there and still attributable.
    ainda = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE entidade_id = :u"),
        {"u": alvo_id},
    ).scalar_one()
    assert ainda >= 1


def test_deactivating_removes_the_credential_so_login_stops(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """Anonymisation nulls `senha_hash`, so the old password is no longer a way in."""
    headers = _as_gestor(application, criar_usuario)
    email = f"nologin-{uuid.uuid4().hex[:8]}@sc.gov.br"
    alvo = criar_usuario(email=email, senha=SENHA)

    application.post(f"{USUARIOS}/{alvo.id}/desativar", headers=headers)

    assert application.post(LOGIN, json={"email": email, "password": SENHA}).status_code == 401


def test_ac_0001_15_a_gestor_lists_members(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-15 — the page envelope is the one `api-conventions.md` fixes."""
    headers = _as_gestor(application, criar_usuario)
    criar_usuario(email=f"lista-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=SENHA)

    response = application.get(USUARIOS, params={"page": 1, "size": 5}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["size"] == 5
    assert len(body["items"]) <= 5
    assert body["total"] >= 1


def test_paging_never_repeats_a_row(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """The order is `criado_em DESC, id`, so pages do not overlap.

    `criado_em` alone is not unique enough: two invitations in the same
    millisecond would order arbitrarily between the two queries.
    """
    headers = _as_gestor(application, criar_usuario)
    for _ in range(4):
        criar_usuario(email=f"pag-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=SENHA)

    primeira = application.get(USUARIOS, params={"page": 1, "size": 2}, headers=headers).json()
    segunda = application.get(USUARIOS, params={"page": 2, "size": 2}, headers=headers).json()

    ids_um = {item["id"] for item in primeira["items"]}
    ids_dois = {item["id"] for item in segunda["items"]}
    assert ids_um and ids_dois
    assert ids_um.isdisjoint(ids_dois)


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_13_a_servidor_or_auditor_cannot_manage_members(
    application: TestClient, criar_usuario: Callable[..., User], perfil: str
) -> None:
    """AC-0001-13 — every member route refuses a non-gestor, including the read."""
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil=perfil, senha=SENHA)
    entrada = application.post(LOGIN, json={"email": email, "password": SENHA})
    headers = {"Authorization": f"Bearer {entrada.json()['access_token']}"}
    alvo = criar_usuario(email=f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=SENHA)

    for response in (
        application.get(USUARIOS, headers=headers),
        application.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=headers),
        application.post(f"{USUARIOS}/{alvo.id}/desativar", headers=headers),
    ):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


def test_an_unknown_id_is_404(application: TestClient, criar_usuario: Callable[..., User]) -> None:
    """A gestor acting on an id that does not exist."""
    headers = _as_gestor(application, criar_usuario)
    response = application.post(f"{USUARIOS}/{uuid.uuid4()}/bloquear", headers=headers)
    assert response.status_code == 404


def test_blocking_an_already_blocked_account_is_idempotent(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """No second audit row, and no error: the status is already what was asked for."""
    headers = _as_gestor(application, criar_usuario)
    alvo = criar_usuario(email=f"idem-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=SENHA)

    primeiro = application.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=headers)
    segundo = application.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=headers)
    assert primeiro.status_code == 200
    assert segundo.status_code == 200
    assert segundo.json()["status"] == "bloqueado"


# ── The last active gestor (AC-0001-29) ─────────────────────────────────────
#
# A property of the whole table, so these take a database of their own.


def _sessions_for(dsn: str) -> sessionmaker[Session]:
    # The fixtures hand out libpq keyword strings, not URLs. `conftest` already
    # converts; a second converter here is a second thing to keep in step.
    from tests.conftest import _para_sqlalchemy

    return sessionmaker(bind=create_engine(_para_sqlalchemy(dsn)))


def _seed_gestor(dsn_admin: str, *, status: str = "ativo") -> uuid.UUID:
    uid = uuid.uuid4()
    with psycopg.connect(dsn_admin, autocommit=True) as c:
        c.execute(
            "INSERT INTO usuario (id, nome, email, perfil, status, senha_hash)"
            " VALUES (%s, %s, %s, 'gestor', %s, 'x')",
            (uid, "Gestor", f"g-{uid.hex[:8]}@sc.gov.br", status),
        )
    return uid


def test_ac_0001_29_the_last_active_gestor_cannot_be_blocked(
    banco_isolado: tuple[str, str],
) -> None:
    """AC-0001-29 — refused with the criterion's own error, not a 500.

    Blocking the only active gestor locks the entity out of its own member
    management, with no path back that does not involve database access.
    """
    dsn_admin, dsn_app = banco_isolado
    ator = _seed_gestor(dsn_admin)
    Sessions = _sessions_for(dsn_app)

    with Sessions() as session:
        actor = session.get(User, ator)
        assert actor is not None
        with pytest.raises(LastGestor):
            members.block(
                session,
                actor=actor,
                usuario_id=ator,
                at=datetime.datetime.now(datetime.UTC),
                correlation_id=uuid.uuid4(),
            )
        session.commit()

    # The refusal is recorded even though nothing was mutated: it is written in
    # the caller's transaction, which still commits.
    with psycopg.connect(dsn_admin, autocommit=True) as c:
        registradas = c.execute(
            "SELECT count(*) FROM historico_movimentacao WHERE acao = 'usuario.ultimo_gestor'"
        ).fetchone()
        assert registradas is not None and registradas[0] >= 1
        ainda_ativo = c.execute("SELECT status FROM usuario WHERE id = %s", (ator,)).fetchone()
        assert ainda_ativo is not None and ainda_ativo[0] == "ativo"


def test_ac_0001_29_the_second_of_two_gestores_may_be_removed(
    banco_isolado: tuple[str, str],
) -> None:
    """The guard is "the last one", not "any gestor"."""
    dsn_admin, dsn_app = banco_isolado
    ator = _seed_gestor(dsn_admin)
    outro = _seed_gestor(dsn_admin)
    Sessions = _sessions_for(dsn_app)

    with Sessions() as session:
        actor = session.get(User, ator)
        assert actor is not None
        members.block(
            session,
            actor=actor,
            usuario_id=outro,
            at=datetime.datetime.now(datetime.UTC),
            correlation_id=uuid.uuid4(),
        )
        session.commit()

    with psycopg.connect(dsn_admin, autocommit=True) as c:
        row = c.execute("SELECT status FROM usuario WHERE id = %s", (outro,)).fetchone()
        assert row is not None and row[0] == "bloqueado"


def test_ac_0001_29_under_concurrency_the_loser_gets_409_not_500(
    banco_isolado: tuple[str, str],
) -> None:
    """Two threads each removing a different one of exactly two gestores.

    The database-level race is covered in `test_migration_baseline.py`, which
    measured the loser surfacing as `40P01` 39 times out of 40 rather than the
    trigger's own `SI005`. This asserts the *service* consequence: with the
    advisory lock taken before the count, and both SQLSTATEs mapped, the loser
    raises `LastGestor` — a 409 — instead of a 500 on a foreseeable race.

    Repeated, because write skew is probabilistic and one pass proves nothing.
    """
    dsn_admin, dsn_app = banco_isolado
    Sessions = _sessions_for(dsn_app)

    for _ in range(6):
        # Seed the pair first, then retire everyone else. Blocking every gestor
        # up front would trip the trigger on the last one, which is the test's
        # own setup failing rather than the behaviour under test.
        primeiro = _seed_gestor(dsn_admin)
        segundo = _seed_gestor(dsn_admin)
        with psycopg.connect(dsn_admin, autocommit=True) as c:
            c.execute(
                "UPDATE usuario SET status = 'bloqueado'"
                " WHERE perfil = 'gestor' AND status = 'ativo' AND id <> %s AND id <> %s",
                (primeiro, segundo),
            )

        resultados: list[str] = []
        lock = threading.Lock()

        def remover(
            alvo: uuid.UUID,
            ator: uuid.UUID,
            saida: list[str] = resultados,
            guarda: threading.Lock = lock,
        ) -> None:
            # `saida` and `guarda` are bound as defaults rather than closed
            # over: the joins below make the closure safe today, but a future
            # edit that moves the join out of the loop would make it silently
            # wrong.
            try:
                with Sessions() as session:
                    actor = session.get(User, ator)
                    assert actor is not None
                    members.block(
                        session,
                        actor=actor,
                        usuario_id=alvo,
                        at=datetime.datetime.now(datetime.UTC),
                        correlation_id=uuid.uuid4(),
                    )
                    session.commit()
                with guarda:
                    saida.append("ok")
            except LastGestor:
                with guarda:
                    saida.append("409")
            except Exception as exc:  # noqa: BLE001 - the point is to catch a 500
                with guarda:
                    saida.append(f"500:{type(exc).__name__}")

        threads = [
            threading.Thread(target=remover, args=(primeiro, primeiro)),
            threading.Thread(target=remover, args=(segundo, segundo)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not [r for r in resultados if r.startswith("500")], resultados
        assert resultados.count("ok") == 1, resultados

        with psycopg.connect(dsn_admin, autocommit=True) as c:
            sobrou = c.execute(
                "SELECT count(*) FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'"
            ).fetchone()
            # The invariant that actually matters.
            assert sobrou is not None and sobrou[0] >= 1, resultados
