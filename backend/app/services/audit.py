"""Writing the audit trail (RN06, RNF08, SPEC-0001 §8).

The contract, from `CLAUDE.md`: every mutation writes a history row **in the
same transaction as the mutation**, and if the history write fails, the mutation
fails. That is why this takes the caller's `Session` and never opens or commits one
of its own — a writer with its own transaction could leave a mutation
without its record, which in an auditability product is the defect the product
exists to prevent.
"""

from __future__ import annotations

import datetime
import re
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_log import insert_row


class DadoPessoalNoHistorico(RuntimeError):
    """A caller tried to write personal data into an immutable table.

    Not a `DomainError`: no user caused this and no message would help them.
    It is a bug, and the right outcome is a 500 plus a fix.
    """


@dataclass(frozen=True)
class Event:
    """One thing that happened, as the audit trail will record it."""

    entidade_tipo: str
    entidade_id: uuid.UUID
    acao: str
    usuario_id: uuid.UUID | None = None
    dados_anteriores: Mapping[str, Any] | None = field(default=None)
    justificativa: str | None = None


# Deliberately loose: it only has to catch an address that slipped into a
# payload, not validate one. `lgpd.md` promises the audit table carries no
# personal data, and that table can never be corrected — so the promise is
# worth enforcing mechanically rather than in prose that decays.
_PARECE_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def record(
    session: Session,
    evento: Event,
    *,
    correlation_id: uuid.UUID,
    at: datetime.datetime | None = None,
) -> None:
    """Append one audit row, in the caller's transaction.

    The caller's session on purpose: every write endpoint records history in
    the same transaction as the write, so if the history fails the write fails
    with it (RN06).
    """
    _refuse_personal_data(evento.dados_anteriores)
    insert_row(
        session,
        AuditLog(
            ocorrido_em=at or datetime.datetime.now(datetime.UTC),
            entidade_tipo=evento.entidade_tipo,
            entidade_id=evento.entidade_id,
            acao=evento.acao,
            usuario_id=evento.usuario_id,
            dados_anteriores=dict(evento.dados_anteriores)
            if evento.dados_anteriores is not None
            else None,
            justificativa=evento.justificativa,
            correlation_id=correlation_id,
        ),
    )


def _refuse_personal_data(data: Mapping[str, Any] | None) -> None:
    if data is None:
        return
    for path, value in _walk(data):
        if isinstance(value, str) and _PARECE_EMAIL.search(value):
            raise DadoPessoalNoHistorico(
                f"dados_anteriores[{path}] looks like it carries an e-mail address. "
                "The audit table can never be corrected, so it carries no "
                "personal data: use app.core.secrets_hmac.digest_secret() and write "
                "the HMAC plus the domain, as SPEC-0001 §8 requires."
            )


def _walk(value: Any, path: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, Mapping):
        return [
            item
            for key, sub in value.items()
            for item in _walk(sub, f"{path}.{key}" if path else str(key))
        ]
    if isinstance(value, list | tuple):
        return [item for i, sub in enumerate(value) for item in _walk(sub, f"{path}[{i}]")]
    return [(path, value)]


@contextmanager
def standalone_transaction() -> Iterator[Session]:
    """A session that commits, independent of the request's.

    For the failure path, which is the path that rolls back. A failed login
    raises, the request's session is rolled back, and anything written in it
    goes with the failure it was recording — the audit trail left with only
    successes in it, and the lockout counter of AC-0001-03 never reaching five.

    Deliberately **not** the default: everything that accompanies a mutation
    must share that mutation's transaction, and a writer that commits on its own
    could leave one without the other.
    """
    from app.core.db import sessao_factory

    with sessao_factory()() as own_session:
        try:
            yield own_session
            own_session.commit()
        except Exception:
            own_session.rollback()
            raise


def record_standalone(evento: Event, *, correlation_id: uuid.UUID) -> None:
    """Write a single audit row in a transaction of its own, and commit it.

    For the failure path, which is the path that rolls back. A failed login
    raises, the request's session is rolled back, and an audit row written in it
    would vanish with the failure it was recording — leaving the trail with only
    successes in it, which is the opposite of useful.

    Use `standalone_transaction` directly when more than one row has to land together.
    """
    with standalone_transaction() as own_session:
        record(own_session, evento, correlation_id=correlation_id)
