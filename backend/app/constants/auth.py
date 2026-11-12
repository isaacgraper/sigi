"""Fixed values of authentication and sessions (SPEC-0001)."""

from __future__ import annotations

from typing import Final

# ── Access and refresh tokens ───────────────────────────────────────────────

JWT_ALGORITHM: Final = "RS256"
ACCESS_TOKEN_TYPE: Final = "access"
BEARER_SCHEME: Final = "bearer"

# 256 bits from a CSPRNG. The refresh token is looked up by equality on an
# indexed column, so its security rests entirely on being unguessable.
REFRESH_TOKEN_BYTES: Final = 32

# The cookie is scoped to the routes that consume it. A refresh token sent on
# every request to every path is a refresh token exposed by every request; only
# `/refresh` and `/logout` ever read it.
REFRESH_COOKIE_PATH: Final = "/api/v1/auth"

# Mirrors `ck_sessao_motivo_valor` as migration 0001 creates it: why a session
# ended. Not the vocabulary of `usuario.status`, which describes the account.
REVOCATION_REASONS: Final = (
    "rotacao",
    "logout",
    "replay",
    "desativacao",
    "bloqueio",
    "redefinicao",
)

# ── Invitation and reset links ──────────────────────────────────────────────

CREDENTIAL_INVITE: Final = "convite"
CREDENTIAL_RESET: Final = "redefinicao"

# Mirrors `ck_token_tipo`.
CREDENTIAL_KINDS: Final = (CREDENTIAL_INVITE, CREDENTIAL_RESET)

# 256 bits from a CSPRNG. The grant is looked up by equality on an indexed
# column, so its security rests entirely on being unguessable.
CREDENTIAL_TOKEN_BYTES: Final = 32

# ── Institutional login (OIDC) ──────────────────────────────────────────────

OIDC_ACCEPTED_ALGORITHMS: Final = ("RS256",)
OIDC_STATE_TYPE: Final = "oidc_estado"
OIDC_STATE_COOKIE: Final = "sigi_oidc_estado"
OIDC_STATE_COOKIE_PATH: Final = "/api/v1/auth/oidc"

# ── Rate limiting ───────────────────────────────────────────────────────────

# The routes throttled per source by default (AC-0001-33).
THROTTLED_PREFIXES: Final = ("/api/v1/auth", "/api/v1/convites")
