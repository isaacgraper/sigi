"""Institutional OIDC — AC-0001-19, -20, -21 and -22.

Fake provider: a key pair generated in the test, JWKS served by a transport, the
`id_token` signed here. It covers a wrong `iss`, `aud` and `exp`, a swapped
nonce and `alg: none` without touching the network, and it is the only way to
exercise any of this before the entity's IT hands over tenant, client and
redirect (OQ-09).
"""

from __future__ import annotations

import datetime
import json
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import oidc

ISSUER = "https://login.exemplo.gov.br/tenant"
CLIENT_ID = "sigi-cliente"
KID = "chave-de-teste"


class FakeProvider:
    """Mints identity tokens and serves the JWKS the verifier fetches."""

    def __init__(self) -> None:
        """Generate this provider's signing key."""
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.id_token = ""

    def jwks(self) -> dict[str, Any]:
        """Serve the public half, in the shape a real provider publishes."""
        numbers = self.private.public_key().public_numbers()

        def to_b64(value: int, size: int) -> str:
            return jwt.utils.base64url_encode(value.to_bytes(size, "big")).decode()

        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": KID,
                    "alg": "RS256",
                    "use": "sig",
                    "n": to_b64(numbers.n, 256),
                    "e": to_b64(numbers.e, 3),
                }
            ]
        }

    def sign(self, **overrides: Any) -> str:
        """Mint an identity token, with any claim overridden for the test."""
        now = datetime.datetime.now(datetime.UTC)
        content: dict[str, Any] = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "subject-estavel-123",
            "email": "ana@sc.gov.br",
            "groups": ["Gestores-TI"],
            "iat": int(now.timestamp()),
            "exp": int((now + datetime.timedelta(minutes=5)).timestamp()),
        }
        content.update(overrides)
        alg = content.pop("__alg", "RS256")
        key = "" if alg == "none" else self.private
        return jwt.encode(content, key, algorithm=alg, headers={"kid": KID})

    def route(self, request: httpx2.Request) -> httpx2.Response:
        """Answer discovery, JWKS and the token exchange."""
        path = request.url.path
        if path.endswith("/.well-known/openid-configuration"):
            return httpx2.Response(
                200,
                json={
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                },
            )
        if path.endswith("/jwks"):
            return httpx2.Response(200, json=self.jwks())
        if path.endswith("/token"):
            return httpx2.Response(200, json={"id_token": self.id_token})
        return httpx2.Response(404)


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeProvider]:
    """A configured provider, with the HTTP client replaced by its transport."""
    from app.core.config import get_settings

    fake = FakeProvider()
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "segredo")
    get_settings.cache_clear()
    monkeypatch.setattr(
        oidc, "client", lambda: httpx2.Client(transport=httpx2.MockTransport(fake.route))
    )
    yield fake
    get_settings.cache_clear()


def _start(application: TestClient) -> tuple[str, str, str]:
    """Hit /authorize and return (state, nonce, the state cookie).

    The nonce matters: a real provider echoes it into the identity token, so the
    fake one has to as well. Without it every token fails the nonce check, and
    the AC-0001-20 cases would pass for that reason instead of the one they
    investigate.
    """
    response = application.get("/api/v1/auth/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302, response.text
    target = httpx2.URL(response.headers["location"])
    cookie = next(
        c.split("=", 1)[1].split(";")[0]
        for c in response.headers.get_list("set-cookie")
        if c.startswith("sigi_oidc_estado=")
    )
    return target.params["state"], target.params["nonce"], cookie


def _callback(application: TestClient, state: str, cookie: str) -> httpx2.Response:
    application.cookies.set("sigi_oidc_estado", cookie)
    response = application.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": state}
    )
    application.cookies.clear()
    return response


def test_ac_0001_19_pkce_state_and_nonce(application: TestClient, provider: FakeProvider) -> None:
    """AC-0001-19 — the redirect carries PKCE S256, state and nonce."""
    response = application.get("/api/v1/auth/oidc/authorize", follow_redirects=False)
    assert response.status_code == 302
    target = httpx2.URL(response.headers["location"])

    assert target.params["response_type"] == "code"
    assert target.params["code_challenge_method"] == "S256"
    assert target.params["code_challenge"]
    assert target.params["state"]
    assert target.params["nonce"]
    assert target.params["client_id"] == CLIENT_ID

    # The verifier never travels in the URL, only the challenge derived from it.
    assert "code_verifier" not in target.params

    raw = next(
        c for c in response.headers.get_list("set-cookie") if c.startswith("sigi_oidc_estado=")
    )
    assert "httponly" in raw.lower()
    assert "max-age=600" in raw.lower()


def test_ac_0001_19_a_state_never_issued_is_refused(
    application: TestClient, provider: FakeProvider
) -> None:
    """AC-0001-19 — a forged state, and a state with no cookie, both answer 401."""
    provider.id_token = provider.sign()

    without_cookie = application.get(
        "/api/v1/auth/oidc/callback", params={"code": "x", "state": "inventado"}
    )
    assert without_cookie.status_code == 401
    assert without_cookie.json()["error"]["code"] == "INVALID_STATE"

    _, _, cookie = _start(application)
    application.cookies.set("sigi_oidc_estado", cookie)
    swapped = application.get(
        "/api/v1/auth/oidc/callback", params={"code": "x", "state": "outro-estado"}
    )
    assert swapped.status_code == 401
    assert swapped.json()["error"]["code"] == "INVALID_STATE"
    application.cookies.clear()


