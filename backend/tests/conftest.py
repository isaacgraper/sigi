"""Shared fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """A client over a freshly built application.

    Built per test rather than per session so that a test changing
    configuration cannot leak that change into the next one.
    """
    return TestClient(create_app())
