"""Institutional OIDC (SPEC-0001 §4.4 — AC-0001-19 to -22, ADR-0010).

Two rules shape everything here. Authentication never creates an account
(AC-0001-21): the provider says who the caller is, and the account has to
already exist because a gestor invited it. And the perfil comes from the usuario
record, never from a claim (AC-0001-22) — a directory edit must not escalate
privilege in a system whose purpose is an auditable trail.

Not `PyJWKClient`, although it ships with PyJWT: it fetches JWKS with `urllib`,
which would force the tests' fake provider to bind a real socket instead of
being a transport. Fetching through the injected client keeps the provider a
fixture and the `kid` cache under explicit control.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import httpx2
import jwt

from app.core.config import get_settings
from app.services.errors import InvalidAssertion, InvalidState

ACCEPTED_ALGORITHMS = ["RS256"]
STATE_TYPE = "oidc_estado"


@dataclass(frozen=True)
class AuthorizationRequest:
    """What `/authorize` hands back: where to send the caller, and what to keep."""

    url: str
    signed_state: str
    """Signed blob for the cookie. Carries state, the PKCE verifier and the nonce."""


@dataclass(frozen=True)
class Assertion:
    """A verified identity token, reduced to what SIGI uses."""

    subject: str
    email: str | None
    asserted_group: str | None


def client() -> httpx2.Client:
    """Build the HTTP client used for discovery, JWKS and the token exchange.

    A function rather than a module constant so tests can replace it with a
    transport and never open a socket.
    """
    return httpx2.Client(timeout=10.0)


def start(*, now: datetime.datetime) -> AuthorizationRequest:
    """Build the authorization redirect and the state to remember (AC-0001-19).

    The state, the PKCE verifier and the nonce live in a signed, short-lived
    blob rather than a table. It is bound to the caller because it travels in an
    httpOnly cookie, and it expires because the signature carries `exp` — so
    there are no expired rows to sweep and no state store to keep consistent.
    """
    cfg = get_settings()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )

    parameters = {
        "response_type": "code",
        "client_id": cfg.oidc_client_id,
        "redirect_uri": cfg.oidc_redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    endpoints = _discover()
    url = str(httpx2.URL(endpoints["authorization_endpoint"]).copy_merge_params(parameters))

    return AuthorizationRequest(url=url, signed_state=_sign_state(state, nonce, verifier, now))


def finish(
    *, code: str, received_state: str, signed_state: str | None, now: datetime.datetime
) -> Assertion:
    """Exchange the code and verify the assertion (AC-0001-19, -20).

    Raises before any database work: nothing about the caller is looked up until
    the provider's token has verified.
    """
    state, nonce, verifier = _read_state(signed_state)
    if not secrets.compare_digest(state, received_state):
        raise InvalidState()

    id_token = _exchange_code(code, verifier)
    return _verify(id_token, nonce=nonce, now=now)


def _sign_state(state: str, nonce: str, verifier: str, now: datetime.datetime) -> str:
    from app.core.security import _key_pair

    cfg = get_settings()
    expires = now + datetime.timedelta(minutes=cfg.oidc_estado_ttl_minutos)
    return jwt.encode(
        {
            "typ": STATE_TYPE,
            "iss": cfg.jwt_issuer,
            "estado": state,
            "nonce": nonce,
            "verificador": verifier,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        },
        _key_pair()[0],
        algorithm="RS256",
    )


def _read_state(signed: str | None) -> tuple[str, str, str]:
    """Open the signed state, or refuse.

    A state that was never issued fails the signature; one that sat too long
    fails `exp`. AC-0001-19 wants both answered the same way, and they are.
    """
    from app.core.security import _key_pair

    if not signed:
        raise InvalidState()
    cfg = get_settings()
    try:
        content = jwt.decode(
            signed,
            _key_pair()[1],
            algorithms=ACCEPTED_ALGORITHMS,
            issuer=cfg.jwt_issuer,
            options={"require": ["exp", "iat", "iss"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidState() from exc
    if content.get("typ") != STATE_TYPE:
        raise InvalidState()
    return content["estado"], content["nonce"], content["verificador"]


def _discover() -> dict[str, Any]:
    cfg = get_settings()
    url = f"{cfg.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
    with client() as c:
        response = c.get(url)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    return data


def _exchange_code(code: str, verifier: str) -> str:
    cfg = get_settings()
    endpoints = _discover()
    with client() as c:
        response = c.post(
            endpoints["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg.oidc_redirect_uri,
                "client_id": cfg.oidc_client_id,
                "client_secret": cfg.oidc_client_secret,
                "code_verifier": verifier,
            },
        )
    if response.status_code != 200:
        raise InvalidAssertion()
    body = response.json()
    id_token = body.get("id_token")
    if not isinstance(id_token, str):
        raise InvalidAssertion()
    return id_token


def _key_for(id_token: str) -> Any:
    """Fetch the provider's key matching this token's `kid`."""
    endpoints = _discover()
    with client() as c:
        response = c.get(endpoints["jwks_uri"])
        response.raise_for_status()
        jwks = response.json()

    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except jwt.InvalidTokenError as exc:
        raise InvalidAssertion() from exc

    for key in jwks.get("keys", []):
        if kid is None or key.get("kid") == kid:
            return jwt.PyJWK(key).key
    raise InvalidAssertion()


def _verify(id_token: str, *, nonce: str, now: datetime.datetime) -> Assertion:
    """Verify signature, issuer, audience, expiry and nonce (AC-0001-20).

    `algorithms` is pinned, which is what makes `alg: none` fail rather than be
    trusted — the same reason it is pinned for our own access tokens.
    """
    cfg = get_settings()
    try:
        content = jwt.decode(
            id_token,
            _key_for(id_token),
            algorithms=ACCEPTED_ALGORITHMS,
            audience=cfg.oidc_client_id,
            issuer=cfg.oidc_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidAssertion() from exc

    if not secrets.compare_digest(str(content.get("nonce", "")), nonce):
        # Without this a token minted for another login of the same user would
        # be replayable into this one.
        raise InvalidAssertion()

    group = content.get(cfg.oidc_claim_grupo)
    if isinstance(group, list):
        group = group[0] if group else None

    return Assertion(
        subject=str(content["sub"]),
        email=content.get("email"),
        asserted_group=str(group) if group is not None else None,
    )


def digest_for_audit(value: str | None) -> str | None:
    """HMAC an asserted address, for the audit row.

    AC-0001-21 records a refusal for a caller who by definition has no usuario,
    so there is no account to anonymise later and the history can never be
    corrected. The address itself must not go in (SPEC-0001 §8).
    """
    if not value:
        return None
    from app.core.secrets_hmac import digest_secret

    return digest_secret(value).hex()


def null_uuid() -> uuid.UUID:
    """Return the entity id used for an audit row about a caller with no account."""
    return uuid.UUID(int=0)
