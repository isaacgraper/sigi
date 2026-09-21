"""Password reset — AC-0001-31 and -32.

AC-0001-30 is not here. Self-service reset needs a channel to reach the
requester, and there is none: returning the token in the response would let
anyone reset anyone's password. It is marked blocked in SPEC-0001 v1.0 rather
than faked with a test that asserts something weaker than the criterion.
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
CONFIRMAR = "/api/v1/auth/redefinicoes/confirmar"
LOGIN = "/api/v1/auth/login"
ANTIGA = "SenhaAntigaOSuficiente-2026"
NOVA = "SenhaNovaOSuficiente-2027"


def _token_from(link: str) -> str:
    return link.split("token=", 1)[1]


def _as_gestor(application: TestClient, criar_usuario: Callable[..., User]) -> dict[str, str]:
    email = f"gestor-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil="gestor", senha=ANTIGA)
    entrada = application.post(LOGIN, json={"email": email, "password": ANTIGA})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def _member_with_reset(
    application: TestClient, criar_usuario: Callable[..., User]
) -> tuple[User, str]:
    headers = _as_gestor(application, criar_usuario)
    user = criar_usuario(email=f"membro-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=ANTIGA)
    response = application.post(f"{USUARIOS}/{user.id}/redefinir-senha", headers=headers)
    assert response.status_code == 200, response.text
    return user, _token_from(response.json()["reset_link"])


def test_ac_0001_31_redeeming_replaces_the_credential(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-31 — the new password works and the old one stops."""
    user, token = _member_with_reset(application, criar_usuario)

    assert application.post(CONFIRMAR, json={"token": token, "password": NOVA}).status_code == 204

    assert application.post(LOGIN, json={"email": user.email, "password": NOVA}).status_code == 200
    assert (
        application.post(LOGIN, json={"email": user.email, "password": ANTIGA}).status_code == 401
    )


