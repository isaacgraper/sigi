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

from app.core.security import issue_access_token
from app.models.user import User
from tests.conftest import cookie_from, use_refresh

ME = "/api/v1/auth/me"
PASSWORD = "SenhaCorreta-12345"


def _sign_in(application: TestClient, user: User) -> str:
    response = application.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return token


def test_ac_0001_08_deactivation_takes_effect_immediately(
    application: TestClient,
    create_user: Callable[..., User],
    db_session: Session,
) -> None:
    """AC-0001-08 deactivation bites at once, not when the token expires."""
    user = create_user()
    token = _sign_in(application, user)
    headers = {"Authorization": f"Bearer {token}"}
    assert application.get(ME, headers=headers).status_code == 200

    # Written directly because member management is the next step (AC-0001-12);
    # what this criterion observes is the effect on the token already issued.
    user.status = "desativado"
    user.nome = None
    user.email = None
    user.senha_hash = None
    user.anonimizado_em = datetime.datetime.now(datetime.UTC)
    db_session.commit()

    refused = application.get(ME, headers=headers)
    assert refused.status_code == 401
    assert refused.json()["error"]["code"] == "USUARIO_INATIVO"


def test_ac_0001_08_blocking_also_takes_effect_immediately(
    application: TestClient,
    create_user: Callable[..., User],
    db_session: Session,
) -> None:
    """Blocking an account kills its live token too.

    `ativo` is generated from `status`, so blocking closes it by the same path,
    and that is the case that actually happens to a compromised account.
    """
    user = create_user()
    headers = {"Authorization": f"Bearer {_sign_in(application, user)}"}

    user.status = "bloqueado"
    db_session.commit()

    assert application.get(ME, headers=headers).status_code == 401


def test_ac_0001_08_refresh_checks_too(
    application: TestClient,
    create_user: Callable[..., User],
    db_session: Session,
) -> None:
    """A refresh is a fresh authorisation decision.

    Without this check the deactivation would be immediate for `/me` and useless
    in practice: the client refreshes on its own and gains another fifteen
    minutes of exactly the access the deactivation removed.
    """
    user = create_user()
    entry = application.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    refresh = cookie_from(entry, "sigi_refresh")
    assert refresh
    use_refresh(application, refresh)

    user.status = "bloqueado"
    db_session.commit()

    refused = application.post("/api/v1/auth/refresh")
    assert refused.status_code == 401
    assert refused.json()["error"]["code"] == "USUARIO_INATIVO"


def test_a_token_without_an_account_is_refused(application: TestClient) -> None:
    """Our own signature, a `sub` that does not exist: 401, not 500.

    It really happens after restoring an old backup, and the cheap failure mode
    is what decides whether somebody investigates or restarts the service.
    """
    token = issue_access_token(user_id=uuid.uuid4(), role="gestor")
    response = application.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "USUARIO_INATIVO"


def test_without_an_authorization_header_it_is_401(application: TestClient) -> None:
    """A request with no Authorization header is 401."""
    response = application.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"
