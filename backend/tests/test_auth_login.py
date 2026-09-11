"""Local login — SPEC-0001 AC-0001-01, -02, -04, -05, -24.

Against a real database and the assembled application, because most of what
these criteria assert lives at the edges: a cookie's flags, the bytes of an
error body, the absence of a column from a response.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.usuario import Usuario
from tests.conftest import cookie_de

SENHA = "SenhaCorreta-12345"
LOGIN = "/api/v1/auth/login"


def test_ac_0001_01_login_emite_par_de_tokens(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """AC-0001-01 — 200, access token de 15 min, e o refresh só no cookie."""
    usuario = criar_usuario()
    resposta = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "Bearer"
    assert corpo["access_token"]

    bruto = next(
        c for c in resposta.headers.get_list("set-cookie") if c.startswith("sigi_refresh=")
    )
    atributos = {p.strip().split("=")[0].lower() for p in bruto.split(";")[1:]}
    assert "httponly" in atributos
    assert "secure" in atributos
    assert "samesite=lax" in bruto.lower()
    assert "max-age=604800" in bruto.lower()  # 7 dias (RNF03)

    # O valor do refresh não aparece em lugar nenhum do corpo — um refresh token
    # que vaza num log ou numa captura de tela renova sessão por sete dias.
    valor = cookie_de(resposta, "sigi_refresh")
    assert valor and valor not in resposta.text


def test_ac_0001_02_resposta_identica_para_email_inexistente(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """AC-0001-02 — senha errada e e-mail inexistente respondem o mesmo.

    O `correlation_id` entra no envelope e muda a cada requisição, então o mesmo
    é enviado nas duas: sem isso "byte-idêntico" seria impossível de afirmar, e
    afirmar menos aqui é abrir de volta o oráculo que o critério fecha.
    """
    usuario = criar_usuario()
    cabecalhos = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-00000000beef"}

    errada = aplicacao.post(
        LOGIN,
        json={"email": usuario.email, "senha": "senha-errada-mas-longa"},
        headers=cabecalhos,
    )
    inexistente = aplicacao.post(
        LOGIN,
        json={"email": "naoexiste@sc.gov.br", "senha": "senha-errada-mas-longa"},
        headers=cabecalhos,
    )

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"
    assert errada.content == inexistente.content
    # E nem o corpo nem o cabeçalho podem dizer "esse e-mail existe".
    assert "existe" not in errada.text.lower().replace("inexistente", "")


def test_ac_0001_04_dominio_fora_da_allowlist(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """AC-0001-04 — e-mail fora dos domínios institucionais não autentica.

    Mesmo com a senha certa e a conta ativa: o registro existe, o domínio é que
    não é aceito — e a resposta é indistinguível de senha errada.
    """
    usuario = criar_usuario(email="alguem@gmail.com")
    cabecalhos = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-0000000000aa"}

    fora = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA}, headers=cabecalhos)
    errada = aplicacao.post(
        LOGIN, json={"email": "outro@sc.gov.br", "senha": SENHA}, headers=cabecalhos
    )

    assert fora.status_code == 401
    assert fora.json()["error"]["code"] == "CREDENCIAIS_INVALIDAS"
    assert fora.content == errada.content


def test_ac_0001_05_hash_nunca_sai_do_banco(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """AC-0001-05 — bcrypt custo ≥ 12, e o hash não sai por nenhuma rota."""
    usuario = criar_usuario()
    assert usuario.senha_hash is not None
    prefixo, custo = usuario.senha_hash.split("$")[1], usuario.senha_hash.split("$")[2]
    assert prefixo in ("2a", "2b", "2y")
    assert int(custo) >= 12

    entrada = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA})
    eu = aplicacao.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {entrada.json()['access_token']}"},
    )

    assert eu.status_code == 200
    assert set(eu.json()) == {"id", "nome", "email", "perfil", "status"}
    for resposta in (entrada, eu):
        assert usuario.senha_hash not in resposta.text
        assert "senha" not in resposta.text.lower()


def test_ac_0001_24_login_local_desligavel(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0001-24 — desligado por configuração, a rota responde 404.

    404 e não 403: um mecanismo desligado deve ser indistinguível de um que
    nunca existiu, senão a própria recusa confirma que ele está lá.
    """
    usuario = criar_usuario()
    monkeypatch.setenv("LOCAL_LOGIN_ENABLED", "false")
    get_settings.cache_clear()

    desligado = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA})
    assert desligado.status_code == 404
    assert desligado.json()["error"]["code"] == "NAO_ENCONTRADO"

    monkeypatch.setenv("LOCAL_LOGIN_ENABLED", "true")
    get_settings.cache_clear()
    assert aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA}).status_code == 200


def test_corpo_malformado_usa_o_mesmo_envelope(aplicacao: TestClient) -> None:
    """`api-conventions.md` diz que erro *sempre* tem uma forma só; o 422 padrão
    do FastAPI tem outra, e um cliente que precisa entender duas não entende
    nenhuma."""
    resposta = aplicacao.post(LOGIN, json={"email": "nao-e-email", "senha": ""})
    assert resposta.status_code == 422
    erro = resposta.json()["error"]
    assert erro["code"] == "DADOS_INVALIDOS"
    assert set(erro["fields"]) == {"email", "senha"}
    assert erro["correlation_id"]