def test_ac_0001_31_every_session_is_revoked(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-31 — two live sessions both end, with reason `redefinicao`.

    Not hygiene. If the person reset because they suspect theft this evicts the
    thief; if a thief holding the link did the reset it evicts the owner, who
    then notices. Leaving old sessions alive makes the reset cosmetic in exactly
    the case that matters.
    """
    user, token = _member_with_reset(application, criar_usuario)

    tokens = []
    for _ in range(2):
        entrada = application.post(LOGIN, json={"email": user.email, "password": ANTIGA})
        assert entrada.status_code == 200
        tokens.append(entrada.json()["access_token"])

    application.post(CONFIRMAR, json={"token": token, "password": NOVA})

    sessao.rollback()
    vivas = sessao.execute(
        text("SELECT count(*) FROM sessao WHERE usuario_id = :u AND revogado_em IS NULL"),
        {"u": user.id},
    ).scalar_one()
    assert vivas == 0
    motivos = set(
        sessao.execute(
            text("SELECT DISTINCT revogado_motivo FROM sessao WHERE usuario_id = :u"),
            {"u": user.id},
        )
        .scalars()
        .all()
    )
    assert motivos == {"redefinicao"}


def test_ac_0001_31_the_token_is_single_use(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-31 — the second redemption answers RESET_ALREADY_USED.

    The code matters: AC-0001-25 asks for INVITE_* and this asks for RESET_*.
    One shared default would report the wrong family.
    """
    _, token = _member_with_reset(application, criar_usuario)
    assert application.post(CONFIRMAR, json={"token": token, "password": NOVA}).status_code == 204

    again = application.post(CONFIRMAR, json={"token": token, "password": NOVA})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "RESET_ALREADY_USED"


def test_ac_0001_31_an_expired_token_answers_reset_expired(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-31 — one hour, against the invitation's 72."""
    user, token = _member_with_reset(application, criar_usuario)

    # `ck_token_expira` enforces `expira_em > criado_em`, so both move: a grant
    # that expired before it was issued is a row the schema rightly refuses,
    # and writing one here would be the test lying rather than ageing anything.
    sessao.execute(
        text(
            "UPDATE token_credencial"
            " SET criado_em = now() - interval '2 hours',"
            "     expira_em = now() - interval '1 hour'"
            " WHERE usuario_id = :u AND tipo = 'redefinicao'"
        ),
        {"u": user.id},
    )
    sessao.commit()

    response = application.post(CONFIRMAR, json={"token": token, "password": NOVA})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESET_EXPIRED"


def test_ac_0001_31_a_weak_password_leaves_the_token_usable(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """AC-0001-31's last clause — validate before spending, as with activation."""
    _, token = _member_with_reset(application, criar_usuario)

    fraca = application.post(CONFIRMAR, json={"token": token, "password": "curta"})
    assert fraca.status_code == 422
    assert fraca.json()["error"]["code"] == "WEAK_PASSWORD"

    assert application.post(CONFIRMAR, json={"token": token, "password": NOVA}).status_code == 204


def test_an_unknown_reset_token_answers_like_a_spent_one(application: TestClient) -> None:
    """Distinguishing the two would say which grants exist."""
    response = application.post(
        CONFIRMAR, json={"token": "nunca-emitido-" + uuid.uuid4().hex, "password": NOVA}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESET_ALREADY_USED"


def test_an_invitation_token_cannot_be_redeemed_as_a_reset(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """The two grant types are not interchangeable.

    Both live in `token_credencial` and differ only by `tipo`, so a redemption
    that ignored it would let an invitation set a password on a live account.
    """
    headers = _as_gestor(application, criar_usuario)
    convite = application.post(
        USUARIOS,
        json={"email": f"conv-{uuid.uuid4().hex[:8]}@sc.gov.br", "perfil": "servidor"},
        headers=headers,
    )
    token_de_convite = _token_from(convite.json()["activation_link"])

    response = application.post(CONFIRMAR, json={"token": token_de_convite, "password": NOVA})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESET_ALREADY_USED"


def test_ac_0001_32_the_gestor_triggers_and_the_act_is_audited(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """AC-0001-32 — actor and target are different people, and the row says so.

    This row is the mitigation for the property v1.0 gives up: the gestor now
    receives the link, so the only thing standing between that and a silent
    takeover is that the act is recorded and the member's sessions all die.
    """
    headers = _as_gestor(application, criar_usuario)
    user = criar_usuario(email=f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=ANTIGA)

    response = application.post(f"{USUARIOS}/{user.id}/redefinir-senha", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["reset_link"]

    sessao.rollback()
    row = sessao.execute(
        text(
            "SELECT usuario_id, entidade_id FROM historico_movimentacao"
            " WHERE acao = 'usuario.redefinicao_solicitada' AND entidade_id = :u"
        ),
        {"u": user.id},
    ).one()
    # The gestor is the actor, the member is the entity. Not the same id.
    assert row.entidade_id == user.id
    assert row.usuario_id != user.id


def test_ac_0001_32_the_reset_link_is_not_recoverable_afterwards(
    application: TestClient, criar_usuario: Callable[..., User], sessao: Session
) -> None:
    """Only the HMAC reaches the database."""
    user, token = _member_with_reset(application, criar_usuario)

    sessao.rollback()
    stored = (
        sessao.execute(
            text("SELECT token_hash::text FROM token_credencial WHERE usuario_id = :u"),
            {"u": user.id},
        )
        .scalars()
        .all()
    )
    assert stored
    assert all(token not in row for row in stored)


@pytest.mark.parametrize("perfil", ["servidor", "auditor"])
def test_ac_0001_32_a_servidor_or_auditor_cannot_trigger_a_reset(
    application: TestClient, criar_usuario: Callable[..., User], perfil: str
) -> None:
    """AC-0001-32 — 403 with the permission code."""
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    criar_usuario(email=email, perfil=perfil, senha=ANTIGA)
    entrada = application.post(LOGIN, json={"email": email, "password": ANTIGA})
    headers = {"Authorization": f"Bearer {entrada.json()['access_token']}"}
    alvo = criar_usuario(email=f"alvo-{uuid.uuid4().hex[:8]}@sc.gov.br", senha=ANTIGA)

    response = application.post(f"{USUARIOS}/{alvo.id}/redefinir-senha", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"


def test_confirming_returns_no_session(
    application: TestClient, criar_usuario: Callable[..., User]
) -> None:
    """204, not a token.

    Unlike activation, a reset may have been triggered by someone who is not the
    account owner, so handing back a session would hand it to whoever redeemed
    the link.
    """
    _, token = _member_with_reset(application, criar_usuario)
    response = application.post(CONFIRMAR, json={"token": token, "password": NOVA})
    assert response.status_code == 204
    assert not response.content


def test_the_reset_token_is_never_a_path_segment(application: TestClient) -> None:
    """OQ-30 — the token travels in the body, and the old shape does not answer."""
    stale = application.post(
        "/api/v1/auth/redefinicoes/algum-token/confirmar", json={"password": NOVA}
    )
    assert stale.status_code == 404
