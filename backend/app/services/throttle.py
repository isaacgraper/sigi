"""Per-source rate limiting (AC-0001-33, ADR-0012).

The second of two independent throttles. The per-address lockout of AC-0001-03
asks "is someone attacking this account?" and is keyed on the submitted
address; this one asks "is someone abusing this endpoint?" and is keyed on the
source. Neither contains the other: the first misses a spray across many
addresses, the second misses a slow, patient attack on one.
"""

from __future__ import annotations

import datetime
import ipaddress
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.secrets_hmac import digest_secret
from app.repositories import rate_limit as repo
from app.services.audit import Event, record_standalone, standalone_transaction
from app.services.errors import RateLimited

PREFIXES = ("/api/v1/auth", "/api/v1/convites")


def ceiling_for(route_path: str, *, institutional: bool) -> int:
    """The ceiling this route allows this source in one window.

    A route with no configured ceiling cannot start, so the fallback below is
    unreachable in a running application. It is the most restrictive configured
    value rather than a permissive default on purpose: if the startup check is
    ever weakened, the failure should be a throttle that is too tight and gets
    noticed, not one that is absent and does not.
    """
    cfg = get_settings()
    if institutional:
        return cfg.rate_limit_institutional_ceiling
    try:
        return cfg.rate_limit_ceilings[route_path]
    except KeyError:  # pragma: no cover - verify_ceilings refuses to start
        return min(cfg.rate_limit_ceilings.values(), default=1)


def is_institutional(source: str) -> bool:
    """Whether the source sits in one of the configured institutional ranges."""
    cfg = get_settings()
    try:
        address = ipaddress.ip_address(source)
    except ValueError:
        # An unparseable source is treated as ordinary rather than trusted. The
        # direction matters: guessing "institutional" would hand the higher
        # ceiling to anyone who can make the source unreadable.
        return False
    for cidr in cfg.rate_limit_institutional_ranges:
        try:
            if address in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:  # pragma: no cover - a malformed CIDR in settings
            continue
    return False


def window_start(now: datetime.datetime, *, seconds: int) -> datetime.datetime:
    """Floor `now` to the start of its window.

    A fixed window, not a sliding one. It costs one row per source per route
    per window and no history, and the price is that a burst straddling a
    boundary can see two windows' worth of allowance. That is a known
    consequence rather than a discovered one: a sliding window would need the
    timestamps of individual requests, which is a table this project would then
    have to keep pruned.
    """
    epoch = int(now.timestamp())
    return datetime.datetime.fromtimestamp(epoch - (epoch % seconds), datetime.UTC)


def check(
    session: Session,
    *,
    source: str,
    route_path: str,
    now: datetime.datetime,
    correlation_id: uuid.UUID,
) -> None:
    """Count this request and refuse it if the source is over the ceiling.

    The counter lives in a transaction of its own, because the refusal raises
    and the request's session is rolled back: a count written in it would vanish
    with the refusal it was recording, and the ceiling would never be reached by
    anyone whose requests all fail.
    """
    cfg = get_settings()
    seconds = cfg.rate_limit_window_seconds
    start = window_start(now, seconds=seconds)
    institutional = is_institutional(source)
    limit = ceiling_for(route_path, institutional=institutional)
    key = digest_secret(source)

    with standalone_transaction() as own:
        total = repo.count_hit(own, key=key, route_path=route_path, window_start=start)

    if total > limit:
        retry_after = max(
            1, int((start + datetime.timedelta(seconds=seconds) - now).total_seconds())
        )
        record_standalone(
            Event(
                entidade_tipo="rota",
                entidade_id=uuid.UUID(int=0),
                acao="auth.limite_excedido",
                user_id=None,
                # The HMAC, never the address: this table can never be
                # corrected and `lgpd.md` promises it carries no personal data.
                dados_anteriores={
                    "rota": route_path,
                    "origem_hmac": key.hex(),
                    "institucional": institutional,
                },
            ),
            correlation_id=correlation_id,
        )
        raise RateLimited(retry_after=retry_after)
