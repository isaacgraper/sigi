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
from app.services.erros import AssercaoInvalida, EstadoInvalido

ALGORITMOS_ACEITOS = ["RS256"]
TIPO_ESTADO = "oidc_estado"


@dataclass(frozen=True)
class PedidoDeAutorizacao:
    """What `/authorize` hands back: where to send the caller, and what to keep."""

    url: str
    estado_assinado: str
    """Signed blob for the cookie. Carries state, the PKCE verifier and the nonce."""


@dataclass(frozen=True)
class Assercao:
    """A verified identity token, reduced to what SIGI uses."""

    subject: str
    email: str | None
    grupo_asserido: str | None


def cliente() -> httpx2.Client:
    """The HTTP client used for discovery, JWKS and the token exchange.

    A function rather than a module constant so tests can replace it with a
    transport and never open a socket.
    """
    return httpx2.Client(timeout=10.0)


def iniciar(*, now: datetime.datetime) -> PedidoDeAutorizacao:
    """Build the authorization redirect and the state to remember (AC-0001-19).

    The state, the PKCE verifier and the nonce live in a signed, short-lived
    blob rather than a table. It is bound to the caller because it travels in an
    httpOnly cookie, and it expires because the signature carries `exp` — so
    there are no expired rows to sweep and no state store to keep consistent.
    """
    cfg = get_settings()
    estado = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )

    params = {
        "response_type": "code",
        "client_id": cfg.oidc_client_id,
        "redirect_uri": cfg.oidc_redirect_uri,
        "scope": "openid email profile",
        "state": estado,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    endpoints = _descobrir()
    url = str(httpx2.URL(endpoints["authorization_endpoint"]).copy_merge_params(params))

    return PedidoDeAutorizacao(
        url=url, estado_assinado=_assinar_estado(estado, nonce, verifier, now)
    )


def concluir(
    *, codigo: str, estado_recebido: str, estado_assinado: str | None, now: datetime.datetime
) -> Assercao:
    """Exchange the code and verify the assertion (AC-0001-19, -20).

    Raises before any database work: nothing about the caller is looked up until
    the provider's token has verified.
    """
    estado, nonce, verifier = _ler_estado(estado_assinado)
    if not secrets.compare_digest(estado, estado_recebido):
        raise EstadoInvalido()

    id_token = _trocar_codigo(codigo, verifier)
    return _verificar(id_token, nonce=nonce, now=now)


def _assinar_estado(estado: str, nonce: str, verifier: str, now: datetime.datetime) -> str:
    from app.core.seguranca import _par_de_chaves

    cfg = get_settings()
    expira = now + datetime.timedelta(minutes=cfg.oidc_estado_ttl_minutos)
    return jwt.encode(
        {
            "typ": TIPO_ESTADO,
            "iss": cfg.jwt_issuer,
            "estado": estado,
            "nonce": nonce,
            "verifier": verifier,
            "iat": int(now.timestamp()),
            "exp": int(expira.timestamp()),
        },
        _par_de_chaves()[0],
        algorithm="RS256",
    )


def _ler_estado(assinado: str | None) -> tuple[str, str, str]:
    """Open the signed state, or refuse.

    A state that was never issued fails the signature; one that sat too long
    fails `exp`. AC-0001-19 wants both answered the same way, and they are.
    """
    from app.core.seguranca import _par_de_chaves

    if not assinado:
        raise EstadoInvalido()
    cfg = get_settings()
    try:
        payload = jwt.decode(
            assinado,
            _par_de_chaves()[1],
            algorithms=ALGORITMOS_ACEITOS,
            issuer=cfg.jwt_issuer,
            options={"require": ["exp", "iat", "iss"]},
        )
    except jwt.InvalidTokenError as exc:
        raise EstadoInvalido() from exc
    if payload.get("typ") != TIPO_ESTADO:
        raise EstadoInvalido()
    return payload["estado"], payload["nonce"], payload["verifier"]


def _descobrir() -> dict[str, Any]:
    cfg = get_settings()
    url = f"{cfg.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
    with cliente() as c:
        response = c.get(url)
        response.raise_for_status()
        dados: dict[str, Any] = response.json()
    return dados


def _trocar_codigo(codigo: str, verifier: str) -> str:
    cfg = get_settings()
    endpoints = _descobrir()
    with cliente() as c:
        response = c.post(
            endpoints["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": codigo,
                "redirect_uri": cfg.oidc_redirect_uri,
                "client_id": cfg.oidc_client_id,
                "client_secret": cfg.oidc_client_secret,
                "code_verifier": verifier,
            },
        )
    if response.status_code != 200:
        raise AssercaoInvalida()
    body = response.json()
    id_token = body.get("id_token")
    if not isinstance(id_token, str):
        raise AssercaoInvalida()
    return id_token


def _chave_para(id_token: str) -> Any:
    """Fetch the provider's key matching this token's `kid`."""
    endpoints = _descobrir()
    with cliente() as c:
        response = c.get(endpoints["jwks_uri"])
        response.raise_for_status()
        jwks = response.json()

    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except jwt.InvalidTokenError as exc:
        raise AssercaoInvalida() from exc

    for chave in jwks.get("keys", []):
        if kid is None or chave.get("kid") == kid:
            return jwt.PyJWK(chave).key
    raise AssercaoInvalida()


def _verificar(id_token: str, *, nonce: str, now: datetime.datetime) -> Assercao:
    """Verify signature, issuer, audience, expiry and nonce (AC-0001-20).

    `algorithms` is pinned, which is what makes `alg: none` fail rather than be
    trusted — the same reason it is pinned for our own access tokens.
    """
    cfg = get_settings()
    try:
        payload = jwt.decode(
            id_token,
            _chave_para(id_token),
            algorithms=ALGORITMOS_ACEITOS,
            audience=cfg.oidc_client_id,
            issuer=cfg.oidc_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise AssercaoInvalida() from exc

    if not secrets.compare_digest(str(payload.get("nonce", "")), nonce):
        # Without this a token minted for another login of the same user would
        # be replayable into this one.
        raise AssercaoInvalida()

    grupo = payload.get(cfg.oidc_claim_grupo)
    if isinstance(grupo, list):
        grupo = grupo[0] if grupo else None

    return Assercao(
        subject=str(payload["sub"]),
        email=payload.get("email"),
        grupo_asserido=str(grupo) if grupo is not None else None,
    )


def digerir_para_auditoria(valor: str | None) -> str | None:
    """HMAC of an asserted address, for the audit row.

    AC-0001-21 records a refusal for a caller who by definition has no usuario,
    so there is no account to anonymise later and the history can never be
    corrected. The address itself must not go in (SPEC-0001 §8).
    """
    if not valor:
        return None
    from app.core.segredos import digest_secret

    return digest_secret(valor).hex()


def uuid_nulo() -> uuid.UUID:
    """Entity id for an audit row about a caller with no account."""
    return uuid.UUID(int=0)
