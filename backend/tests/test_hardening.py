"""Input bounds, the body ceiling and API security headers (AC-0001-41 to -43)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

LOGIN = "/api/v1/auth/login"


def test_ac_0001_41_an_oversized_password_is_refused(application: TestClient) -> None:
    """AC-0001-41 — 129 characters is refused before anything is hashed."""
    response = application.post(LOGIN, json={"email": "ana@sc.gov.br", "password": "x" * 129})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_DATA"
    assert error["fields"] == {"password": "Use no máximo 128 caracteres."}


@pytest.mark.parametrize(
    "route", ["/api/v1/convites/ativar", "/api/v1/auth/redefinicoes/confirmar"]
)
def test_ac_0001_41_an_oversized_token_is_refused(application: TestClient, route: str) -> None:
    """A token longer than any the API issues is refused unread."""
    response = application.post(route, json={"token": "t" * 513, "password": "x" * 20})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"token": "Use no máximo 512 caracteres."}


def test_ac_0001_42_an_oversized_body_is_refused(application: TestClient) -> None:
    """AC-0001-42 — 64 KiB and one byte is refused with the envelope."""
    body = b'{"email": "ana@sc.gov.br", "password": "' + b"x" * (64 * 1024) + b'"}'
    response = application.post(LOGIN, content=body, headers={"content-type": "application/json"})
    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "PAYLOAD_TOO_LARGE"
    assert error["correlation_id"]


def test_ac_0001_42_a_chunked_body_is_counted(application: TestClient) -> None:
    """A body with no declared length is counted as it arrives."""

    def chunks():
        yield b'{"email": "ana@sc.gov.br", "password": "'
        for _ in range(80):
            yield b"x" * 1024
        yield b'"}'

    response = application.post(
        LOGIN, content=chunks(), headers={"content-type": "application/json"}
    )
    assert response.status_code == 413


@pytest.mark.parametrize("path", ["/health", "/api/v1/auth/me"])
def test_ac_0001_43_every_response_forbids_sniffing_and_framing(
    application: TestClient, path: str
) -> None:
    """AC-0001-43 — success and error responses alike."""
    response = application.get(path)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"password": "x"}, "email", "Campo obrigatório."),
        ({"email": "nao-e-email", "password": "x"}, "email", "E-mail inválido."),
        ({"email": "ana@sc.gov.br", "password": ""}, "password", "Campo obrigatório."),
    ],
)
def test_field_messages_are_pt_br(
    application: TestClient, payload: dict[str, str], field: str, message: str
) -> None:
    """`fields` values are read by the servidor, so they are pt-BR (ADR-0013)."""
    response = application.post(LOGIN, json=payload)
    assert response.json()["error"]["fields"][field] == message
