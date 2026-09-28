"""The rate-limit dependency, and the check that every route carries one.

AC-0001-33's last clause asks for the coverage check, and it exists for the same
reason `authorization.verify_coverage` does: a throttle that silently covers
nothing looks exactly like one that works.
"""

from __future__ import annotations

import datetime
import ipaddress
import uuid

from fastapi import Request
from starlette.applications import Starlette

from app.core.config import get_settings
from app.core.correlation import current as current_correlation_id
from app.services import throttle


class RouteWithoutCeiling(RuntimeError):
    """A throttled prefix carries a route with no configured ceiling."""


def _is_trusted(
    address: str, networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network]
) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(parsed in network for network in networks)


def source_of(peer: str | None, forwarded_for: str | None) -> str:
    """The address a request is counted against (AC-0001-37, -38).

    The peer, unless the peer is a configured trusted proxy. Then the right-most
    forwarded address that is not itself trusted: the right end is what the
    nearest trusted hop saw, and everything to the left of it was written by
    the client and proves nothing. Believing `X-Forwarded-For` from anyone would
    let each request choose its own source, which is worse than no throttle
    because it still looks like one.
    """
    if peer is None:
        return "desconhecido"
    networks = [ipaddress.ip_network(cidr, strict=False) for cidr in get_settings().trusted_proxies]
    if not forwarded_for or not _is_trusted(peer, networks):
        return peer
    for hop in reversed([part.strip() for part in forwarded_for.split(",")]):
        if hop and not _is_trusted(hop, networks):
            return hop
    return peer


def _source(request: Request) -> str:
    return source_of(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
    )


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
        if path.startswith(throttle.PREFIXES) and path not in cfg.rate_limit_ceilings
    ]
    if missing:
        raise RouteWithoutCeiling(
            "throttled routes with no ceiling: "
            + ", ".join(sorted(missing))
            + ". Add one to rate_limit_ceilings. There is no default to fall back"
            " on, deliberately: with one, this check could never fail."
        )
