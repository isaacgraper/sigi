"""Invitations — AC-0001-10, -11, -25, -26 and -28.

AC-0001-10 changed in v0.6: the link goes back once to the inviting gestor
rather than by e-mail. These tests hold the three properties that decision rests
on — once only, not recoverable afterwards, and never in the audit trail.
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
    response = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _token_do_link(link: str) -> str:
    return link.rstrip("/").rsplit("/", 1)[-1]


def test_ac_0001_10_gestor_convida(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-10 — a `pendente` account with no credential, and the link once."""
    gestor = criar_usuario(perfil="gestor")
    headers = _entrar(aplicacao, gestor)

    response = aplicacao.post(
        USUARIOS,
        json={"email": "novo.membro@sc.gov.br", "perfil": "servidor"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["usuario"]["status"] == "pendente"
    assert body["usuario"]["perfil"] == "servidor"
    assert body["link"].startswith("http")

    sessao.rollback()
    linha = sessao.execute(
        text("SELECT senha_hash, status FROM usuario WHERE email = :e"),
        {"e": "novo.membro@sc.gov.br"},
    ).one()
    # Born with no credential: whoever holds the link sets the senha.
    assert linha.senha_hash is None
    assert linha.status == "pendente"

    # The token value must not be in the database — only its HMAC. That is
    # what makes "not recoverable afterwards" a fact about the schema rather
    # than a promise.
    token = _token_do_link(body["link"])
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
        {"alvo": body["usuario"]["id"]},
    ).one()
    assert auditoria.usuario_id == gestor.id
    assert "servidor" in auditoria.dados_anteriores
    # The table can never be corrected, so the grant does not go into it.
    assert token not in auditoria.dados_anteriores


def test_ac_0001_10_link_nao_volta_uma_segunda_vez(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """No route returns the link a second time — not the listing, not by id."""
    gestor = criar_usuario(perfil="gestor")
    headers = _entrar(aplicacao, gestor)
    criado = aplicacao.post(
        USUARIOS, json={"email": "so.uma.vez@sc.gov.br", "perfil": "servidor"}, headers=headers
    )
    token = _token_do_link(criado.json()["link"])

    listagem = aplicacao.get(USUARIOS, headers=headers)
    assert listagem.status_code == 200
    assert token not in listagem.text
    assert "link" not in listagem.text


def test_ac_0001_11_ativacao(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-11 — activation sets the senha and issues a session."""
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

    # Activation and first login are one step: the token already works.
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
    """AC-0001-25 — a second attempt is 409, an expired one 409, distinct codes."""
    gestor = criar_usuario(perfil="gestor")
    headers = _entrar(aplicacao, gestor)

    usado = _token_do_link(
        aplicacao.post(
            USUARIOS, json={"email": "usa.uma@sc.gov.br", "perfil": "servidor"}, headers=headers
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

    # And the credential is unchanged: a second redemption must not rewrite it.
    assert (
        aplicacao.post(
            "/api/v1/auth/login", json={"email": "usa.uma@sc.gov.br", "senha": SENHA}
        ).status_code
        == 200
    )

    velho = _token_do_link(
        aplicacao.post(
            USUARIOS, json={"email": "expira@sc.gov.br", "perfil": "servidor"}, headers=headers
        ).json()["link"]
    )
    sessao.rollback()
    # Wind the row's clock back instead of waiting 72 hours. Both columns
    # together: `ck_token_expira` requires `expira_em > criado_em`, so moving
    # only the expiry would produce a row the database refuses — rightly.
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
    """AC-0001-26 — a short senha is 422, and **does not burn the invitation**.

    The point of the criterion is its last line: a typo must not force the
    gestor to issue another invitation.
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

    # The same token, now with a valid senha, has to work.
    segunda = aplicacao.post(f"/api/v1/convites/{token}/ativar", json={"senha": SENHA})
    assert segunda.status_code == 200, segunda.text


def test_ac_0001_28_convite_duplicado_ou_fora_do_dominio(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-28 — a duplicate is 409, an off-domain address 422 naming those accepted."""
    gestor = criar_usuario(perfil="gestor")
    headers = _entrar(aplicacao, gestor)
    assert gestor.email

    duplicado = aplicacao.post(
        USUARIOS, json={"email": gestor.email, "perfil": "servidor"}, headers=headers
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
        USUARIOS, json={"email": "alguem@gmail.com", "perfil": "servidor"}, headers=headers
    )
    assert fora.status_code == 422
    erro = fora.json()["error"]
    assert erro["code"] == "DOMINIO_NAO_INSTITUCIONAL"
    assert "sc.gov.br" in erro["message"]


def test_convite_duplicado_vale_para_qualquer_status(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario]
) -> None:
    """ "In any status" includes `pendente`: inviting the same address twice
    would create two accounts for one person and split their history."""
    gestor = criar_usuario(perfil="gestor")
    headers = _entrar(aplicacao, gestor)
    body = {"email": "duas.vezes@sc.gov.br", "perfil": "servidor"}

    assert aplicacao.post(USUARIOS, json=body, headers=headers).status_code == 201
    segunda = aplicacao.post(USUARIOS, json=body, headers=headers)
    assert segunda.status_code == 409
    assert segunda.json()["error"]["code"] == "EMAIL_JA_CADASTRADO"
