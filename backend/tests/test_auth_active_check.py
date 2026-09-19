"""AC-0001-08 — deactivation takes effect now, not in fifteen minutes.

The criterion looks small and is the most expensive in the spec: it forces a
database lookup on *every* authenticated request. The alternative — trusting the
signature alone — leaves a deactivated person with up to fifteen minutes of full
access, and fifteen minutes is exactly the window in which somebody cut off in a
hurry still acts.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seguranca import issue_access_token
from app.models.usuario import Usuario
from tests.conftest import cookie_de, usar_refresh

ME = "/api/v1/auth/me"
SENHA = "SenhaCorreta-12345"


def _entrar(aplicacao: TestClient, usuario: Usuario) -> str:
    response = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return token


def test_ac_0001_08_desativacao_vale_imediatamente(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    """AC-0001-08 deactivation bites at once, not when the token expires."""
    usuario = criar_usuario()
    token = _entrar(aplicacao, usuario)
    headers = {"Authorization": f"Bearer {token}"}
    assert aplicacao.get(ME, headers=headers).status_code == 200

    # Written directly because member management is the next step (AC-0001-12);
    # what this criterion observes is the effect on the token already issued.
    usuario.status = "desativado"
    usuario.nome = None
    usuario.email = None
    usuario.senha_hash = None
    usuario.anonimizado_em = datetime.datetime.now(datetime.UTC)
    sessao.commit()

    recusado = aplicacao.get(ME, headers=headers)
    assert recusado.status_code == 401
    assert recusado.json()["error"]["code"] == "USUARIO_INATIVO"


def test_ac_0001_08_bloqueio_tambem_vale_imediatamente(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    """Blocking an account kills its live token too.

    `ativo` is generated from `status`, so blocking closes it by the same path,
    and that is the case that actually happens to a compromised account.
    """
    usuario = criar_usuario()
    headers = {"Authorization": f"Bearer {_entrar(aplicacao, usuario)}"}

    usuario.status = "bloqueado"
    sessao.commit()

    assert aplicacao.get(ME, headers=headers).status_code == 401


def test_ac_0001_08_refresh_tambem_checa(
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
    sessao: Session,
) -> None:
    """A refresh is a fresh authorisation decision.

    Without this check the deactivation would be immediate for `/me` and useless
    in practice: the client refreshes on its own and gains another fifteen
    minutes of exactly the access the deactivation removed.
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
    """Our own signature, a `sub` that does not exist: 401, not 500.

    It really happens after restoring an old backup, and the cheap failure mode
    is what decides whether somebody investigates or restarts the service.
    """
    token = issue_access_token(usuario_id=uuid.uuid4(), perfil="gestor")
    response = aplicacao.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "USUARIO_INATIVO"


def test_sem_cabecalho_authorization_e_401(aplicacao: TestClient) -> None:
    """A request with no Authorization header is 401."""
    response = aplicacao.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALIDO"
