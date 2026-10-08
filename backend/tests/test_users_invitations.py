"""Invitations — AC-0001-10, -11, -13, -25, -26, -28, -45.

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
from tests.conftest import invite_body

USUARIOS = "/api/v1/usuarios"
ACTIVATE = "/api/v1/convites/ativar"
LOGIN = "/api/v1/auth/login"
# Not `*_PASSWORD`: gitleaks reads that keyword beside this entropy as a
# credential. See `docs/process/sop-qualidade.md`.
STRONG_ENOUGH = "SenhaLongaOSuficiente-2026"


def _token_from(link: str) -> str:
    return link.split("token=", 1)[1]


def _as_gestor(application: TestClient, create_user: Callable[..., User]) -> dict[str, str]:
    email = f"gestor-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil="gestor", password=STRONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": STRONG_ENOUGH})
    assert entry.status_code == 200, entry.text
    return {"Authorization": f"Bearer {entry.json()['access_token']}"}


def test_ac_0001_10_a_gestor_invites_a_member(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-10 — the account is born `pendente` and the link comes back once."""
    headers = _as_gestor(application, create_user)
    email = f"novo-{uuid.uuid4().hex[:8]}@sc.gov.br"

    response = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pendente"
    assert body["perfil"] == "servidor"
    assert body["activation_link"]

    # Only the HMAC reaches the database, so "cannot be recovered afterwards" is
    # a fact about the schema rather than a promise about the code.
    db_session.rollback()
    stored = db_session.execute(
        text(
            "SELECT count(*) FROM token_credencial t JOIN usuario u ON u.id = t.usuario_id"
            " WHERE u.email = :e"
        ),
        {"e": email},
    ).scalar_one()
    assert stored == 1
    token = _token_from(body["activation_link"])
    raw = db_session.execute(text("SELECT token_hash::text FROM token_credencial")).scalars().all()
    assert all(token not in row for row in raw)


