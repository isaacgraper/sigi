"""Issuing and verifying a session (RNF03, AC-0001-01/06/07/09).

Two token kinds, deliberately different in nature:

- The **access token** is a signed JWT, RS256, 15 minutes. It is verified by
  signature alone, so no database round trip is needed to know *who* is calling
  — which is what keeps the hot path cheap.
- The **refresh token** is an opaque random string, never a JWT. AC-0001-07
  requires invalidating one before its own expiry and detecting a replay, and
  neither is possible with a self-contained token: the state has to live in
  `sessao`. Only its HMAC is stored, so a leaked database yields nothing usable.

Asymmetric signing for the access token even though only this service verifies
it today: RS256 means a future reader — a report exporter, a second service —
can verify without holding the power to mint.
"""

from __future__ import annotations

import datetime
import secrets
import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import get_settings
from app.core.segredos import digest_secret
from app.services.erros import ErroDominio

ALGORITMO = "RS256"
TIPO_ACESSO = "access"
# 256 bits from a CSPRNG. The refresh token is looked up by equality on an
# indexed column, so its security rests entirely on being unguessable.
BYTES_REFRESH = 32


class TokenExpirado(ErroDominio):
    codigo = "TOKEN_EXPIRADO"
    http = 401


class TokenInvalido(ErroDominio):
    codigo = "TOKEN_INVALIDO"
    http = 401


@dataclass(frozen=True)
class ClaimsAcesso:
    usuario_id: uuid.UUID
    perfil: str
    expira_em: datetime.datetime


@lru_cache
def _par_de_chaves() -> tuple[bytes, bytes]:
    """The signing pair, or an ephemeral one in development.

    Generating a pair when none is configured keeps a fresh clone working. Doing
    that outside `development` would silently invalidate every session on each
    restart, and nobody connects those two facts — so there it is a startup
    error instead.
    """
    cfg = get_settings()
    if cfg.jwt_private_key and cfg.jwt_public_key:
        return cfg.jwt_private_key.encode(), cfg.jwt_public_key.encode()
    if cfg.app_env != "development":
        raise RuntimeError(
            "jwt_private_key and jwt_public_key are required outside development: "
            "an ephemeral pair would invalidate every session on each restart."
        )
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        privada.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )


def reset_keys() -> None:
    """Drop the cached pair. Tests mint their own."""
    _par_de_chaves.cache_clear()


def issue_access_token(
    *,
    usuario_id: uuid.UUID,
    perfil: str,
    now: datetime.datetime | None = None,
) -> str:
    cfg = get_settings()
    now = now or datetime.datetime.now(datetime.UTC)
    expira = now + datetime.timedelta(minutes=cfg.access_token_ttl_minutos)
    return jwt.encode(
        {
            # RS256 is deterministic: with no unique claim, two tokens issued
            # in the same second for the same usuario come out **byte for byte
            # identical**, because `iat` and `exp` are whole seconds. `jti` is
            # what gives each issued token an identity of its own, which is what
            # a log line, an audit correlation or a future revocation list need
            # in order to mean anything.
            "jti": str(uuid.uuid4()),
            "sub": str(usuario_id),
            "perfil": perfil,
            "typ": TIPO_ACESSO,
            "iss": cfg.jwt_issuer,
            "iat": int(now.timestamp()),
            "exp": int(expira.timestamp()),
        },
        _par_de_chaves()[0],
        algorithm=ALGORITMO,
    )


def verify_access_token(token: str) -> ClaimsAcesso:
    """Decode and validate, or raise.

    `algorithms` is pinned to RS256, which is what makes `alg: none` and an
    HS256 token signed with the public key both fail (AC-0001-09). This says
    nothing about whether the usuario is still active — that is a separate
    check, on every request, and conflating the two is how a deactivation comes
    to take fifteen minutes (AC-0001-08).
    """
    cfg = get_settings()
    try:
        payload = jwt.decode(
            token,
            _par_de_chaves()[1],
            algorithms=[ALGORITMO],
            issuer=cfg.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpirado("Sua sessão expirou. Entre novamente.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.") from exc

    if payload.get("typ") != TIPO_ACESSO:
        # A refresh token is opaque and could never arrive here, but a future
        # token kind could — and accepting one as an access token would be a
        # privilege escalation with no signature error to notice it.
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.")

    return ClaimsAcesso(
        usuario_id=uuid.UUID(payload["sub"]),
        perfil=payload["perfil"],
        expira_em=datetime.datetime.fromtimestamp(payload["exp"], datetime.UTC),
    )


def generate_refresh_token() -> tuple[str, bytes]:
    """Return `(valor, hash)`. Only the hash is ever stored."""
    valor = secrets.token_urlsafe(BYTES_REFRESH)
    return valor, digest_secret(valor)
