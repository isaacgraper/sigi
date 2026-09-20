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

SENHA = "SenhaCorreta-12345"
LOGIN = "/api/v1/auth/login"


def test_ac_0001_01_login_emite_par_de_tokens(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-01 — 200, a 15-minute access token, and the refresh only in the cookie."""
    usuario = criar_usuario()
    response = application.post(LOGIN, json={"email": usuario.email, "password": SENHA})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]

    bruto = next(
        c for c in response.headers.get_list("set-cookie") if c.startswith("sigi_refresh=")
    )
    atributos = {p.strip().split("=")[0].lower() for p in bruto.split(";")[1:]}
    assert "httponly" in atributos
    assert "secure" in atributos
    assert "samesite=lax" in bruto.lower()
    assert "max-age=604800" in bruto.lower()  # 7 dias (RNF03)

    # The refresh value appears nowhere in the body — one that leaks into a log
    # or a screenshot renews a session for seven days.
    valor = cookie_from(response, "sigi_refresh")
    assert valor and valor not in response.text


def test_ac_0001_02_resposta_identica_para_email_inexistente(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-02 — a wrong senha and an unknown e-mail answer the same.

    `correlation_id` goes into the envelope and changes per request, so the same
    one is sent on both: without that, "byte-identical" could not be asserted,
    and asserting less here reopens the oracle the criterion closes.
    """
    usuario = criar_usuario()
    headers = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-00000000beef"}

    errada = application.post(
        LOGIN,
        json={"email": usuario.email, "password": "senha-errada-mas-longa"},
        headers=headers,
    )
    inexistente = application.post(
        LOGIN,
        json={"email": "naoexiste@sc.gov.br", "password": "senha-errada-mas-longa"},
        headers=headers,
    )

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert errada.content == inexistente.content
    # And neither the body nor the headers may say "this e-mail exists".
    assert "existe" not in errada.text.lower().replace("inexistente", "")


def test_ac_0001_04_dominio_fora_da_allowlist(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-04 — an address off the institutional domains does not authenticate.

    Even with the right senha and an active account: the record exists, the
    domain is what is refused — and the response is indistinguishable from a
    wrong senha.
    """
    usuario = criar_usuario(email="alguem@gmail.com")
    headers = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-0000000000aa"}

    fora = application.post(
        LOGIN, json={"email": usuario.email, "password": SENHA}, headers=headers
    )
    errada = application.post(
        LOGIN, json={"email": "outro@sc.gov.br", "password": SENHA}, headers=headers
    )

    assert fora.status_code == 401
    assert fora.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert fora.content == errada.content


def test_ac_0001_05_hash_nunca_sai_do_banco(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-05 — bcrypt cost >= 12, and the hash leaves by no route."""
    usuario = criar_usuario()
    assert usuario.senha_hash is not None
    prefixo, custo = usuario.senha_hash.split("$")[1], usuario.senha_hash.split("$")[2]
    assert prefixo in ("2a", "2b", "2y")
    assert int(custo) >= 12

    entrada = application.post(LOGIN, json={"email": usuario.email, "password": SENHA})
    eu = application.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {entrada.json()['access_token']}"},
    )

    assert eu.status_code == 200
    assert set(eu.json()) == {"id", "name", "email", "perfil", "status"}
    for response in (entrada, eu):
        assert usuario.senha_hash not in response.text
        assert "password" not in response.text.lower()


def test_ac_0001_24_login_local_desligavel(
    application: TestClient,
    criar_usuario: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0001-24 — switched off by configuration, the route answers 404.

    404 and not 403: a mechanism that is off should be indistinguishable from
    one that was never built, or the refusal itself confirms it is there.
    """
    usuario = criar_usuario()
    monkeypatch.setenv("LOCAL_LOGIN_ENABLED", "false")
    get_settings.cache_clear()

    desligado = application.post(LOGIN, json={"email": usuario.email, "password": SENHA})
    assert desligado.status_code == 404
    assert desligado.json()["error"]["code"] == "NOT_FOUND"

    monkeypatch.setenv("LOCAL_LOGIN_ENABLED", "true")
    get_settings.cache_clear()
    assert (
        application.post(LOGIN, json={"email": usuario.email, "password": SENHA}).status_code == 200
    )


def test_corpo_malformado_usa_o_mesmo_envelope(application: TestClient) -> None:
    """A malformed body uses the same error envelope as everything else.

    `api-conventions.md` says an error always has one shape. FastAPI's default
    422 has another, and a client that must understand two understands neither.
    """
    response = application.post(LOGIN, json={"email": "nao-e-email", "password": ""})
    assert response.status_code == 422
    erro = response.json()["error"]
    assert erro["code"] == "INVALID_DATA"
    assert set(erro["fields"]) == {"email", "password"}
    assert erro["correlation_id"]
