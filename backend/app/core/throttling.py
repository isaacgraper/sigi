"""The rate-limit dependency, and the check that every route carries one.

AC-0001-33's last clause asks for the coverage check, and it exists for the same
reason `authorization.verify_coverage` does: a throttle that silently covers
nothing looks exactly like one that works.
"""

from __future__ import annotations

import datetime
import uuid

from fastapi import Request
from starlette.applications import Starlette

from app.core.config import get_settings
from app.core.correlation import current as current_correlation_id
from app.services import throttle


class RouteWithoutCeiling(RuntimeError):
    """A throttled prefix carries a route with no configured ceiling."""


def _source(request: Request) -> str:
    """The address this request is counted against.

    `request.client.host` and deliberately **not** `X-Forwarded-For`. Honouring
    that header unconditionally would let anyone bypass the throttle by setting
    it, which is worse than having no throttle because it still looks like one.
    A deployment behind a reverse proxy needs an explicit trusted-proxy setting
    first; OQ-32 records that.
    """
    return request.client.host if request.client else "desconhecido"


def enforce(request: Request) -> None:
    """Count this request against its source and route, or refuse it."""
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    raw = request.scope.get("state", {}).get("correlation_id")
    correlation_id = raw if isinstance(raw, uuid.UUID) else current_correlation_id()

    from app.core.db import session_factory

    with session_factory()() as session:
        throttle.check(
            session,
            source=_source(request),
            route_path=route_path,
            now=datetime.datetime.now(datetime.UTC),
            correlation_id=correlation_id,
        )


def verify_ceilings(app: Starlette) -> None:
    """Refuse to start if a throttled route has no ceiling (AC-0001-33).

    Runs when the application is assembled, so it breaks the build and the test
    suite rather than production. Without it, adding a route under one of these
    prefixes would silently inherit whatever the default happens to be, and the
    criterion's "a route without one is reported by name" would never fire.
    """
    from app.core.authorization import application_routes

    cfg = get_settings()
    missing = [
        path
        for path, _ in application_routes(app)
        if path.startswith(throttle.PREFIXES) and path not in cfg.rate_limit_tetos
    ]
    if missing:
        raise RouteWithoutCeiling(
            "throttled routes with no ceiling: "
            + ", ".join(sorted(missing))
            + ". Add one to rate_limit_tetos. There is no default to fall back"
            " on, deliberately: with one, this check could never fail."
        )
