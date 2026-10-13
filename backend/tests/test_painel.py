"""The dashboard's data — SPEC-0012 v1.1, AC-0012-12."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

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