@pytest.mark.parametrize(
    ("label", "overrides"),
    [
        ("wrong-issuer", {"iss": "https://outro-provedor.exemplo"}),
        ("wrong-audience", {"aud": "outro-cliente"}),
        ("expired", {"exp": 1000000000}),
        ("alg-none", {"__alg": "none"}),
    ],
)
def test_ac_0001_20_the_id_token_is_verified(
    application: TestClient,
    provider: FakeProvider,
    sessao: Session,
    label: str,
    overrides: dict[str, Any],
) -> None:
    """AC-0001-20 — signature, issuer, audience, expiry and `alg: none`."""
    state, nonce, cookie = _start(application)
    provider.id_token = provider.sign(nonce=nonce, **overrides)

    response = _callback(application, state, cookie)

    assert response.status_code == 401, f"{label}: {response.text}"
    assert response.json()["error"]["code"] == "INVALID_ASSERTION"

    sessao.rollback()
    refusals = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE acao = 'auth.oidc_recusada'")
    ).scalar_one()
    assert refusals >= 1


def test_ac_0001_20_a_signature_from_another_key(
    application: TestClient, provider: FakeProvider
) -> None:
    """A well-formed token, signed by someone the provider never published."""
    state, nonce, cookie = _start(application)
    intruder = FakeProvider()
    provider.id_token = intruder.sign(nonce=nonce)

    assert _callback(application, state, cookie).status_code == 401


def test_ac_0001_20_a_swapped_nonce(application: TestClient, provider: FakeProvider) -> None:
    """Refuse a token whose nonce belongs to another login.

    Without this check, a token minted for another login of this same person
    would be replayable into this one.
    """
    state, _, cookie = _start(application)
    provider.id_token = provider.sign(nonce="nonce-de-outro-login")

    response = _callback(application, state, cookie)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_ASSERTION"


def test_ac_0001_21_no_just_in_time_provisioning(
    application: TestClient, provider: FakeProvider, sessao: Session
) -> None:
    """AC-0001-21 — a valid assertion with no account: 403, and no row created."""
    sessao.rollback()
    before = sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one()

    state, nonce, cookie = _start(application)
    provider.id_token = provider.sign(nonce=nonce, sub="ninguem-aqui", email="ninguem@sc.gov.br")
    response = _callback(application, state, cookie)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USUARIO_NAO_PROVISIONADO"

    sessao.rollback()
    assert sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one() == before

    # The asserted address is recorded as an HMAC: whoever was refused has no
    # account to anonymise later, and the table can never be corrected.
    row = sessao.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'auth.oidc_recusada' ORDER BY ocorrido_em DESC LIMIT 1"
        )
    ).scalar_one()
    assert "ninguem@sc.gov.br" not in row
    assert "sc.gov.br" in row


@pytest.mark.parametrize("status", ["pendente", "bloqueado", "desativado"])
def test_ac_0001_21_an_inactive_account_does_not_enter(
    application: TestClient,
    provider: FakeProvider,
    criar_usuario: Callable[..., User],
    status: str,
) -> None:
    """An account that exists but is not `ativo` also receives 403."""
    subject = f"sub-{status}-{uuid.uuid4().hex[:6]}"
    email = f"{status}-{uuid.uuid4().hex[:6]}@sc.gov.br"
    criar_usuario(
        email=email,
        status=status,
        senha=None if status == "pendente" else "SenhaCorreta-12345",
    )

    state, nonce, cookie = _start(application)
    provider.id_token = provider.sign(nonce=nonce, sub=subject, email=email)
    response = _callback(application, state, cookie)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USUARIO_NAO_PROVISIONADO"


def test_ac_0001_22_the_perfil_comes_from_the_record(
    application: TestClient,
    provider: FakeProvider,
    criar_usuario: Callable[..., User],
    sessao: Session,
) -> None:
    """AC-0001-22 — the provider asserts "Gestores-TI"; the session is `servidor`."""
    email = f"perfil-{uuid.uuid4().hex[:6]}@sc.gov.br"
    user = criar_usuario(email=email, perfil="servidor")

    state, nonce, cookie = _start(application)
    provider.id_token = provider.sign(nonce=nonce, sub=f"sub-{user.id}", email=email)
    response = _callback(application, state, cookie)

    assert response.status_code == 200, response.text
    access = response.json()["access_token"]
    claims = json.loads(jwt.utils.base64url_decode(access.split(".")[1] + "==").decode())
    assert claims["perfil"] == "servidor"

    sessao.rollback()
    claim = sessao.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'auth.oidc_claim' AND entidade_id = :u"
        ),
        {"u": user.id},
    ).scalar_one()
    # Recorded for the audit trail, and consulted by no decision at all.
    assert "Gestores-TI" in claim
    assert "servidor" in claim


def test_ac_0001_03_oidc_is_not_affected(
    application: TestClient,
    provider: FakeProvider,
    criar_usuario: Callable[..., User],
) -> None:
    """AC-0001-03, last clause — the per-address lockout does not reach OIDC.

    If it did, anyone who knew the last gestor's e-mail could deny member
    management in fifteen-minute blocks, anonymously: the outcome AC-0001-29
    exists to prevent, reached through a route it does not guard.
    """
    email = f"travado-{uuid.uuid4().hex[:6]}@sc.gov.br"
    criar_usuario(email=email, perfil="gestor")

    for _ in range(6):
        application.post(
            "/api/v1/auth/login", json={"email": email, "password": "errada-mas-longa"}
        )
    locked = application.post(
        "/api/v1/auth/login", json={"email": email, "password": "errada-mas-longa"}
    )
    assert locked.status_code == 429

    state, nonce, cookie = _start(application)
    provider.id_token = provider.sign(nonce=nonce, sub=f"sub-{email}", email=email)
    response = _callback(application, state, cookie)

    assert response.status_code == 200, response.text
