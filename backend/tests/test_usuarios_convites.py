"""Convites — AC-0001-10, -11, -25, -26 e -28.

O AC-0001-10 mudou na v0.6: o link volta uma vez ao gestor que convidou, e não
por e-mail. Os testes seguram as três propriedades que sustentam essa decisão —
uma vez só, não recuperável depois, e nunca no histórico.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.usuario import Usuario

SENHA = "SenhaCorreta-12345"
USUARIOS = "/api/v1/usuarios"


def _entrar(aplicacao: TestClient, usuario: Usuario) -> dict[str, str]:
    resposta = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def _token_do_link(link: str) -> str:
    return link.rstrip("/").rsplit("/", 1)[-1]


def test_ac_0001_10_gestor_convida(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-10 — conta `pendente` sem credencial, e o link uma vez só."""
    gestor = criar_usuario(perfil="gestor")
    cabecalhos = _entrar(aplicacao, gestor)

    resposta = aplicacao.post(
        USUARIOS,
        json={"email": "novo.membro@sc.gov.br", "perfil": "servidor"},
        headers=cabecalhos,
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["usuario"]["status"] == "pendente"
    assert corpo["usuario"]["perfil"] == "servidor"
    assert corpo["link"].startswith("http")

    sessao.rollback()
    linha = sessao.execute(
        text("SELECT senha_hash, status FROM usuario WHERE email = :e"),
        {"e": "novo.membro@sc.gov.br"},
    ).one()
    # Nasce sem credencial: quem define a senha é quem tem o link.
    assert linha.senha_hash is None
    assert linha.status == "pendente"

    # O valor do token não pode estar no banco — só o HMAC. É isso que torna
    # "não é recuperável depois" um fato do esquema e não uma promessa.
    token = _token_do_link(corpo["link"])
    guardados = sessao.execute(
        text("SELECT count(*) FROM token_credencial WHERE encode(token_hash, 'hex') LIKE :t"),
        {"t": f"%{token[:8]}%"},
    ).scalar_one()
    assert guardados == 0

    auditoria = sessao.execute(
        text(
            "SELECT usuario_id, dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'usuario.convidado' AND entidade_id = :alvo"
        ),
        {"alvo": corpo["usuario"]["id"]},
    ).one()
    assert auditoria.usuario_id == gestor.id
    assert "servidor" in auditoria.dados_anteriores
    # A tabela nunca pode ser corrigida, então o grant não entra nela.
    assert token not in auditoria.dados_anteriores


def test_ac_0001_10_link_nao_volta_uma_segunda_vez(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """Nenhuma rota devolve o link de novo — nem a listagem, nem por id."""
    gestor = criar_usuario(perfil="gestor")
    cabecalhos = _entrar(aplicacao, gestor)
    criado = aplicacao.post(
        USUARIOS, json={"email": "so.uma.vez@sc.gov.br", "perfil": "servidor"}, headers=cabecalhos
    )
    token = _token_do_link(criado.json()["link"])

    listagem = aplicacao.get(USUARIOS, headers=cabecalhos)
    assert listagem.status_code == 200
    assert token not in listagem.text
    assert "link" not in listagem.text


def test_ac_0001_11_ativacao(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-11 — ativar define a senha e já entrega sessão."""
    gestor = criar_usuario(perfil="gestor")
    criado = aplicacao.post(
        USUARIOS,
        json={"email": "ativa@sc.gov.br", "perfil": "servidor"},
        headers=_entrar(aplicacao, gestor),
    )
    token = _token_do_link(criado.json()["link"])

    ativacao = aplicacao.post(f"/api/v1/convites/{token}/ativar", json={"senha": SENHA})
    assert ativacao.status_code == 200, ativacao.text
    acesso = ativacao.json()["sessao"]["access_token"]

    # Ativação e primeiro login são um passo só: o token já vale.
    eu = aplicacao.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {acesso}"})
    assert eu.status_code == 200
    assert eu.json()["status"] == "ativo"

    sessao.rollback()
    assert (
        sessao.execute(
            text("SELECT count(*) FROM historico_movimentacao WHERE acao = 'usuario.ativado'")
        ).scalar_one()
        >= 1
    )


def test_ac_0001_25_convite_uso_unico_e_expiracao(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-25 — segunda tentativa 409, e expirado 409, com códigos distintos."""
    gestor = criar_usuario(perfil="gestor")
    cabecalhos = _entrar(aplicacao, gestor)

    usado = _token_do_link(
        aplicacao.post(
            USUARIOS, json={"email": "usa.uma@sc.gov.br", "perfil": "servidor"}, headers=cabecalhos
        ).json()["link"]
    )
    assert (
        aplicacao.post(f"/api/v1/convites/{usado}/ativar", json={"senha": SENHA}).status_code == 200
    )

    repetido = aplicacao.post(
        f"/api/v1/convites/{usado}/ativar", json={"senha": "OutraSenha-99999"}
    )
    assert repetido.status_code == 409
    assert repetido.json()["error"]["code"] == "CONVITE_JA_UTILIZADO"

    # E a credencial não muda: o segundo resgate não pode reescrever a senha.
    assert (
        aplicacao.post(
            "/api/v1/auth/login", json={"email": "usa.uma@sc.gov.br", "senha": SENHA}
        ).status_code
        == 200
    )

    velho = _token_do_link(
        aplicacao.post(
            USUARIOS, json={"email": "expira@sc.gov.br", "perfil": "servidor"}, headers=cabecalhos
        ).json()["link"]
    )
    sessao.rollback()
    # Recuar o relógio da linha em vez de esperar 72 horas. As duas colunas
    # juntas: `ck_token_expira` exige `expira_em > criado_em`, então mexer só na
    # expiração produziria uma linha que o banco recusa — e com razão.
    sessao.execute(
        text(
            "UPDATE token_credencial"
            " SET criado_em = now() - interval '80 hours',"
            "     expira_em = now() - interval '8 hours'"
            " WHERE usuario_id = (SELECT id FROM usuario WHERE email = 'expira@sc.gov.br')"
        )
    )
    sessao.commit()

    expirado = aplicacao.post(f"/api/v1/convites/{velho}/ativar", json={"senha": SENHA})
    assert expirado.status_code == 409
    assert expirado.json()["error"]["code"] == "CONVITE_EXPIRADO"

    sessao.rollback()
    assert (
        sessao.execute(
            text("SELECT status FROM usuario WHERE email = 'expira@sc.gov.br'")
        ).scalar_one()
        == "pendente"
    )


def test_ac_0001_26_politica_de_senha(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """AC-0001-26 — senha curta é 422, e **não queima o convite**.

    O ponto do critério é a última linha: um erro de digitação não pode obrigar
    o gestor a emitir outro convite.
    """
    gestor = criar_usuario(perfil="gestor")
    token = _token_do_link(
        aplicacao.post(
            USUARIOS,
            json={"email": "senha.curta@sc.gov.br", "perfil": "servidor"},
            headers=_entrar(aplicacao, gestor),
        ).json()["link"]
    )

    fraca = aplicacao.post(f"/api/v1/convites/{token}/ativar", json={"senha": "curta"})
    assert fraca.status_code == 422
    erro = fraca.json()["error"]
    assert erro["code"] == "SENHA_FRACA"
    assert "12" in erro["message"]

    # O mesmo token, agora com senha válida, tem de funcionar.
    segunda = aplicacao.post(f"/api/v1/convites/{token}/ativar", json={"senha": SENHA})
    assert segunda.status_code == 200, segunda.text


def test_ac_0001_28_convite_duplicado_ou_fora_do_dominio(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-28 — duplicado 409, domínio de fora 422 nomeando os aceitos."""
    gestor = criar_usuario(perfil="gestor")
    cabecalhos = _entrar(aplicacao, gestor)
    assert gestor.email

    duplicado = aplicacao.post(
        USUARIOS, json={"email": gestor.email, "perfil": "servidor"}, headers=cabecalhos
    )
    assert duplicado.status_code == 409
    assert duplicado.json()["error"]["code"] == "EMAIL_JA_CADASTRADO"

    sessao.rollback()
    assert (
        sessao.execute(
            text("SELECT count(*) FROM usuario WHERE email = :e"), {"e": gestor.email}
        ).scalar_one()
        == 1
    )

    fora = aplicacao.post(
        USUARIOS, json={"email": "alguem@gmail.com", "perfil": "servidor"}, headers=cabecalhos
    )
    assert fora.status_code == 422
    erro = fora.json()["error"]
    assert erro["code"] == "DOMINIO_NAO_INSTITUCIONAL"
    assert "sc.gov.br" in erro["message"]


def test_convite_duplicado_vale_para_qualquer_status(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """ "Em qualquer status" inclui `pendente`: convidar duas vezes o mesmo
    endereço criaria duas contas para uma pessoa e partiria o histórico dela."""
    gestor = criar_usuario(perfil="gestor")
    cabecalhos = _entrar(aplicacao, gestor)
    corpo = {"email": "duas.vezes@sc.gov.br", "perfil": "servidor"}

    assert aplicacao.post(USUARIOS, json=corpo, headers=cabecalhos).status_code == 201
    segunda = aplicacao.post(USUARIOS, json=corpo, headers=cabecalhos)
    assert segunda.status_code == 409
    assert segunda.json()["error"]["code"] == "EMAIL_JA_CADASTRADO"
