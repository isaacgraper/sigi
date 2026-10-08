"""Access tokens: AC-0001-06 (expiry) and AC-0001-09 (signature).

Named in `traceability.md` under RNF03. No database needed — these are
properties of the token itself, and keeping them out of the DB-backed suite is
what makes them fast enough to run on every save.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.security import (
    ALGORITHM,
    AccessClaims,
    TokenExpired,
    TokenInvalid,
    generate_refresh_token,
    issue_access_token,
    verify_access_token,
)
from app.models.user import User
from tests.conftest import cookie_from, use_refresh

PASSWORD = "SenhaCorreta-12345"


def _issue(**kwargs: object) -> str:
    return issue_access_token(user_id=uuid.uuid4(), role="servidor", **kwargs)  # type: ignore[arg-type]


def test_a_valid_token_returns_the_claims() -> None:
    """A token this service minted verifies, and its claims come back intact."""
    uid = uuid.uuid4()
    claims = verify_access_token(issue_access_token(user_id=uid, role="gestor"))
    assert isinstance(claims, AccessClaims)
    assert claims.user_id == uid
    assert claims.role == "gestor"


def test_ac_0001_06_a_fifteen_minute_expiry() -> None:
    """RNF03 fixes the window; AC-0001-06 fixes what an expired one does."""
    now = datetime.datetime.now(datetime.UTC)
    claims = verify_access_token(_issue(now=now))
    minutes = (claims.expires_at - now).total_seconds() / 60
    assert 14.9 < minutes < 15.1
    assert minutes == pytest.approx(get_settings().access_token_ttl_minutes, abs=0.1)


def test_ac_0001_06_an_expired_token_is_refused() -> None:
    """AC-0001-06 — an expired token is refused."""
    past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    with pytest.raises(TokenExpired) as exc:
        verify_access_token(_issue(now=past))
    assert exc.value.code == "TOKEN_EXPIRED"
    assert exc.value.http == 401


def test_ac_0001_09_a_signature_from_another_key_is_refused() -> None:
    """AC-0001-09 — a token signed with another key is refused."""
    other_one = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = other_one.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "perfil": "gestor",
            "typ": "access",
            "iss": get_settings().jwt_issuer,
            "iat": int(datetime.datetime.now(datetime.UTC).timestamp()),
            "exp": int(
                (datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)).timestamp()
            ),
        },
        pem,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenInvalid):
        verify_access_token(forged)


def test_ac_0001_09_alg_none_is_refused() -> None:
    """AC-0001-09 — `alg: none` is refused.

    Pinning `algorithms=["RS256"]` at decode time is what makes an unsigned
    token fail rather than be trusted.
    """
    unsigned = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "perfil": "gestor",
            "typ": "access",
            "iss": get_settings().jwt_issuer,
            "iat": int(datetime.datetime.now(datetime.UTC).timestamp()),
            "exp": int(
                (datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)).timestamp()
            ),
        },
        key="",
        algorithm="none",
    )
    with pytest.raises(TokenInvalid):
        verify_access_token(unsigned)


def test_ac_0001_09_a_foreign_issuer_is_refused() -> None:
    """AC-0001-09 — a token from another issuer is refused."""
    private_key = security._key_pair()[0]
    from_another_system = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "perfil": "gestor",
            "typ": "access",
            "iss": "outro-sistema",
            "iat": int(datetime.datetime.now(datetime.UTC).timestamp()),
            "exp": int(
                (datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)).timestamp()
            ),
        },
        private_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenInvalid):
        verify_access_token(from_another_system)


def test_a_token_of_another_kind_does_not_pass_as_access() -> None:
    """A token of another `typ` is not accepted as an access token.

    A refresh token is opaque and could not arrive here, but a future token kind
    could — and accepting one would be a privilege escalation with no signature
    error to notice it.
    """
    private_key = security._key_pair()[0]
    other_kind = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "perfil": "gestor",
            "typ": "reset",
            "iss": get_settings().jwt_issuer,
            "iat": int(datetime.datetime.now(datetime.UTC).timestamp()),
            "exp": int(
                (datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=15)).timestamp()
            ),
        },
        private_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenInvalid):
        verify_access_token(other_kind)


def test_the_refresh_is_opaque_and_only_the_hash_circulates() -> None:
    """The refresh token is opaque, and only its HMAC is stored.

    AC-0001-07 needs server-side invalidation, which a self-contained token
    cannot offer.
    """
    value, digest = generate_refresh_token()
    assert len(value) >= 40
    assert len(digest) == 32
    assert value.encode() not in digest
    other, other_digest = generate_refresh_token()
    assert value != other
    assert digest != other_digest
    # Deterministic, or the lookup by hash would never match.
    from app.core.secrets_hmac import digest_secret

    assert digest_secret(value) == digest


# ── Against the database and the assembled application ──────────────────────
# What follows is not a property of the token alone: renewing and invalidating
# are server state, which is exactly why the refresh token is opaque.


def test_ac_0001_06_an_expired_token_and_refresh(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-06 — an expired token is refused; refresh renews without a senha."""
    user = create_user()
    entry = application.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    refresh = cookie_from(entry, "sigi_refresh")
    assert refresh

    expired = issue_access_token(
        user_id=user.id,
        role=user.role,
        now=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
    )
    refused = application.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert refused.status_code == 401
    assert refused.json()["error"]["code"] == "TOKEN_EXPIRED"

    use_refresh(application, refresh)
    rotated = application.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    new_one = rotated.json()["access_token"]
    assert new_one != entry.json()["access_token"]

    # The cookie was rotated, not reissued identical: rotation is what makes a
    # stolen refresh token detectable rather than merely valid for seven days.
    rotated_pair = cookie_from(rotated, "sigi_refresh")
    assert rotated_pair and rotated_pair != refresh

    accepted = application.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_one}"})
    assert accepted.status_code == 200
    assert accepted.json()["id"] == str(user.id)


