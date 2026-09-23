"""AC-0001-03 — the lockout, and what it hides.

The criterion has two halves and the second is the one nearly lost: the counter
lives on the **submitted address**, not on the account. In v0.3 it lived on the
account, so an address with no account had no counter — it answered 401 for ever
while a real one switched to 429. Six requests told you which addresses exist,
which is exactly what AC-0001-02 forbids. That is why the threshold test is here.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.secrets_hmac import digest_secret
from app.models.user import User

LOGIN = "/api/v1/auth/login"
PASSWORD = "SenhaCorreta-12345"
WRONG_PASSWORD = "senha-errada-mas-longa"


def _fail(application: TestClient, email: str, times: int) -> None:
    for _ in range(times):
        assert (
            application.post(LOGIN, json={"email": email, "password": WRONG_PASSWORD}).status_code
            == 401
        )


def _age(db_session: Session, email: str, minutes: int) -> None:
    """Wind the row's clock back instead of waiting.

    The window is fifteen minutes; a test that really waits costs fifteen
    minutes and nobody runs it. Moving `ultima_em` and `bloqueado_ate` back
    exercises the same predicate time would.
    """
    db_session.rollback()
    db_session.execute(
        text(
            "UPDATE tentativa_login"
            " SET ultima_em = ultima_em - make_interval(mins => :m),"
            "     bloqueado_ate = bloqueado_ate - make_interval(mins => :m)"
            " WHERE email_hmac = :h"
        ),
        {"m": minutes, "h": digest_secret(email)},
    )
    db_session.commit()


def test_ac_0001_03_blocking_after_repeated_attempts(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-03 the sixth attempt is 429, even with the right password."""
    user = create_user()
    assert user.email
    _fail(application, user.email, 5)

    # The sixth, **with the right password**. A lockout a correct password walks
    # through announces the exact moment the attacker got it right.
    sixth = application.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert sixth.status_code == 429
    error = sixth.json()["error"]
    assert error["code"] == "ATTEMPTS_EXCEEDED"
    assert "minutos" in error["message"]
    # The "when" has to exist outside the pt-BR sentence: a 429 that states the
    # time only inside prose is a 429 no client can obey.
    assert sixth.headers["retry-after"] == "900"

    db_session.rollback()
    attempts = db_session.execute(
        text(
            "SELECT dados_anteriores->>'tentativas' FROM historico_movimentacao"
            " WHERE acao = 'auth.bloqueio_tentativas' AND usuario_id = :uid"
        ),
        {"uid": user.id},
    ).scalar_one()
    assert attempts == "5"

    _age(db_session, user.email, 16)
    released = application.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert released.status_code == 200

    # And success clears the count: the next series starts from zero, or
    # tomorrow's fifth failure would be today's tenth.
    db_session.rollback()
    remaining = db_session.execute(
        text("SELECT count(*) FROM tentativa_login WHERE email_hmac = :h"),
        {"h": digest_secret(user.email)},
    ).scalar_one()
    assert remaining == 0


def test_ac_0001_03_the_window_decays(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """Four old failures plus a new one count as *one*, not five.

    "Five within fifteen minutes" and "five failures, ever" are not the same
    rule. The second locks an account over errors spread across months, which is
    the failure mode `ultima_em` exists to prevent.
    """
    user = create_user()
    assert user.email
    _fail(application, user.email, 4)
    _age(db_session, user.email, 16)

    fifth = application.post(LOGIN, json={"email": user.email, "password": WRONG_PASSWORD})
    assert fifth.status_code == 401

    db_session.rollback()
    count = db_session.execute(
        text("SELECT tentativas, bloqueado_ate FROM tentativa_login WHERE email_hmac = :h"),
        {"h": digest_secret(user.email)},
    ).one()
    assert count.tentativas == 1
    assert count.bloqueado_ate is None
    assert (
        application.post(LOGIN, json={"email": user.email, "password": PASSWORD}).status_code == 200
    )


def test_ac_0001_02_at_the_threshold_the_unknown_answers_the_same(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """The last line of AC-0001-02, and why the counter left the account.

    Counting attempts must not become an oracle: if a real address locks on the
    sixth and an unknown one never locks, counting to six answers the question
    the error message refuses to answer.
    """
    user = create_user()
    assert user.email
    headers = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-00000000c0de"}

    for endereco in (user.email, "naoexiste-nunca@sc.gov.br"):
        _fail(application, endereco, 5)

    real = application.post(
        LOGIN, json={"email": user.email, "password": PASSWORD}, headers=headers
    )
    nonexistent = application.post(
        LOGIN, json={"email": "naoexiste-nunca@sc.gov.br", "password": PASSWORD}, headers=headers
    )

    assert real.status_code == nonexistent.status_code == 429
    assert real.content == nonexistent.content


def test_an_inactive_account_with_the_right_password_records_no_attempt(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """Nobody is guessing: the password was right.

    Counting it would lock out precisely the person about to ask the gestor to
    unblock them, for fifteen minutes per attempt to understand what happened.
    """
    user = create_user(status="bloqueado")
    assert user.email
    for _ in range(6):
        response = application.post(LOGIN, json={"email": user.email, "password": PASSWORD})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "USUARIO_INATIVO"

    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT count(*) FROM tentativa_login WHERE email_hmac = :h"),
            {"h": digest_secret(user.email)},
        ).scalar_one()
        == 0
    )
