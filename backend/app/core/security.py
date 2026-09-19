"""Issuing and verifying a session (RNF03, AC-0001-01/06/07/09).

Two token kinds, deliberately different in nature:

- The **access token** is a signed JWT, RS256, 15 minutes. It is verified by
  signature alone, so no database round trip is needed to know *who* is calling
  — which is what keeps the hot path cheap.
- The **refresh token** is an opaque random string, never a JWT. AC-0001-07
  requires invalidating one before its own expiry and detecting a replay, and
  neither is possible with a self-contained token: the state has to live in
  `session`. Only its HMAC is stored, so a leaked database yields nothing usable.

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
from app.core.secrets_hmac import digest_secret
from app.services.errors import DomainError

ALGORITMO = "RS256"
TIPO_ACESSO = "access"
# 256 bits from a CSPRNG. The refresh token is looked up by equality on an
# indexed column, so its security rests entirely on being unguessable.
BYTES_REFRESH = 32


class TokenExpirado(DomainError):
    """The access token is past its `exp`."""

    code = "TOKEN_EXPIRADO"
    http = 401


class TokenInvalido(DomainError):
    """The access token did not verify, or is not an access token."""

    code = "TOKEN_INVALIDO"
    http = 401


@dataclass(frozen=True)
class AccessClaims:
    """What a verified access token asserts."""

    usuario_id: uuid.UUID
    role: str
    expira_em: datetime.datetime


@lru_cache
def _key_pair() -> tuple[bytes, bytes]:
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
    _key_pair.cache_clear()


def issue_access_token(
    *,
    usuario_id: uuid.UUID,
    role: str,
    now: datetime.datetime | None = None,
) -> str:
    """Mint an access token for this user and role."""
    cfg = get_settings()
    now = now or datetime.datetime.now(datetime.UTC)
    expires = now + datetime.timedelta(minutes=cfg.access_token_ttl_minutos)
    return jwt.encode(
        {
            # RS256 é determinístico: sem um claim único, dois tokens emitidos
            # no mesmo segundo para o mesmo usuário saem **byte a byte iguais**,
            # porque `iat` e `exp` são segundos inteiros. O `jti` é o que dá a
            # cada token emitido uma identidade própria — que é o que um log,
            # uma correlação de audit ou uma futura lista de revogação
            # precisam ter para significar alguma coisa.
            "jti": str(uuid.uuid4()),
            "sub": str(usuario_id),
            "perfil": role,
            "typ": TIPO_ACESSO,
            "iss": cfg.jwt_issuer,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        },
        _key_pair()[0],
        algorithm=ALGORITMO,
    )


def verify_access_token(token: str) -> AccessClaims:
    """Decode and validate, or raise.

    `algorithms` is pinned to RS256, which is what makes `alg: none` and an
    HS256 token signed with the public key both fail (AC-0001-09). This says
    nothing about whether the user is still active — that is a separate
    check, on every request, and conflating the two is how a deactivation comes
    to take fifteen minutes (AC-0001-08).
    """
    cfg = get_settings()
    try:
        payload = jwt.decode(
            token,
            _key_pair()[1],
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

    return AccessClaims(
        usuario_id=uuid.UUID(payload["sub"]),
        role=payload["perfil"],
        expira_em=datetime.datetime.fromtimestamp(payload["exp"], datetime.UTC),
    )


def generate_refresh_token() -> tuple[str, bytes]:
    """Return `(value, hash)`. Only the hash is ever stored."""
    value = secrets.token_urlsafe(BYTES_REFRESH)
    return value, digest_secret(value)