def test_ac_0001_07_logout_and_replay_bring_the_family_down(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-07 — logout invalidates the refresh, and a replay is audited.

    What this test exists to pin is the last `assert`: the family revocation and
    the audit row must **survive** the request that fails. Written in the
    request's session they would roll back with it, leaving the stolen family
    alive and the theft unrecorded — behind the same 401 on screen.
    """
    user = create_user()
    entry = application.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    first = cookie_from(entry, "sigi_refresh")
    assert first

    use_refresh(application, first)
    rotated = application.post("/api/v1/auth/refresh")
    second = cookie_from(rotated, "sigi_refresh")
    assert second

    use_refresh(application, second)
    assert application.post("/api/v1/auth/logout").status_code == 204

    use_refresh(application, second)
    replay = application.post("/api/v1/auth/refresh")
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "INVALID_REFRESH"

    # An earlier generation, which the logout should also have revoked.
    use_refresh(application, first)
    assert application.post("/api/v1/auth/refresh").status_code == 401

    db_session.rollback()  # enxerga o que as transações do servidor comitaram
    rows = db_session.execute(
        text(
            "SELECT dados_anteriores FROM historico_movimentacao"
            " WHERE acao = 'auth.refresh_replay' AND usuario_id = :uid"
        ),
        {"uid": user.id},
    ).all()
    assert len(rows) >= 1
    alive = db_session.execute(
        text("SELECT count(*) FROM sessao WHERE usuario_id = :uid AND revogado_em IS NULL"),
        {"uid": user.id},
    ).scalar_one()
    assert alive == 0


def test_a_missing_or_unknown_refresh_is_401(application: TestClient) -> None:
    """A missing refresh cookie and an invented one answer identically.

    Saying "that token does not exist" would confirm, by elimination, which
    ones do.
    """
    missing = application.post("/api/v1/auth/refresh")
    use_refresh(application, "token-que-nunca-foi-emitido")
    unknown = application.post("/api/v1/auth/refresh")

    assert missing.status_code == unknown.status_code == 401
    assert missing.json()["error"]["code"] == unknown.json()["error"]["code"] == "INVALID_REFRESH"


def test_logout_without_a_cookie_does_not_fail(application: TestClient) -> None:
    """Logging out with no session is still 204.

    A client that lost its cookie still wants to leave, and an error here only
    teaches people to ignore errors.
    """
    assert application.post("/api/v1/auth/logout").status_code == 204
