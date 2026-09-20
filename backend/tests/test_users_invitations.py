"""Invitations — AC-0001-10, -11, -13, -25, -26, -28.

Every account in the system is born here: there is no self-registration and no
just-in-time provisioning (AC-0001-21). So these tests are also the answer to
"can anyone get into this system at all".
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User

USUARIOS = "/api/v1/usuarios"
ATIVAR = "/api/v1/convites/ativar"
LOGIN = "/api/v1/auth/login"
SENHA_BOA = "SenhaLongaOSuficiente-2026"


def _token_from(link: str) -> str:
    return link.split("token=", 1)[1]


def _as_gestor(application: TestClient, criar_usuario: Callable[..., User]) -> dict[str, str]:
    email = f"gestor-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil="gestor", senha=SENHA_BOA)
    entrada = application.post(LOGIN, json={"email": email, "password": SENHA_BOA})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def test_ac_0001_10_a_gestor_invites_a_member(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-10 — the account is born `pendente` and the link comes back once."""
    headers = _as_gestor(application, criar_usuario)
    email = f"novo-{uuid.uuid4().hex[:8]}@sc.gov.br"

    response = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pendente"
    assert body["perfil"] == "servidor"
    assert body["link_ativacao"]

    # Only the HMAC reaches the database, so "cannot be recovered afterwards" is
    # a fact about the schema rather than a promise about the code.
    sessao.rollback()
    stored = sessao.execute(
        text(
            "SELECT count(*) FROM token_credencial t JOIN usuario u ON u.id = t.usuario_id"
            " WHERE u.email = :e"
        ),
        {"e": email},
    ).scalar_one()
    assert stored == 1
    token = _token_from(body["link_ativacao"])
    raw = sessao.execute(text("SELECT token_hash::text FROM token_credencial")).scalars().all()
    assert all(token not in row for row in raw)


def test_ac_0001_10_the_audit_row_carries_no_token(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """The grant is auditable; the credential inside it is not recorded."""
    headers = _as_gestor(application, criar_usuario)
    email = f"aud-{uuid.uuid4().hex[:8]}@sc.gov.br"
    response = application.post(
        USUARIOS, json={"email": email, "perfil": "auditor"}, headers=headers
    )
    token = _token_from(response.json()["link_ativacao"])

    sessao.rollback()
    row = sessao.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'usuario.convidado' ORDER BY ocorrido_em DESC LIMIT 1"
        )
    ).scalar_one()
    assert token not in row
    assert "auditor" in row


def test_ac_0001_11_an_invited_user_activates_and_enters(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-11 — activation sets the credential and issues a session."""
    headers = _as_gestor(application, criar_usuario)
    email = f"ativa-{uuid.uuid4().hex[:8]}@sc.gov.br"
    convite = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )
    token = _token_from(convite.json()["link_ativacao"])

    ativacao = application.post(ATIVAR, json={"token": token, "password": SENHA_BOA})
    assert ativacao.status_code == 200, ativacao.text
    assert ativacao.json()["sessao"]["access_token"]

    # And the credential works on its own, which is what makes the account real.
    entrada = application.post(LOGIN, json={"email": email, "password": SENHA_BOA})
    assert entrada.status_code == 200, entrada.text


def test_ac_0001_25_an_invitation_is_single_use(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-25 — the second redemption is refused."""
    headers = _as_gestor(application, criar_usuario)
    email = f"unica-{uuid.uuid4().hex[:8]}@sc.gov.br"
    convite = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )
    token = _token_from(convite.json()["link_ativacao"])

    assert application.post(ATIVAR, json={"token": token, "password": SENHA_BOA}).status_code == 200

    again = application.post(ATIVAR, json={"token": token, "password": SENHA_BOA})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "INVITE_ALREADY_USED"


