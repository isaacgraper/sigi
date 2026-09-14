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


def iniciar(*, agora: datetime.datetime) -> PedidoDeAutorizacao:
    """Build the authorization redirect and the state to remember (AC-0001-19).

    The state, the PKCE verifier and the nonce live in a signed, short-lived
    blob rather than a table. It is bound to the caller because it travels in an
    httpOnly cookie, and it expires because the signature carries `exp` — so
    there are no expired rows to sweep and no state store to keep consistent.
    """
    cfg = get_settings()
    estado = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verificador = secrets.token_urlsafe(64)
    desafio = (
        base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).decode().rstrip("=")
    )

    parametros = {
        "response_type": "code",
        "client_id": cfg.oidc_client_id,
        "redirect_uri": cfg.oidc_redirect_uri,
        "scope": "openid email profile",
        "state": estado,
        "nonce": nonce,
        "code_challenge": desafio,
        "code_challenge_method": "S256",
    }
    endpoints = _descobrir()
    url = str(httpx2.URL(endpoints["authorization_endpoint"]).copy_merge_params(parametros))

    return PedidoDeAutorizacao(
        url=url, estado_assinado=_assinar_estado(estado, nonce, verificador, agora)
    )


def concluir(
    *, codigo: str, estado_recebido: str, estado_assinado: str | None, agora: datetime.datetime
) -> Assercao:
    """Exchange the code and verify the assertion (AC-0001-19, -20).

    Raises before any database work: nothing about the caller is looked up until
    the provider's token has verified.
    """
    estado, nonce, verificador = _ler_estado(estado_assinado)
    if not secrets.compare_digest(estado, estado_recebido):
        raise EstadoInvalido()

    id_token = _trocar_codigo(codigo, verificador)
    return _verificar(id_token, nonce=nonce, agora=agora)


def _assinar_estado(estado: str, nonce: str, verificador: str, agora: datetime.datetime) -> str:
    from app.core.seguranca import _par_de_chaves

    cfg = get_settings()
    expira = agora + datetime.timedelta(minutes=cfg.oidc_estado_ttl_minutos)
    return jwt.encode(
        {
            "typ": TIPO_ESTADO,
            "iss": cfg.jwt_issuer,
            "estado": estado,
            "nonce": nonce,
            "verificador": verificador,
            "iat": int(agora.timestamp()),
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
        conteudo = jwt.decode(
            assinado,
            _par_de_chaves()[1],
            algorithms=ALGORITMOS_ACEITOS,
            issuer=cfg.jwt_issuer,
            options={"require": ["exp", "iat", "iss"]},
        )
    except jwt.InvalidTokenError as exc:
        raise EstadoInvalido() from exc
    if conteudo.get("typ") != TIPO_ESTADO:
        raise EstadoInvalido()
    return conteudo["estado"], conteudo["nonce"], conteudo["verificador"]


def _descobrir() -> dict[str, Any]:
    cfg = get_settings()
    url = f"{cfg.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
    with cliente() as c:
        resposta = c.get(url)
        resposta.raise_for_status()
        dados: dict[str, Any] = resposta.json()
    return dados


def _trocar_codigo(codigo: str, verificador: str) -> str:
    cfg = get_settings()
    endpoints = _descobrir()
    with cliente() as c:
        resposta = c.post(
            endpoints["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": codigo,
                "redirect_uri": cfg.oidc_redirect_uri,
                "client_id": cfg.oidc_client_id,
                "client_secret": cfg.oidc_client_secret,
                "code_verifier": verificador,
            },
        )
    if resposta.status_code != 200:
        raise AssercaoInvalida()
    corpo = resposta.json()
    id_token = corpo.get("id_token")
    if not isinstance(id_token, str):
        raise AssercaoInvalida()
    return id_token


def _chave_para(id_token: str) -> Any:
    """Fetch the provider's key matching this token's `kid`."""
    endpoints = _descobrir()
    with cliente() as c:
        resposta = c.get(endpoints["jwks_uri"])
        resposta.raise_for_status()
        jwks = resposta.json()

    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except jwt.InvalidTokenError as exc:
        raise AssercaoInvalida() from exc

    for chave in jwks.get("keys", []):
        if kid is None or chave.get("kid") == kid:
            return jwt.PyJWK(chave).key
    raise AssercaoInvalida()


def _verificar(id_token: str, *, nonce: str, agora: datetime.datetime) -> Assercao:
    """Verify signature, issuer, audience, expiry and nonce (AC-0001-20).

    `algorithms` is pinned, which is what makes `alg: none` fail rather than be
    trusted — the same reason it is pinned for our own access tokens.
    """
    cfg = get_settings()
    try:
        conteudo = jwt.decode(
            id_token,
            _chave_para(id_token),
            algorithms=ALGORITMOS_ACEITOS,
            audience=cfg.oidc_client_id,
            issuer=cfg.oidc_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise AssercaoInvalida() from exc

    if not secrets.compare_digest(str(conteudo.get("nonce", "")), nonce):
        # Without this a token minted for another login of the same user would
        # be replayable into this one.
        raise AssercaoInvalida()

    grupo = conteudo.get(cfg.oidc_claim_grupo)
    if isinstance(grupo, list):
        grupo = grupo[0] if grupo else None

    return Assercao(
        subject=str(conteudo["sub"]),
        email=conteudo.get("email"),
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
    from app.core.segredos import digerir

    return digerir(valor).hex()


def uuid_nulo() -> uuid.UUID:
    """Entity id for an audit row about a caller with no account."""
    return uuid.UUID(int=0)
