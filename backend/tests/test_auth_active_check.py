"""AC-0001-08 — a desativação vale agora, não daqui a quinze minutos.

O critério parece pequeno e é o mais caro da spec: obriga uma consulta ao banco
em *toda* requisição autenticada. A alternativa — confiar só na assinatura —
deixa quem foi desativado com até quinze minutos de acesso pleno, e quinze
minutos é exatamente a janela em que alguém desligado às pressas ainda age.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seguranca import emitir_access_token
from app.models.usuario import Usuario
from tests.conftest import cookie_de, usar_refresh

ME = "/api/v1/auth/me"
SENHA = "SenhaCorreta-12345"


def _entrar(aplicacao: TestClient, usuario: Usuario) -> str:
    resposta = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert resposta.status_code == 200
    token: str = resposta.json()["access_token"]
    return token


def test_ac_0001_08_desativacao_vale_imediatamente(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    usuario = criar_usuario()
    token = _entrar(aplicacao, usuario)
    cabecalhos = {"Authorization": f"Bearer {token}"}
    assert aplicacao.get(ME, headers=cabecalhos).status_code == 200

    # Escrita direta porque a gestão de membros é o passo seguinte (AC-0001-12);
    # o que este critério observa é o efeito sobre o token já emitido.
    usuario.status = "desativado"
    usuario.nome = None
    usuario.email = None
    usuario.senha_hash = None
    usuario.anonimizado_em = datetime.datetime.now(datetime.UTC)
    sessao.commit()

    recusado = aplicacao.get(ME, headers=cabecalhos)
    assert recusado.status_code == 401
    assert recusado.json()["error"]["code"] == "USUARIO_INATIVO"


def test_ac_0001_08_bloqueio_tambem_vale_imediatamente(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    """`ativo` é gerado de `status`, então bloquear derruba pelo mesmo caminho —
    e é o caso que de fato acontece com uma conta comprometida."""
    usuario = criar_usuario()
    cabecalhos = {"Authorization": f"Bearer {_entrar(aplicacao, usuario)}"}

    usuario.status = "bloqueado"
    sessao.commit()

    assert aplicacao.get(ME, headers=cabecalhos).status_code == 401


def test_ac_0001_08_refresh_tambem_checa(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    """Renovar é uma decisão de autorização nova.

    Sem esta checagem a desativação seria imediata para `/me` e inútil na
    prática: o cliente renova sozinho e ganha mais quinze minutos do acesso que
    a desativação tirou.
    """
    usuario = criar_usuario()
    entrada = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    refresh = cookie_de(entrada, "sigi_refresh")
    assert refresh
    usar_refresh(aplicacao, refresh)

    usuario.status = "bloqueado"
    sessao.commit()

    recusado = aplicacao.post("/api/v1/auth/refresh")
    assert recusado.status_code == 401
    assert recusado.json()["error"]["code"] == "USUARIO_INATIVO"


def test_token_sem_conta_e_recusado(aplicacao: TestClient) -> None:
    """Assinatura nossa, `sub` que não existe: 401, não 500.

    Acontece de verdade depois de restaurar um backup antigo, e o modo de falha
    barato é o que decide se alguém investiga ou reinicia o serviço.
    """
    token = emitir_access_token(usuario_id=uuid.uuid4(), perfil="gestor")
    resposta = aplicacao.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "USUARIO_INATIVO"


def test_sem_cabecalho_authorization_e_401(aplicacao: TestClient) -> None:
    resposta = aplicacao.get(ME)
    assert resposta.status_code == 401
    assert resposta.json()["error"]["code"] == "TOKEN_INVALIDO"
