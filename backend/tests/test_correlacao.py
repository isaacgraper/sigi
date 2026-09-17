"""Correlation id on every response (RNF12).

`historico_movimentacao.correlation_id` is `NOT NULL`, so an audit row cannot be
written without one — which makes this middleware a prerequisite for every write
endpoint, not a logging nicety.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.correlacao import CABECALHO


def test_resposta_sempre_carrega_correlation_id(client: TestClient) -> None:
    """RNF12 — every response carries one, whether or not the caller sent it."""
    response = client.get("/health")
    assert response.status_code == 200
    assert uuid.UUID(response.headers[CABECALHO])


def test_valor_recebido_e_preservado(client: TestClient) -> None:
    """A value the caller supplies is kept.

    Accepting it is what lets one request be followed from the frontend through
    the API and into the audit trail.
    """
    meu = uuid.uuid4()
    response = client.get("/health", headers={CABECALHO: str(meu)})
    assert response.headers[CABECALHO] == str(meu)


def test_valor_malformado_e_substituido_e_nao_rejeitado(client: TestClient) -> None:
    """A malformed value is replaced, never rejected.

    It is a tracing convenience, not an authorisation input, so a bad value
    earns a fresh id rather than a 400.
    """
    response = client.get("/health", headers={CABECALHO: "nao-e-um-uuid"})
    assert response.status_code == 200
    assert uuid.UUID(response.headers[CABECALHO]) != "nao-e-um-uuid"
