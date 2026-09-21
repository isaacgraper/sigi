"""Data access for `limite_taxa`. The policy lives in the service."""

from __future__ import annotations

import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.rate_limit import RateLimit


def count_hit(session: Session, *, key: bytes, rota: str, window_start: datetime.datetime) -> int:
    """Count one request in this window and return the running total.

    One statement, for the same reason `login_attempt.count_attempt` is one:
    two concurrent requests must not both read n and both write n+1, or the
    ceiling disappears for anyone who sends their requests in parallel rather
    than in series. `ON CONFLICT DO UPDATE` takes the row lock that makes the
    increment atomic.

    The conflict target is the table's own primary key, so no extra index is
    needed for it.
    """
    statement = (
        insert(RateLimit)
        .values(chave=key, rota=rota, janela_inicio=window_start, contador=1)
        .on_conflict_do_update(
            index_elements=[RateLimit.key, RateLimit.rota, RateLimit.janela_inicio],
            set_={"contador": RateLimit.contador + 1},
        )
        .returning(RateLimit.contador)
    )
    return int(session.execute(statement).scalar_one())
