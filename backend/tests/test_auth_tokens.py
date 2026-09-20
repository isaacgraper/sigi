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
    TokenExpirado,
    TokenInvalido,
    generate_refresh_token,
    issue_access_token,
    verify_access_token,
)
from app.models.user import User
from tests.conftest import cookie_from, use_refresh

SENHA = "SenhaCorreta-12345"


def _issue(**kwargs: object) -> str:
    return issue_access_token(usuario_id=uuid.uuid4(), role="servidor", **kwargs)  # type: ignore[arg-type]


def test_token_valido_devolve_as_claims() -> None:
    """A token this service minted verifies, and its claims come back intact."""
    uid = uuid.uuid4()
    claims = verify_access_token(issue_access_token(usuario_id=uid, role="gestor"))
    assert isinstance(claims, AccessClaims)
    assert claims.usuario_id == uid
    assert claims.role == "gestor"


def test_ac_0001_06_expiracao_de_quinze_minutos() -> None:
    """RNF03 fixes the window; AC-0001-06 fixes what an expired one does."""
    now = datetime.datetime.now(datetime.UTC)
    claims = verify_access_token(_issue(now=now))
    minutos = (claims.expira_em - now).total_seconds() / 60
    assert 14.9 < minutos < 15.1
    assert minutos == pytest.approx(get_settings().access_token_ttl_minutos, abs=0.1)


def test_ac_0001_06_token_expirado_e_recusado() -> None:
    """AC-0001-06 — an expired token is refused."""
    passado = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    with pytest.raises(TokenExpirado) as exc:
        verify_access_token(_issue(now=passado))
    assert exc.value.code == "TOKEN_EXPIRED"
    assert exc.value.http == 401


def test_ac_0001_09_assinatura_de_outra_chave_e_recusada() -> None:
    """AC-0001-09 — a token signed with another key is refused."""
    outra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = outra.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    forjado = jwt.encode(
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
    with pytest.raises(TokenInvalido):
        verify_access_token(forjado)


def test_ac_0001_09_alg_none_e_recusado() -> None:
    """AC-0001-09 — `alg: none` is refused.

    Pinning `algorithms=["RS256"]` at decode time is what makes an unsigned
    token fail rather than be trusted.
    """
    sem_assinatura = jwt.encode(
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
    with pytest.raises(TokenInvalido):
        verify_access_token(sem_assinatura)


def test_ac_0001_09_emissor_alheio_e_recusado() -> None:
    """AC-0001-09 — a token from another issuer is refused."""
    privada = security._key_pair()[0]
    de_outro_sistema = jwt.encode(
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
        privada,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenInvalido):
        verify_access_token(de_outro_sistema)


def test_token_de_outro_tipo_nao_passa_por_access() -> None:
    """A token of another `typ` is not accepted as an access token.

    A refresh token is opaque and could not arrive here, but a future token kind
    could — and accepting one would be a privilege escalation with no signature
    error to notice it.
    """
    privada = security._key_pair()[0]
    outro_tipo = jwt.encode(
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
        privada,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenInvalido):
        verify_access_token(outro_tipo)


def test_refresh_e_opaco_e_so_o_hash_circula() -> None:
    """The refresh token is opaque, and only its HMAC is stored.

    AC-0001-07 needs server-side invalidation, which a self-contained token
    cannot offer.
    """
    valor, digest = generate_refresh_token()
    assert len(valor) >= 40
    assert len(digest) == 32
    assert valor.encode() not in digest
    outro, outro_digest = generate_refresh_token()
    assert valor != outro
    assert digest != outro_digest
    # Deterministic, or the lookup by hash would never match.
    from app.core.secrets_hmac import digest_secret

    assert digest_secret(valor) == digest


# ── Against the database and the assembled application ──────────────────────
# What follows is not a property of the token alone: renewing and invalidating
# are server state, which is exactly why the refresh token is opaque.


def test_ac_0001_06_token_expirado_e_refresh(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-06 — an expired token is refused; refresh renews without a senha."""
    usuario = criar_usuario()
    entrada = application.post(
        "/api/v1/auth/login", json={"email": usuario.email, "password": SENHA}
    )
    refresh = cookie_from(entrada, "sigi_refresh")
    assert refresh

    expirado = issue_access_token(
        usuario_id=usuario.id,
        role=usuario.role,
        now=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
    )
    recusado = application.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expirado}"})
    assert recusado.status_code == 401
    assert recusado.json()["error"]["code"] == "TOKEN_EXPIRED"

    use_refresh(application, refresh)
    renovado = application.post("/api/v1/auth/refresh")
    assert renovado.status_code == 200
    novo = renovado.json()["access_token"]
    assert novo != entrada.json()["access_token"]

    # The cookie was rotated, not reissued identical: rotation is what makes a
    # stolen refresh token detectable rather than merely valid for seven days.
    rotacionado = cookie_from(renovado, "sigi_refresh")
    assert rotacionado and rotacionado != refresh

    aceito = application.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {novo}"})
    assert aceito.status_code == 200
    assert aceito.json()["id"] == str(usuario.id)


def test_ac_0001_07_logout_e_replay_derruba_familia(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-07 — logout invalidates the refresh, and a replay is audited.

    What this test exists to pin is the last `assert`: the family revocation and
    the audit row must **survive** the request that fails. Written in the
    request's session they would roll back with it, leaving the stolen family
    alive and the theft unrecorded — behind the same 401 on screen.
    """
    usuario = criar_usuario()
    entrada = application.post(
        "/api/v1/auth/login", json={"email": usuario.email, "password": SENHA}
    )
    primeiro = cookie_from(entrada, "sigi_refresh")
    assert primeiro

    use_refresh(application, primeiro)
    renovado = application.post("/api/v1/auth/refresh")
    segundo = cookie_from(renovado, "sigi_refresh")
    assert segundo

    use_refresh(application, segundo)
    assert application.post("/api/v1/auth/logout").status_code == 204

    use_refresh(application, segundo)
    replay = application.post("/api/v1/auth/refresh")
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "INVALID_REFRESH"

    # An earlier generation, which the logout should also have revoked.
    use_refresh(application, primeiro)
    assert application.post("/api/v1/auth/refresh").status_code == 401

    sessao.rollback()  # enxerga o que as transações do servidor comitaram
    linhas = sessao.execute(
        text(
            "SELECT dados_anteriores FROM historico_movimentacao"
            " WHERE acao = 'auth.refresh_replay' AND usuario_id = :uid"
        ),
        {"uid": usuario.id},
    ).all()
    assert len(linhas) >= 1
    vivas = sessao.execute(
        text("SELECT count(*) FROM sessao WHERE usuario_id = :uid AND revogado_em IS NULL"),
        {"uid": usuario.id},
    ).scalar_one()
    assert vivas == 0


def test_refresh_ausente_ou_desconhecido_e_401(application: TestClient) -> None:
    """A missing refresh cookie and an invented one answer identically.

    Saying "that token does not exist" would confirm, by elimination, which
    ones do.
    """
    sem = application.post("/api/v1/auth/refresh")
    use_refresh(application, "token-que-nunca-foi-emitido")
    desconhecido = application.post("/api/v1/auth/refresh")

    assert sem.status_code == desconhecido.status_code == 401
    assert sem.json()["error"]["code"] == desconhecido.json()["error"]["code"] == "INVALID_REFRESH"


def test_logout_sem_cookie_nao_falha(application: TestClient) -> None:
    """Logging out with no session is still 204.

    A client that lost its cookie still wants to leave, and an error here only
    teaches people to ignore errors.
    """
    assert application.post("/api/v1/auth/logout").status_code == 204
