"""Local login — SPEC-0001 AC-0001-01, -02, -04, -05, -24.

Against a real database and the assembled application, because most of what
these criteria assert lives at the edges: a cookie's flags, the bytes of an
error body, the absence of a column from a response.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.user import User
from tests.conftest import cookie_from

PASSWORD = "SenhaCorreta-12345"
LOGIN = "/api/v1/auth/login"


def test_ac_0001_01_login_issues_a_token_pair(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-01 — 200, a 15-minute access token, and the refresh only in the cookie."""
    user = create_user()
    response = application.post(LOGIN, json={"email": user.email, "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]

    raw = next(c for c in response.headers.get_list("set-cookie") if c.startswith("sigi_refresh="))
    attributes = {p.strip().split("=")[0].lower() for p in raw.split(";")[1:]}
    assert "httponly" in attributes
    assert "secure" in attributes
    assert "samesite=lax" in raw.lower()
    assert "max-age=604800" in raw.lower()  # 7 dias (RNF03)

    # The refresh value appears nowhere in the body — one that leaks into a log
    # or a screenshot renews a session for seven days.
    value = cookie_from(response, "sigi_refresh")
    assert value and value not in response.text


def test_ac_0001_02_an_identical_answer_for_an_unknown_email(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-02 — a wrong senha and an unknown e-mail answer the same.

    `correlation_id` goes into the envelope and changes per request, so the same
    one is sent on both: without that, "byte-identical" could not be asserted,
    and asserting less here reopens the oracle the criterion closes.
    """
    user = create_user()
    headers = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-00000000beef"}

    wrong = application.post(
        LOGIN,
        json={"email": user.email, "password": "senha-errada-mas-longa"},
        headers=headers,
    )
    nonexistent = application.post(
        LOGIN,
        json={"email": "naoexiste@sc.gov.br", "password": "senha-errada-mas-longa"},
        headers=headers,
    )

    assert wrong.status_code == nonexistent.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong.content == nonexistent.content
    # And neither the body nor the headers may say "this e-mail exists".
    assert "existe" not in wrong.text.lower().replace("inexistente", "")


def test_ac_0001_04_a_domain_outside_the_allowlist(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-04 — an address off the institutional domains does not authenticate.

    Even with the right senha and an active account: the record exists, the
    domain is what is refused — and the response is indistinguishable from a
    wrong senha.
    """
    user = create_user(email="alguem@gmail.com")
    headers = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-0000000000aa"}

    outside = application.post(
        LOGIN, json={"email": user.email, "password": PASSWORD}, headers=headers
    )
    wrong = application.post(
        LOGIN, json={"email": "outro@sc.gov.br", "password": PASSWORD}, headers=headers
    )

    assert outside.status_code == 401
    assert outside.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert outside.content == wrong.content


def test_ac_0001_05_the_hash_never_leaves_the_database(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-05 — bcrypt cost >= 12, and the hash leaves by no route."""
    user = create_user()
    assert user.senha_hash is not None
    prefix, cost = user.senha_hash.split("$")[1], user.senha_hash.split("$")[2]
    assert prefix in ("2a", "2b", "2y")
    assert int(cost) >= 12

    entry = application.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    me_response = application.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {entry.json()['access_token']}"},
    )

    assert me_response.status_code == 200
    assert set(me_response.json()) == {"id", "name", "email", "perfil", "status"}
    for response in (entry, me_response):
        assert user.senha_hash not in response.text
        assert "password" not in response.text.lower()


def test_ac_0001_24_local_login_can_be_turned_off(
    application: TestClient,
    create_user: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0001-24 — switched off by configuration, the route answers 404.

    404 and not 403: a mechanism that is off should be indistinguishable from
    one that was never built, or the refusal itself confirms it is there.
    """
    user = create_user()
    monkeypatch.setenv("LOCAL_LOGIN_ENABLED", "false")
    get_settings.cache_clear()

    turned_off = application.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert turned_off.status_code == 404
    assert turned_off.json()["error"]["code"] == "NOT_FOUND"

    monkeypatch.setenv("LOCAL_LOGIN_ENABLED", "true")
    get_settings.cache_clear()
    assert (
        application.post(LOGIN, json={"email": user.email, "password": PASSWORD}).status_code == 200
    )


def test_a_malformed_body_uses_the_same_envelope(application: TestClient) -> None:
    """A malformed body uses the same error envelope as everything else.

    `api-conventions.md` says an error always has one shape. FastAPI's default
    422 has another, and a client that must understand two understands neither.
    """
    response = application.post(LOGIN, json={"email": "nao-e-email", "password": ""})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert set(error["fields"]) == {"email", "password"}
    assert error["correlation_id"]