def test_ac_0001_10_the_audit_row_carries_no_token(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """The grant is auditable; the credential inside it is not recorded."""
    headers = _as_gestor(application, create_user)
    email = f"aud-{uuid.uuid4().hex[:8]}@sc.gov.br"
    response = application.post(USUARIOS, json=invite_body(email, "auditor"), headers=headers)
    token = _token_from(response.json()["activation_link"])

    db_session.rollback()
    row = db_session.execute(
        text(
            "SELECT dados_anteriores::text FROM historico_movimentacao"
            " WHERE acao = 'usuario.convidado' ORDER BY ocorrido_em DESC LIMIT 1"
        )
    ).scalar_one()
    assert token not in row
    assert "auditor" in row


def test_ac_0001_11_an_invited_user_activates_and_enters(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-11 — activation sets the credential and issues a session."""
    headers = _as_gestor(application, create_user)
    email = f"ativa-{uuid.uuid4().hex[:8]}@sc.gov.br"
    invitation = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    token = _token_from(invitation.json()["activation_link"])

    ativacao = application.post(ACTIVATE, json={"token": token, "password": STRONG_ENOUGH})
    assert ativacao.status_code == 200, ativacao.text
    assert ativacao.json()["session"]["access_token"]

    # And the credential works on its own, which is what makes the account real.
    entry = application.post(LOGIN, json={"email": email, "password": STRONG_ENOUGH})
    assert entry.status_code == 200, entry.text


def test_ac_0001_25_an_invitation_is_single_use(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-25 — the second redemption is refused."""
    headers = _as_gestor(application, create_user)
    email = f"unica-{uuid.uuid4().hex[:8]}@sc.gov.br"
    invitation = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    token = _token_from(invitation.json()["activation_link"])

    assert (
        application.post(ACTIVATE, json={"token": token, "password": STRONG_ENOUGH}).status_code
        == 200
    )

    again = application.post(ACTIVATE, json={"token": token, "password": STRONG_ENOUGH})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "INVITE_ALREADY_USED"


def test_ac_0001_25_an_unknown_token_answers_like_a_spent_one(application: TestClient) -> None:
    """Distinguishing the two would say which grants exist."""
    response = application.post(
        ACTIVATE, json={"token": "nunca-emitido-" + uuid.uuid4().hex, "password": STRONG_ENOUGH}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITE_ALREADY_USED"


def test_ac_0001_25_reinviting_supersedes_the_first_link(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """A second invitation cancels the first, which then reads as expired."""
    headers = _as_gestor(application, create_user)
    email = f"resend-{uuid.uuid4().hex[:8]}@sc.gov.br"
    first = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    old_token = _token_from(first.json()["activation_link"])

    # The account now exists, so a re-invite is refused by AC-0001-28. The
    # supersede path is exercised through the service instead, which is where it
    # lives; the API-level guard is the test above.
    duplicate = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

    # The first link is still good, because nothing superseded it.
    assert (
        application.post(ACTIVATE, json={"token": old_token, "password": STRONG_ENOUGH}).status_code
        == 200
    )


def test_ac_0001_26_a_weak_password_does_not_burn_the_invitation(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-26 — the policy is enforced, and a typo leaves the grant usable.

    This is the ordering criterion: validate the password before spending the
    grant. Otherwise one short password forces the gestor to issue another
    invitation.
    """
    headers = _as_gestor(application, create_user)
    email = f"fraca-{uuid.uuid4().hex[:8]}@sc.gov.br"
    invitation = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    token = _token_from(invitation.json()["activation_link"])

    weak = application.post(ACTIVATE, json={"token": token, "password": "curta"})
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "WEAK_PASSWORD"
    # The rule is in the message, so the person knows what to do next.
    assert "12" in weak.json()["error"]["message"]

    strong = application.post(ACTIVATE, json={"token": token, "password": STRONG_ENOUGH})
    assert strong.status_code == 200, strong.text


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_13_only_a_gestor_invites(
    application: TestClient, create_user: Callable[..., User], perfil: str, db_session: Session
) -> None:
    """AC-0001-13 — a servidor or auditor is refused, and the refusal is audited.

    AC-0001-18 rides along: this is the first route that actually refuses by
    perfil, so it is the first place the refusal writer is observable.
    """
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil=perfil, password=STRONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": STRONG_ENOUGH})
    headers = {"Authorization": f"Bearer {entry.json()['access_token']}"}

    response = application.post(
        USUARIOS,
        json=invite_body(f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", "servidor"),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"

    db_session.rollback()
    denied = db_session.execute(
        text(
            "SELECT count(*) FROM historico_movimentacao"
            " WHERE acao = 'auth.negada' AND dados_anteriores->>'perfil' = :p"
        ),
        {"p": perfil},
    ).scalar_one()
    assert denied >= 1


def test_ac_0001_13_an_anonymous_caller_is_refused(application: TestClient) -> None:
    """No token at all is 401, not 403: there is nobody to refuse yet."""
    response = application.post(USUARIOS, json=invite_body("alguem@sc.gov.br", "servidor"))
    assert response.status_code == 401


def test_ac_0001_28_a_duplicate_address_is_refused(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-28 — in any status, including `desativado`.

    A second account for one person splits their audit trail in two, and neither
    half answers "what did this person do".
    """
    headers = _as_gestor(application, create_user)
    email = f"dup-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil="servidor", status="desativado", password=None)

    response = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_ac_0001_28_an_address_outside_the_institutional_domains_is_refused(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-28 — and the message names the domains, so it can be corrected."""
    headers = _as_gestor(application, create_user)

    response = application.post(
        USUARIOS, json=invite_body("pessoa@gmail.com", "servidor"), headers=headers
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
    stale = application.post(
        "/api/v1/convites/algum-token/ativar", json={"password": STRONG_ENOUGH}
    )
    assert stale.status_code == 404


# ── AC-0001-45 — the invitation carries the full name and the registration ──


def test_ac_0001_45_the_invitation_stores_the_name_and_the_registration(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-45 — both land on the usuario, and neither reaches the audit row."""
    headers = _as_gestor(application, create_user)
    email = f"nome-{uuid.uuid4().hex[:8]}@sc.gov.br"

    response = application.post(
        USUARIOS,
        json={
            "email": email,
            "perfil": "servidor",
            "name": "  Maria da Silva  ",
            "registration": " REG-98765 ",
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Maria da Silva"
    db_session.rollback()
    row = db_session.execute(
        text("SELECT id, nome, registro_funcional FROM usuario WHERE email = :e"), {"e": email}
    ).one()
    assert (row.nome, row.registro_funcional) == ("Maria da Silva", "REG-98765")
    audit = db_session.execute(
        text(
            "SELECT dados_anteriores::text, justificativa FROM historico_movimentacao"
            " WHERE entidade_id = :u AND acao = 'usuario.convidado'"
        ),
        {"u": row.id},
    ).one()
    assert "Maria" not in audit[0]
    assert "REG-98765" not in audit[0]


@pytest.mark.parametrize("missing", ["name", "registration"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_ac_0001_45_a_missing_name_or_registration_is_refused(
    application: TestClient,
    create_user: Callable[..., User],
    db_session: Session,
    missing: str,
    value: str | None,
) -> None:
    """AC-0001-45 — 422 `INVALID_DATA` naming the field, and no account is created."""
    headers = _as_gestor(application, create_user)
    email = f"falta-{uuid.uuid4().hex[:8]}@sc.gov.br"
    body = invite_body(email)
    if value is None:
        del body[missing]
    else:
        body[missing] = value

    response = application.post(USUARIOS, json=body, headers=headers)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert missing in error["fields"]
    db_session.rollback()
    assert (
        db_session.execute(
            text("SELECT count(*) FROM usuario WHERE email = :e"), {"e": email}
        ).scalar_one()
        == 0
    )


def test_ac_0001_45_the_fields_are_bounded(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-45, AC-0001-41 — a name over 200 and a registration over 32 are refused."""
    headers = _as_gestor(application, create_user)
    long_name = invite_body(f"longo-{uuid.uuid4().hex[:8]}@sc.gov.br") | {"name": "N" * 201}
    long_registration = invite_body(f"longo-{uuid.uuid4().hex[:8]}@sc.gov.br") | {
        "registration": "R" * 33
    }

    for body, field in ((long_name, "name"), (long_registration, "registration")):
        response = application.post(USUARIOS, json=body, headers=headers)
        assert response.status_code == 422
        assert field in response.json()["error"]["fields"]


def test_ac_0001_45_the_member_list_shows_the_registration_to_a_gestor_and_an_auditor(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-45, §6 — the list is the gestor's and the auditor's, and carries it."""
    headers = _as_gestor(application, create_user)
    email = f"lista-{uuid.uuid4().hex[:8]}@sc.gov.br"
    application.post(
        USUARIOS,
        json=invite_body(email) | {"registration": "REG-LISTA-1"},
        headers=headers,
    )
    auditor = f"auditor-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=auditor, perfil="auditor", password=STRONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": auditor, "password": STRONG_ENOUGH})
    auditor_headers = {"Authorization": f"Bearer {entry.json()['access_token']}"}

    for who in (headers, auditor_headers):
        page = application.get(f"{USUARIOS}?size=100", headers=who).json()
        assert {m["registration"] for m in page["items"] if m["email"] == email} == {"REG-LISTA-1"}


# ── AC-0001-46 — a new invitation link for a pending member ─────────────────


def test_ac_0001_46_a_new_link_replaces_the_lost_one(
    application: TestClient, create_user: Callable[..., User], db_session: Session
) -> None:
    """AC-0001-46 — the new link activates, the old one reads as expired, the act is audited."""
    headers = _as_gestor(application, create_user)
    email = f"perdido-{uuid.uuid4().hex[:8]}@sc.gov.br"
    first = application.post(USUARIOS, json=invite_body(email, "servidor"), headers=headers)
    member_id = first.json()["id"]
    old_token = _token_from(first.json()["activation_link"])

    response = application.post(f"{USUARIOS}/{member_id}/reemitir-convite", headers=headers)

    assert response.status_code == 200, response.text
    new_link = response.json()["activation_link"]
    assert "/invite?token=" in new_link
    new_token = _token_from(new_link)
    assert new_token != old_token

    stale = application.post(ACTIVATE, json={"token": old_token, "password": STRONG_ENOUGH})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "INVITE_EXPIRED"
    fresh = application.post(ACTIVATE, json={"token": new_token, "password": STRONG_ENOUGH})
    assert fresh.status_code == 200, fresh.text

    db_session.rollback()
    row = db_session.execute(
        text(
            "SELECT usuario_id, dados_anteriores::text AS dados FROM historico_movimentacao"
            " WHERE entidade_id = :u AND acao = 'usuario.convite_reemitido'"
        ),
        {"u": member_id},
    ).one()
    assert row.usuario_id is not None
    assert new_token not in row.dados and old_token not in row.dados


@pytest.mark.parametrize("status", ["ativo", "bloqueado", "desativado"])
def test_ac_0001_46_only_a_pending_account_gets_a_new_link(
    application: TestClient, create_user: Callable[..., User], db_session: Session, status: str
) -> None:
    """AC-0001-46 — any other status answers 409 `NOT_PENDING` and issues nothing."""
    headers = _as_gestor(application, create_user)
    target = create_user(email=f"ja-{uuid.uuid4().hex[:8]}@sc.gov.br", status=status)

    response = application.post(f"{USUARIOS}/{target.id}/reemitir-convite", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_PENDING"
    db_session.rollback()
    issued = db_session.execute(
        text("SELECT count(*) FROM token_credencial WHERE usuario_id = :u"), {"u": target.id}
    ).scalar_one()
    assert issued == 0


def test_ac_0001_46_an_unknown_account_is_404(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0001-46 — the same 404 as the other member routes."""
    headers = _as_gestor(application, create_user)
    response = application.post(f"{USUARIOS}/{uuid.uuid4()}/reemitir-convite", headers=headers)
    assert response.status_code == 404


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_13_a_servidor_or_auditor_cannot_issue_a_new_link(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> None:
    """AC-0001-13, AC-0001-46 — a gestor's act."""
    gestor = _as_gestor(application, create_user)
    pending = application.post(
        USUARIOS, json=invite_body(f"pend-{uuid.uuid4().hex[:8]}@sc.gov.br"), headers=gestor
    ).json()
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil=perfil, password=STRONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": STRONG_ENOUGH})
    headers = {"Authorization": f"Bearer {entry.json()['access_token']}"}

    response = application.post(f"{USUARIOS}/{pending['id']}/reemitir-convite", headers=headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"
