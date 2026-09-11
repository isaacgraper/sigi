"""Access tokens: AC-0001-06 (expiry) and AC-0001-09 (signature).

Named in `traceability.md` under RNF03. No database needed — these are
properties of the token itself, and keeping them out of the DB-backed suite is
what makes them fast enough to run on every save.
"""

from __future__ import annotations

import datetime
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import seguranca
from app.core.config import get_settings
from app.core.seguranca import (
    ALGORITMO,
    ClaimsAcesso,
    TokenExpirado,
    TokenInvalido,
    emitir_access_token,
    gerar_refresh_token,
    verificar_access_token,
)


def _emitir(**kwargs: object) -> str:
    return emitir_access_token(usuario_id=uuid.uuid4(), perfil="servidor", **kwargs)  # type: ignore[arg-type]


def test_token_valido_devolve_as_claims() -> None:
    uid = uuid.uuid4()
    claims = verificar_access_token(emitir_access_token(usuario_id=uid, perfil="gestor"))
    assert isinstance(claims, ClaimsAcesso)
    assert claims.usuario_id == uid
    assert claims.perfil == "gestor"


def test_ac_0001_06_expiracao_de_quinze_minutos() -> None:
    """RNF03 fixes the window; AC-0001-06 fixes what an expired one does."""
    agora = datetime.datetime.now(datetime.UTC)
    claims = verificar_access_token(_emitir(agora=agora))
    minutos = (claims.expira_em - agora).total_seconds() / 60
    assert 14.9 < minutos < 15.1
    assert minutos == pytest.approx(get_settings().access_token_ttl_minutos, abs=0.1)


def test_ac_0001_06_token_expirado_e_recusado() -> None:
    passado = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    with pytest.raises(TokenExpirado) as exc:
        verificar_access_token(_emitir(agora=passado))
    assert exc.value.codigo == "TOKEN_EXPIRADO"
    assert exc.value.http == 401


def test_ac_0001_09_assinatura_de_outra_chave_e_recusada() -> None:
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
        algorithm=ALGORITMO,
    )
    with pytest.raises(TokenInvalido):
        verificar_access_token(forjado)


def test_ac_0001_09_alg_none_e_recusado() -> None:
    """The classic. Pinning `algorithms=["RS256"]` at decode time is what makes
    an unsigned token fail rather than be trusted."""
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
        verificar_access_token(sem_assinatura)


def test_ac_0001_09_emissor_alheio_e_recusado() -> None:
    privada = seguranca._par_de_chaves()[0]
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
        algorithm=ALGORITMO,
    )
    with pytest.raises(TokenInvalido):
        verificar_access_token(de_outro_sistema)


def test_token_de_outro_tipo_nao_passa_por_access() -> None:
    """A refresh token is opaque and could not arrive here, but a future token
    kind could — and accepting one would be a privilege escalation with no
    signature error to notice it."""
    privada = seguranca._par_de_chaves()[0]
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
        algorithm=ALGORITMO,
    )
    with pytest.raises(TokenInvalido):
        verificar_access_token(outro_tipo)


def test_refresh_e_opaco_e_so_o_hash_circula() -> None:
    """AC-0001-07 needs server-side invalidation, which a self-contained token
    cannot offer. So: opaque, high-entropy, and stored only as its HMAC."""
    valor, digest = gerar_refresh_token()
    assert len(valor) >= 40
    assert len(digest) == 32
    assert valor.encode() not in digest
    outro, outro_digest = gerar_refresh_token()
    assert valor != outro
    assert digest != outro_digest
    # Deterministic, or the lookup by hash would never match.
    from app.core.segredos import digerir

    assert digerir(valor) == digest
