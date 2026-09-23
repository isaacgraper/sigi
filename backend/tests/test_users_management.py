"""Member management — AC-0001-12, -13, -14, -15, -29.

The API-level cases run against the shared test database, which already holds
other active gestores, so blocking one never trips the last-gestor guard. The
guard itself is a property of the whole table, so its tests take
`isolated_database`.
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
# Not `*_PASSWORD`: gitleaks reads that keyword beside this entropy as a
# credential. See `docs/process/sop-qualidade.md`.
LONG_ENOUGH = "SenhaLongaOSuficiente-2026"


def _as_gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    email = f"gestor-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil="gestor", password=LONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH})
    assert entry.status_code == 200, entry.text
    return {"Authorization": f"Bearer {entry.json()['access_token']}"}


def test_ac_0001_12_a_gestor_blocks_an_account(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-12 — the account is blocked and its sessions are revoked."""
    headers = _as_gestor(application, create_user)
    target = create_user(email=f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", password=LONG_ENOUGH)

    # The target has a live session, so there is something to revoke.
    entry = application.post(LOGIN, json={"email": target.email, "password": LONG_ENOUGH})
    assert entry.status_code == 200
    target_token = entry.json()["access_token"]

    response = application.post(f"{USUARIOS}/{target.id}/bloquear", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "bloqueado"

    # The unexpired access token stops working at once, because `ativo` is
    # checked on every request rather than at login (AC-0001-08).
    me_response = application.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {target_token}"}
    )
    assert me_response.status_code == 401

    db_session.rollback()
    motivo = db_session.execute(
        text("SELECT revogado_motivo FROM sessao WHERE usuario_id = :u"), {"u": target.id}
    ).scalar_one()
    # The session vocabulary, not the account's: `ck_sessao_motivo_valor` fixes
    # this list and "bloqueado" is not in it.
    assert motivo == "bloqueio"


def test_ac_0001_14_deactivation_anonymises_and_keeps_the_history(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-14, RN16 — identifying fields go, the record of what they did stays."""
    headers = _as_gestor(application, create_user)
    target = create_user(
        email=f"anon-{uuid.uuid4().hex[:8]}@sc.gov.br", name="Pessoa Real", password=LONG_ENOUGH
    )
    target_id = target.id

    response = application.post(f"{USUARIOS}/{target_id}/desativar", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "desativado"
    assert body["name"] is None
    assert body["email"] is None
    # The column is `pseudonimo` and the payload field is `pseudonym`: they have
    # different readers, so they need not match (ADR-0013). It is generated, so
    # the trail keeps resolving to one stable name without the history being
    # rewritten, which AC-0001-27 forbids anyway.
    assert body["pseudonym"]

    db_session.rollback()
    row = db_session.execute(
        text(
            "SELECT nome, email, senha_hash, oidc_subject, anonimizado_em"
            " FROM usuario WHERE id = :u"
        ),
        {"u": target_id},
    ).one()
    assert row.nome is None
    assert row.email is None
    assert row.senha_hash is None
    assert row.oidc_subject is None
    assert row.anonimizado_em is not None

    # The audit rows this person generated are still there and still attributable.
    still = db_session.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE entidade_id = :u"),
        {"u": target_id},
    ).scalar_one()
    assert still >= 1


def test_deactivating_removes_the_credential_so_login_stops(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """Anonymisation nulls `senha_hash`, so the old password is no longer a way in."""
    headers = _as_gestor(application, create_user)
    email = f"nologin-{uuid.uuid4().hex[:8]}@sc.gov.br"
    target = create_user(email=email, password=LONG_ENOUGH)

    application.post(f"{USUARIOS}/{target.id}/desativar", headers=headers)

    assert (
        application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH}).status_code == 401
    )


def test_ac_0001_15_a_gestor_lists_members(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-15 — the page envelope is the one `api-conventions.md` fixes."""
    headers = _as_gestor(application, create_user)
    create_user(email=f"lista-{uuid.uuid4().hex[:8]}@sc.gov.br", password=LONG_ENOUGH)

    response = application.get(USUARIOS, params={"page": 1, "size": 5}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["size"] == 5
    assert len(body["items"]) <= 5
    assert body["total"] >= 1


def test_paging_never_repeats_a_row(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """The order is `criado_em DESC, id`, so pages do not overlap.

    `criado_em` alone is not unique enough: two invitations in the same
    millisecond would order arbitrarily between the two queries.
    """
    headers = _as_gestor(application, create_user)
    for _ in range(4):
        create_user(email=f"pag-{uuid.uuid4().hex[:8]}@sc.gov.br", password=LONG_ENOUGH)

    first_page = application.get(USUARIOS, params={"page": 1, "size": 2}, headers=headers).json()
    second_page = application.get(USUARIOS, params={"page": 2, "size": 2}, headers=headers).json()

    ids_one = {item["id"] for item in first_page["items"]}
    ids_two = {item["id"] for item in second_page["items"]}
    assert ids_one and ids_two
    assert ids_one.isdisjoint(ids_two)


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_13_a_servidor_or_auditor_cannot_manage_members(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> None:
    """AC-0001-13 — managing members refuses a non-gestor.

    Managing, not reading. This test used to include `GET /usuarios` and assert
    403 for both perfis, which contradicted SPEC-0001 §6: the matrix grants the
    member list to "auditor ✅ read-only". The test was asserting the bug, so it
    kept the bug alive. The read is checked separately below.
    """
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil=perfil, password=LONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH})
    headers = {"Authorization": f"Bearer {entry.json()['access_token']}"}
    target = create_user(email=f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", password=LONG_ENOUGH)

    for response in (
        application.post(f"{USUARIOS}/{target.id}/bloquear", headers=headers),
        application.post(f"{USUARIOS}/{target.id}/desativar", headers=headers),
        application.post(f"{USUARIOS}/{target.id}/redefinir-senha", headers=headers),
    ):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


def test_ac_0001_17_an_auditor_reads_the_member_list_and_a_servidor_does_not(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """SPEC-0001 §6 — the member list is the auditor's one member route.

    An auditor who cannot open the member list cannot resolve the actor column
    of any audit row, which is the job the perfil exists for.
    """
    for perfil, expected in (("auditor", 200), ("servidor", 403)):
        email = f"{perfil}-lista-{uuid.uuid4().hex[:8]}@sc.gov.br"
        create_user(email=email, perfil=perfil, password=LONG_ENOUGH)
        entry = application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH})
        headers = {"Authorization": f"Bearer {entry.json()['access_token']}"}

        response = application.get(USUARIOS, headers=headers)
        assert response.status_code == expected, f"{perfil}: {response.text}"


def test_an_unknown_id_is_404(application: TestClient, create_user: Callable[..., User]) -> None:
    """A gestor acting on an id that does not exist."""
    headers = _as_gestor(application, create_user)
    response = application.post(f"{USUARIOS}/{uuid.uuid4()}/bloquear", headers=headers)
    assert response.status_code == 404


def test_blocking_an_already_blocked_account_is_idempotent(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """No second audit row, and no error: the status is already what was asked for."""
    headers = _as_gestor(application, create_user)
    target = create_user(email=f"idem-{uuid.uuid4().hex[:8]}@sc.gov.br", password=LONG_ENOUGH)

    first = application.post(f"{USUARIOS}/{target.id}/bloquear", headers=headers)
    second = application.post(f"{USUARIOS}/{target.id}/bloquear", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "bloqueado"


# ── The last active gestor (AC-0001-29) ─────────────────────────────────────
#
# A property of the whole table, so these take a database of their own.


def _sessions_for(dsn: str) -> sessionmaker[Session]:
    # The fixtures hand out libpq keyword strings, not URLs. `conftest` already
    # converts; a second converter here is a second thing to keep in step.
    from tests.conftest import _to_sqlalchemy

    return sessionmaker(bind=create_engine(_to_sqlalchemy(dsn)))


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
    isolated_database: tuple[str, str],
) -> None:
    """AC-0001-29 — refused with the criterion's own error, not a 500.

    Blocking the only active gestor locks the entity out of its own member
    management, with no path back that does not involve database access.
    """
    dsn_admin, dsn_app = isolated_database
    ator = _seed_gestor(dsn_admin)
    Sessions = _sessions_for(dsn_app)

    with Sessions() as session:
        actor = session.get(User, ator)
        assert actor is not None
        with pytest.raises(LastGestor):
            members.block(
                session,
                actor=actor,
                user_id=ator,
                at=datetime.datetime.now(datetime.UTC),
                correlation_id=uuid.uuid4(),
            )
        session.commit()

    # The refusal is recorded even though nothing was mutated: it is written in
    # the caller's transaction, which still commits.
    with psycopg.connect(dsn_admin, autocommit=True) as c:
        recorded_rows = c.execute(
            "SELECT count(*) FROM historico_movimentacao WHERE acao = 'usuario.ultimo_gestor'"
        ).fetchone()
        assert recorded_rows is not None and recorded_rows[0] >= 1
        still_active = c.execute("SELECT status FROM usuario WHERE id = %s", (ator,)).fetchone()
        assert still_active is not None and still_active[0] == "ativo"


def test_ac_0001_29_the_second_of_two_gestores_may_be_removed(
    isolated_database: tuple[str, str],
) -> None:
    """The guard is "the last one", not "any gestor"."""
    dsn_admin, dsn_app = isolated_database
    ator = _seed_gestor(dsn_admin)
    other = _seed_gestor(dsn_admin)
    Sessions = _sessions_for(dsn_app)

    with Sessions() as session:
        actor = session.get(User, ator)
        assert actor is not None
        members.block(
            session,
            actor=actor,
            user_id=other,
            at=datetime.datetime.now(datetime.UTC),
            correlation_id=uuid.uuid4(),
        )
        session.commit()

    with psycopg.connect(dsn_admin, autocommit=True) as c:
        row = c.execute("SELECT status FROM usuario WHERE id = %s", (other,)).fetchone()
        assert row is not None and row[0] == "bloqueado"


def test_ac_0001_29_under_concurrency_the_loser_gets_409_not_500(
    isolated_database: tuple[str, str],
) -> None:
    """Two threads each removing a different one of exactly two gestores.

    The database-level race is covered in `test_migration_baseline.py`, which
    measured the loser surfacing as `40P01` 39 times out of 40 rather than the
    trigger's own `SI005`. This asserts the *service* consequence: with the
    advisory lock taken before the count, and both SQLSTATEs mapped, the loser
    raises `LastGestor` — a 409 — instead of a 500 on a foreseeable race.

    Repeated, because write skew is probabilistic and one pass proves nothing.
    """
    dsn_admin, dsn_app = isolated_database
    Sessions = _sessions_for(dsn_app)

    for _ in range(6):
        # Seed the pair first, then retire everyone else. Blocking every gestor
        # up front would trip the trigger on the last one, which is the test's
        # own setup failing rather than the behaviour under test.
        first = _seed_gestor(dsn_admin)
        second = _seed_gestor(dsn_admin)
        with psycopg.connect(dsn_admin, autocommit=True) as c:
            c.execute(
                "UPDATE usuario SET status = 'bloqueado'"
                " WHERE perfil = 'gestor' AND status = 'ativo' AND id <> %s AND id <> %s",
                (first, second),
            )

        results: list[str] = []
        lock = threading.Lock()

        def remove(
            target: uuid.UUID,
            ator: uuid.UUID,
            output: list[str] = results,
            guard: threading.Lock = lock,
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
                        user_id=target,
                        at=datetime.datetime.now(datetime.UTC),
                        correlation_id=uuid.uuid4(),
                    )
                    session.commit()
                with guard:
                    output.append("ok")
            except LastGestor:
                with guard:
                    output.append("409")
            except Exception as exc:  # noqa: BLE001 - the point is to catch a 500
                with guard:
                    output.append(f"500:{type(exc).__name__}")

        threads = [
            threading.Thread(target=remove, args=(first, first)),
            threading.Thread(target=remove, args=(second, second)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not [r for r in results if r.startswith("500")], results
        assert results.count("ok") == 1, results

        with psycopg.connect(dsn_admin, autocommit=True) as c:
            left_over = c.execute(
                "SELECT count(*) FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'"
            ).fetchone()
            # The invariant that actually matters.
            assert left_over is not None and left_over[0] >= 1, results
