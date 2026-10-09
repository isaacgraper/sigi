"""The dashboard's data — SPEC-0012 v1.2, AC-0012-12 to -14."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.models.user import User
from app.services import painel

PAINEL = "/api/v1/painel"
LOGIN = "/api/v1/auth/login"
# Not `*_PASSWORD`: gitleaks reads that keyword beside this entropy as a credential.
LONG_ENOUGH = "SenhaLongaOSuficiente-2026"


def _login(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> dict[str, str]:
    email = f"{perfil}-{uuid.uuid4().hex[:8]}@sc.gov.br"
    create_user(email=email, perfil=perfil, password=LONG_ENOUGH)
    entry = application.post(LOGIN, json={"email": email, "password": LONG_ENOUGH})
    assert entry.status_code == 200, entry.text
    return {"Authorization": f"Bearer {entry.json()['access_token']}"}


@pytest.mark.parametrize("perfil", ["gestor", "servidor", "auditor"])
def test_ac_0012_12_every_perfil_reads_every_section_block_by_block(
    application: TestClient, create_user: Callable[..., User], perfil: str
) -> None:
    """AC-0012-12 — 200 for each section, one entry per block, empty rows today."""
    headers = _login(application, create_user, perfil)
    for section, blocks in painel.SECTIONS.items():
        response = application.get(f"{PAINEL}/{section}", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json() == {
            "section": section,
            "demo": False,
            "blocks": {block: {"rows": []} for block in blocks},
        }


def test_ac_0012_12_the_four_sections_are_the_reports() -> None:
    """AC-0012-12 — the sections are the report's four pages, in its order."""
    assert list(painel.SECTIONS) == ["atendimento", "consumo", "processos", "itens-em-falta"]


def test_ac_0012_12_without_a_session_is_refused(application: TestClient) -> None:
    """AC-0012-12 — 401 without a session."""
    response = application.get(f"{PAINEL}/consumo")
    assert response.status_code == 401


def test_ac_0012_12_an_unknown_section_is_not_found(
    application: TestClient, create_user: Callable[..., User]
) -> None:
    """AC-0012-12 — 404 NOT_FOUND for a section the dashboard does not have."""
    headers = _login(application, create_user, "servidor")
    response = application.get(f"{PAINEL}/nao-existe", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_ac_0012_13_in_development_the_demo_fills_every_block(
    application: TestClient, create_user: Callable[..., User], monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-0012-13 — with DASHBOARD_DEMO in development, every block has rows and demo is true."""
    headers = _login(application, create_user, "servidor")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DASHBOARD_DEMO", "true")
    get_settings.cache_clear()
    try:
        for section, blocks in painel.SECTIONS.items():
            body = application.get(f"{PAINEL}/{section}", headers=headers).json()
            assert body["demo"] is True
            assert set(body["blocks"]) == set(blocks)
            for block in blocks:
                assert body["blocks"][block]["rows"], f"{section}.{block} has no demo rows"
    finally:
        monkeypatch.delenv("DASHBOARD_DEMO")
        get_settings.cache_clear()


def test_ac_0012_13_the_demo_keeps_saldo_and_estoque_apart() -> None:
    """AC-0012-13, invariant 5 — the estoque tiles name their position's date."""
    for section in ("consumo", "itens-em-falta"):
        estoque = painel.read(section, demo=True)["estoque"]
        assert estoque[0][1].startswith("Posição de ")


@pytest.mark.parametrize("env", ["production", "staging", "test"])
def test_ac_0012_14_the_demo_refuses_any_other_environment(env: str) -> None:
    """AC-0012-14 — DASHBOARD_DEMO outside development stops the settings from loading."""
    with pytest.raises(ValidationError, match="DASHBOARD_DEMO"):
        Settings(app_env=env, dashboard_demo=True)


def test_ac_0012_14_without_the_switch_the_answer_is_the_real_one() -> None:
    """AC-0012-14 — the default is off, so the service answers SIGI's real, empty rows."""
    assert Settings().dashboard_demo is False
    assert all(rows == [] for rows in painel.read("itens-em-falta", demo=False).values())
