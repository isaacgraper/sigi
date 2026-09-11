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
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert uuid.UUID(resposta.headers[CABECALHO])


def test_valor_recebido_e_preservado(client: TestClient) -> None:
    """Accepting the caller's value is what lets one request be followed from
    the frontend through the API and into the audit trail."""
    meu = uuid.uuid4()
    resposta = client.get("/health", headers={CABECALHO: str(meu)})
    assert resposta.headers[CABECALHO] == str(meu)


def test_valor_malformado_e_substituido_e_nao_rejeitado(client: TestClient) -> None:
    """It is a tracing convenience, not an authorisation input: a bad value
    earns a fresh id, not a 400."""
    resposta = client.get("/health", headers={CABECALHO: "nao-e-um-uuid"})
    assert resposta.status_code == 200
    assert uuid.UUID(resposta.headers[CABECALHO]) != "nao-e-um-uuid"
