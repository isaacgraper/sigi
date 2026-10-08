"""The liveness probe (RNF09)."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    """RNF09 — the assembled application answers `/health` with 200."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
