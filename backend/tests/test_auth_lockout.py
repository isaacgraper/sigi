"""AC-0001-03 — o bloqueio por tentativas, e o que ele esconde.

O critério tem duas metades e a segunda é a que quase se perde: o contador vive
no **endereço submetido**, não na conta. Na v0.3 ele vivia na conta, e por isso
um endereço inexistente não tinha contador — respondia 401 para sempre enquanto
um real virava 429. Seis requisições diziam quais endereços existem, que é
exatamente o que o AC-0001-02 proíbe. Por isso o teste do limiar está aqui.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.segredos import digerir
from app.models.usuario import Usuario

LOGIN = "/api/v1/auth/login"
SENHA = "SenhaCorreta-12345"
ERRADA = "senha-errada-mas-longa"


def _errar(aplicacao: TestClient, email: str, vezes: int) -> None:
    for _ in range(vezes):
        assert aplicacao.post(LOGIN, json={"email": email, "senha": ERRADA}).status_code == 401


def _envelhecer(sessao: Session, email: str, minutos: int) -> None:
    """Recuar o relógio da linha em vez de esperar.

    A janela é de quinze minutos; um teste que a espera de verdade custa quinze
    minutos e ninguém o roda. Recuar `ultima_em` e `bloqueado_ate` exercita o
    mesmo predicado que o tempo exercitaria.
    """
    sessao.rollback()
    sessao.execute(
        text(
            "UPDATE tentativa_login"
            " SET ultima_em = ultima_em - make_interval(mins => :m),"
            "     bloqueado_ate = bloqueado_ate - make_interval(mins => :m)"
            " WHERE email_hmac = :h"
        ),
        {"m": minutos, "h": digerir(email)},
    )
    sessao.commit()


def test_ac_0001_03_bloqueio_por_tentativas(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    usuario = criar_usuario()
    assert usuario.email
    _errar(aplicacao, usuario.email, 5)

    # A sexta, **com a senha certa**. Um bloqueio que a senha correta atravessa
    # avisa ao atacante o instante exato em que ele acertou.
    sexta = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA})
    assert sexta.status_code == 429
    erro = sexta.json()["error"]
    assert erro["code"] == "TENTATIVAS_EXCEDIDAS"
    assert "minutos" in erro["message"]
    # O "quando" precisa existir fora da frase em pt-BR: um 429 que só diz a
    # hora dentro do texto é um 429 que nenhum cliente consegue obedecer.
    assert sexta.headers["retry-after"] == "900"

    sessao.rollback()
    tentativas = sessao.execute(
        text(
            "SELECT dados_anteriores->>'tentativas' FROM historico_movimentacao"
            " WHERE acao = 'auth.bloqueio_tentativas' AND usuario_id = :uid"
        ),
        {"uid": usuario.id},
    ).scalar_one()
    assert tentativas == "5"

    _envelhecer(sessao, usuario.email, 16)
    liberado = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA})
    assert liberado.status_code == 200

    # E o sucesso zera a contagem: a próxima série começa do zero, senão a
    # quinta falha de amanhã seria a décima de hoje.
    sessao.rollback()
    restantes = sessao.execute(
        text("SELECT count(*) FROM tentativa_login WHERE email_hmac = :h"),
        {"h": digerir(usuario.email)},
    ).scalar_one()
    assert restantes == 0


def test_ac_0001_03_decaimento_da_janela(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """Quatro falhas antigas mais uma nova contam como *uma*, não como cinco.

    "Cinco em quinze minutos" e "cinco falhas, sempre" não são a mesma regra. A
    segunda tranca uma conta por erros espalhados ao longo de meses, que é o
    modo de falha que o `ultima_em` existe para evitar.
    """
    usuario = criar_usuario()
    assert usuario.email
    _errar(aplicacao, usuario.email, 4)
    _envelhecer(sessao, usuario.email, 16)

    quinta = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": ERRADA})
    assert quinta.status_code == 401

    sessao.rollback()
    contagem = sessao.execute(
        text("SELECT tentativas, bloqueado_ate FROM tentativa_login WHERE email_hmac = :h"),
        {"h": digerir(usuario.email)},
    ).one()
    assert contagem.tentativas == 1
    assert contagem.bloqueado_ate is None
    assert aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA}).status_code == 200


def test_ac_0001_02_no_limiar_o_desconhecido_responde_igual(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """A última linha do AC-0001-02, e a razão de o contador ter saído da conta.

    Contar tentativas não pode virar um oráculo: se um endereço real trava na
    sexta e um inexistente não trava nunca, contar até seis responde a pergunta
    que a mensagem de erro se recusa a responder.
    """
    usuario = criar_usuario()
    assert usuario.email
    cabecalhos = {"X-Correlation-Id": "018f3c2e-0000-4000-8000-00000000c0de"}

    for endereco in (usuario.email, "naoexiste-nunca@sc.gov.br"):
        _errar(aplicacao, endereco, 5)

    real = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA}, headers=cabecalhos)
    inexistente = aplicacao.post(
        LOGIN, json={"email": "naoexiste-nunca@sc.gov.br", "senha": SENHA}, headers=cabecalhos
    )

    assert real.status_code == inexistente.status_code == 429
    assert real.content == inexistente.content


def test_conta_inativa_com_senha_certa_nao_conta_tentativa(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """Ninguém está adivinhando nada: a senha estava certa.

    Contar isso trancaria justamente quem vai pedir ao gestor para desbloquear,
    e por quinze minutos a cada tentativa de entender o que houve.
    """
    usuario = criar_usuario(status="bloqueado")
    assert usuario.email
    for _ in range(6):
        resposta = aplicacao.post(LOGIN, json={"email": usuario.email, "senha": SENHA})
        assert resposta.status_code == 401
        assert resposta.json()["error"]["code"] == "USUARIO_INATIVO"

    sessao.rollback()
    assert (
        sessao.execute(
            text("SELECT count(*) FROM tentativa_login WHERE email_hmac = :h"),
            {"h": digerir(usuario.email)},
        ).scalar_one()
        == 0
    )
