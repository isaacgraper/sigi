"""Liveness probe. Verifies RNF09 — `docker compose up` reaches a live app."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report that the process is up.

    Deliberately does not touch the database: this answers "is the process
    serving requests", and a probe that fails on a database blip takes the
    application down with it.
    """
    return {"status": "ok"}