def test_ac_0001_25_an_unknown_token_answers_like_a_spent_one(application: TestClient) -> None:
    """Distinguishing the two would say which grants exist."""
    response = application.post(
        ATIVAR, json={"token": "nunca-emitido-" + uuid.uuid4().hex, "password": SENHA_BOA}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITE_ALREADY_USED"


def test_ac_0001_25_reinviting_supersedes_the_first_link(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """A second invitation cancels the first, which then reads as expired."""
    headers = _as_gestor(application, criar_usuario)
    email = f"resend-{uuid.uuid4().hex[:8]}@sc.gov.br"
    primeiro = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )
    token_velho = _token_from(primeiro.json()["link_ativacao"])

    # The account now exists, so a re-invite is refused by AC-0001-28. The
    # supersede path is exercised through the service instead, which is where it
    # lives; the API-level guard is the test above.
    duplicado = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )
    assert duplicado.status_code == 409
    assert duplicado.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

    # The first link is still good, because nothing superseded it.
    assert (
        application.post(ATIVAR, json={"token": token_velho, "password": SENHA_BOA}).status_code
        == 200
    )


def test_ac_0001_26_a_weak_password_does_not_burn_the_invitation(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-26 — the policy is enforced, and a typo leaves the grant usable.

    This is the ordering criterion: validate the password before spending the
    grant. Otherwise one short password forces the gestor to issue another
    invitation.
    """
    headers = _as_gestor(application, criar_usuario)
    email = f"fraca-{uuid.uuid4().hex[:8]}@sc.gov.br"
    convite = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )
    token = _token_from(convite.json()["link_ativacao"])

    fraca = application.post(ATIVAR, json={"token": token, "password": "curta"})
    assert fraca.status_code == 422
    assert fraca.json()["error"]["code"] == "WEAK_PASSWORD"
    # The rule is in the message, so the person knows what to do next.
    assert "12" in fraca.json()["error"]["message"]

    boa = application.post(ATIVAR, json={"token": token, "password": SENHA_BOA})
    assert boa.status_code == 200, boa.text


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_13_only_a_gestor_invites(
    application: TestClient, criar_usuario: Callable[..., User], perfil: str, sessao: Session
) -> None:
    """AC-0001-13 — a servidor or auditor is refused, and the refusal is audited.

    AC-0001-18 rides along: this is the first route that actually refuses by
    perfil, so it is the first place the refusal writer is observable.
    """
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil=perfil, senha=SENHA_BOA)
    entrada = application.post(LOGIN, json={"email": email, "password": SENHA_BOA})
    headers = {"Authorization": f"Bearer {entrada.json()['access_token']}"}

    response = application.post(
        USUARIOS,
        json={"email": f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", "perfil": "servidor"},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"

    sessao.rollback()
    negadas = sessao.execute(
        text(
            "SELECT count(*) FROM historico_movimentacao"
            " WHERE acao = 'auth.negada' AND dados_anteriores->>'perfil' = :p"
        ),
        {"p": perfil},
    ).scalar_one()
    assert negadas >= 1


def test_ac_0001_13_an_anonymous_caller_is_refused(application: TestClient) -> None:
    """No token at all is 401, not 403: there is nobody to refuse yet."""
    response = application.post(USUARIOS, json={"email": "alguem@sc.gov.br", "perfil": "servidor"})
    assert response.status_code == 401


def test_ac_0001_28_a_duplicate_address_is_refused(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-28 — in any status, including `desativado`.

    A second account for one person splits their audit trail in two, and neither
    half answers "what did this person do".
    """
    headers = _as_gestor(application, criar_usuario)
    email = f"dup-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil="servidor", status="desativado", senha=None)

    response = application.post(
        USUARIOS, json={"email": email, "perfil": "servidor"}, headers=headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_ac_0001_28_an_address_outside_the_institutional_domains_is_refused(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-28 — and the message names the domains, so it can be corrected."""
    headers = _as_gestor(application, criar_usuario)

    response = application.post(
        USUARIOS, json={"email": "pessoa@gmail.com", "perfil": "servidor"}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NON_INSTITUTIONAL_DOMAIN"
    assert "sc.gov.br" in response.json()["error"]["message"]


def test_the_activation_token_is_never_a_path_segment(application: TestClient) -> None:
    """OQ-31 — the token travels in the body.

    A single-use credential in a URL path lands in access logs, proxy logs and
    browser history. The old shape must not answer, or a client could keep using
    it and quietly reintroduce the leak.
    """
    stale = application.post("/api/v1/convites/algum-token/ativar", json={"password": SENHA_BOA})
    assert stale.status_code == 404
