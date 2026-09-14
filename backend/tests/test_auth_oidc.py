"""OIDC institucional — AC-0001-19, -20, -21 e -22.

Provedor falso: par de chaves gerado no teste, JWKS servido por um transporte,
`id_token` assinado aqui. Cobre `iss`/`aud`/`exp` errados, `nonce` trocado e
`alg: none` sem tocar em rede — e é o único jeito de exercer isso antes de a TI
da entidade entregar tenant, client e redirect (OQ-09).
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

from app.models.usuario import Usuario
from app.services import oidc

EMISSOR = "https://login.exemplo.gov.br/tenant"
CLIENT_ID = "sigi-cliente"
KID = "chave-de-teste"


class ProvedorFalso:
    """Mints identity tokens and serves the JWKS the verifier fetches."""

    def __init__(self) -> None:
        self.privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.id_token = ""

    def jwks(self) -> dict[str, Any]:
        numeros = self.privada.public_key().public_numbers()
        para_b64 = lambda v, n: jwt.utils.base64url_encode(  # noqa: E731
            v.to_bytes(n, "big")
        ).decode()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": KID,
                    "alg": "RS256",
                    "use": "sig",
                    "n": para_b64(numeros.n, 256),
                    "e": para_b64(numeros.e, 3),
                }
            ]
        }

    def assinar(self, **sobrescreve: Any) -> str:
        agora = datetime.datetime.now(datetime.UTC)
        conteudo: dict[str, Any] = {
            "iss": EMISSOR,
            "aud": CLIENT_ID,
            "sub": "subject-estavel-123",
            "email": "ana@sc.gov.br",
            "groups": ["Gestores-TI"],
            "iat": int(agora.timestamp()),
            "exp": int((agora + datetime.timedelta(minutes=5)).timestamp()),
        }
        conteudo.update(sobrescreve)
        alg = sobrescreve.pop("__alg", "RS256")
        chave = "" if alg == "none" else self.privada
        return jwt.encode(conteudo, chave, algorithm=alg, headers={"kid": KID})

    def rota(self, requisicao: httpx2.Request) -> httpx2.Response:
        caminho = requisicao.url.path
        if caminho.endswith("/.well-known/openid-configuration"):
            return httpx2.Response(
                200,
                json={
                    "authorization_endpoint": f"{EMISSOR}/authorize",
                    "token_endpoint": f"{EMISSOR}/token",
                    "jwks_uri": f"{EMISSOR}/jwks",
                },
            )
        if caminho.endswith("/jwks"):
            return httpx2.Response(200, json=self.jwks())
        if caminho.endswith("/token"):
            return httpx2.Response(200, json={"id_token": self.id_token})
        return httpx2.Response(404)


@pytest.fixture
def provedor(monkeypatch: pytest.MonkeyPatch) -> Iterator[ProvedorFalso]:
    """A configured provider, with the HTTP client replaced by its transport."""
    from app.core.config import get_settings

    falso = ProvedorFalso()
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", EMISSOR)
    monkeypatch.setenv("OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "segredo")
    get_settings.cache_clear()
    monkeypatch.setattr(
        oidc, "cliente", lambda: httpx2.Client(transport=httpx2.MockTransport(falso.rota))
    )
    yield falso
    get_settings.cache_clear()


def _iniciar(aplicacao: TestClient) -> tuple[str, str, str]:
    """Hit /authorize and return (state, nonce, the state cookie).

    The nonce matters: a real provider echoes it into the identity token, so the
    fake one has to as well. Without it every token fails the nonce check, and
    the AC-0001-20 cases would pass for that reason instead of the one they
    investigate.
    """
    resposta = aplicacao.get("/api/v1/auth/oidc/authorize", follow_redirects=False)
    assert resposta.status_code == 302, resposta.text
    destino = httpx2.URL(resposta.headers["location"])
    cookie = next(
        c.split("=", 1)[1].split(";")[0]
        for c in resposta.headers.get_list("set-cookie")
        if c.startswith("sigi_oidc_estado=")
    )
    return destino.params["state"], destino.params["nonce"], cookie


def test_ac_0001_19_pkce_state_nonce(aplicacao: TestClient, provedor: ProvedorFalso) -> None:
    """AC-0001-19 — o redirect leva PKCE S256, state e nonce."""
    resposta = aplicacao.get("/api/v1/auth/oidc/authorize", follow_redirects=False)
    assert resposta.status_code == 302
    destino = httpx2.URL(resposta.headers["location"])

    assert destino.params["response_type"] == "code"
    assert destino.params["code_challenge_method"] == "S256"
    assert destino.params["code_challenge"]
    assert destino.params["state"]
    assert destino.params["nonce"]
    assert destino.params["client_id"] == CLIENT_ID

    # O verificador nunca vai na URL — só o desafio derivado dele.
    assert "code_verifier" not in destino.params

    bruto = next(
        c for c in resposta.headers.get_list("set-cookie") if c.startswith("sigi_oidc_estado=")
    )
    assert "httponly" in bruto.lower()
    assert "max-age=600" in bruto.lower()


def test_ac_0001_19_estado_nunca_emitido_e_recusado(
    aplicacao: TestClient, provedor: ProvedorFalso
) -> None:
    """AC-0001-19 — state forjado, e state sem cookie, respondem 401."""
    provedor.id_token = provedor.assinar()

    sem_cookie = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "x", "state": "inventado"}
    )
    assert sem_cookie.status_code == 401
    assert sem_cookie.json()["error"]["code"] == "ESTADO_INVALIDO"

    _, _, cookie = _iniciar(aplicacao)
    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    trocado = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "x", "state": "outro-estado"}
    )
    assert trocado.status_code == 401
    assert trocado.json()["error"]["code"] == "ESTADO_INVALIDO"
    aplicacao.cookies.clear()


@pytest.mark.parametrize(
    ("rotulo", "sobrescreve"),
    [
        ("emissor-errado", {"iss": "https://outro-provedor.exemplo"}),
        ("audiencia-errada", {"aud": "outro-cliente"}),
        ("expirado", {"exp": 1000000000}),
        ("alg-none", {"__alg": "none"}),
    ],
)
def test_ac_0001_20_verificacao_do_id_token(
    aplicacao: TestClient,
    provedor: ProvedorFalso,
    sessao: Session,
    rotulo: str,
    sobrescreve: dict[str, Any],
) -> None:
    """AC-0001-20 — assinatura, emissor, audiência, expiração e `alg: none`."""
    estado, nonce, cookie = _iniciar(aplicacao)
    provedor.id_token = provedor.assinar(nonce=nonce, **sobrescreve)

    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()

    assert resposta.status_code == 401, f"{rotulo}: {resposta.text}"
    assert resposta.json()["error"]["code"] == "ASSERCAO_INVALIDA"

    sessao.rollback()
    recusas = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE acao = 'auth.oidc_recusada'")
    ).scalar_one()
    assert recusas >= 1


def test_ac_0001_20_assinatura_de_outra_chave(
    aplicacao: TestClient, provedor: ProvedorFalso
) -> None:
    """Token bem formado, assinado por quem o provedor não publicou."""
    estado, nonce, cookie = _iniciar(aplicacao)
    intruso = ProvedorFalso()
    provedor.id_token = intruso.assinar(nonce=nonce)

    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()
    assert resposta.status_code == 401


def test_ac_0001_20_nonce_trocado(aplicacao: TestClient, provedor: ProvedorFalso) -> None:
    """Sem a checagem de nonce, um token emitido para outro login desta mesma
    pessoa seria reaproveitável neste."""
    estado, nonce, cookie = _iniciar(aplicacao)
    provedor.id_token = provedor.assinar(nonce="nonce-de-outro-login")

    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()
    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "ASSERCAO_INVALIDA"


def test_ac_0001_21_sem_provisionamento_jit(
    aplicacao: TestClient, provedor: ProvedorFalso, sessao: Session
) -> None:
    """AC-0001-21 — assertiva válida sem conta: 403, e nenhuma linha criada."""
    sessao.rollback()
    antes = sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one()

    estado, nonce, cookie = _iniciar(aplicacao)
    provedor.id_token = provedor.assinar(nonce=nonce, sub="ninguem-aqui", email="ninguem@sc.gov.br")
    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()

    assert resposta.status_code == 403
    assert resposta.json()["error"]["code"] == "USUARIO_NAO_PROVISIONADO"

    sessao.rollback()
    assert sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one() == antes

    # O endereço asserido é registrado como HMAC: quem foi recusado não tem
    # conta para anonimizar depois, e a tabela nunca pode ser corrigida.
    linha = sessao.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'auth.oidc_recusada' ORDER BY ocorrido_em DESC LIMIT 1"
        )
    ).scalar_one()
    assert "ninguem@sc.gov.br" not in linha
    assert "sc.gov.br" in linha


@pytest.mark.parametrize("status", ["pendente", "bloqueado", "desativado"])
def test_ac_0001_21_conta_inativa_nao_entra(
    aplicacao: TestClient,
    provedor: ProvedorFalso,
    criar_usuario: Callable[..., Usuario],
    status: str,
) -> None:
    """Conta que existe mas não está `ativo` também recebe 403."""
    sujeito = f"sub-{status}-{uuid.uuid4().hex[:6]}"
    email = f"{status}-{uuid.uuid4().hex[:6]}@sc.gov.br"
    criar_usuario(
        email=email,
        status=status,
        senha=None if status == "pendente" else "SenhaCorreta-12345",
    )

    estado, nonce, cookie = _iniciar(aplicacao)
    provedor.id_token = provedor.assinar(nonce=nonce, sub=sujeito, email=email)
    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()

    assert resposta.status_code == 403
    assert resposta.json()["error"]["code"] == "USUARIO_NAO_PROVISIONADO"


def test_ac_0001_22_perfil_vem_do_registro(
    aplicacao: TestClient,
    provedor: ProvedorFalso,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    """AC-0001-22 — o provedor assere "Gestores-TI"; a sessão sai `servidor`."""
    email = f"perfil-{uuid.uuid4().hex[:6]}@sc.gov.br"
    usuario = criar_usuario(email=email, perfil="servidor")

    estado, nonce, cookie = _iniciar(aplicacao)
    provedor.id_token = provedor.assinar(nonce=nonce, sub=f"sub-{usuario.id}", email=email)
    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()

    assert resposta.status_code == 200, resposta.text
    acesso = resposta.json()["access_token"]
    assert (
        json.loads(jwt.utils.base64url_decode(acesso.split(".")[1] + "==").decode())["perfil"]
        == "servidor"
    )

    sessao.rollback()
    claim = sessao.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'auth.oidc_claim' AND entidade_id = :u"
        ),
        {"u": usuario.id},
    ).scalar_one()
    # Registrada para a auditoria, e consultada por decisão nenhuma.
    assert "Gestores-TI" in claim
    assert "servidor" in claim


def test_ac_0001_03_oidc_nao_e_afetado(
    aplicacao: TestClient,
    provedor: ProvedorFalso,
    criar_usuario: Callable[..., Usuario],
) -> None:
    """AC-0001-03, última cláusula — o bloqueio por tentativas não alcança o OIDC.

    Se alcançasse, quem soubesse o e-mail do último gestor negaria a gestão de
    membros em blocos de quinze minutos, anonimamente — o desfecho que o
    AC-0001-29 existe para impedir, alcançado por uma rota que ele não guarda.
    """
    email = f"travado-{uuid.uuid4().hex[:6]}@sc.gov.br"
    criar_usuario(email=email, perfil="gestor")

    for _ in range(6):
        aplicacao.post("/api/v1/auth/login", json={"email": email, "senha": "errada-mas-longa"})
    travado = aplicacao.post(
        "/api/v1/auth/login", json={"email": email, "senha": "errada-mas-longa"}
    )
    assert travado.status_code == 429

    estado, nonce, cookie = _iniciar(aplicacao)
    provedor.id_token = provedor.assinar(nonce=nonce, sub=f"sub-{email}", email=email)
    aplicacao.cookies.set("sigi_oidc_estado", cookie)
    resposta = aplicacao.get(
        "/api/v1/auth/oidc/callback", params={"code": "codigo", "state": estado}
    )
    aplicacao.cookies.clear()

    assert resposta.status_code == 200, resposta.text
