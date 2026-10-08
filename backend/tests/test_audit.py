"""The audit writer's contract (RN06, SPEC-0001 §8).

`CLAUDE.md`: "Every write endpoint records a `HISTORICO_MOVIMENTACAO` row in the
same transaction as the write. If the history write fails, the write fails."

That is two promises pointing in opposite directions, and it is easy to test one
and believe you covered both.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.services.audit import Event, PersonalDataInHistory, record


def _create_user(db_session: Session, nome: str = "Ana") -> uuid.UUID:
    uid = uuid.uuid4()
    db_session.execute(
        text(
            "INSERT INTO usuario (id, nome, email, perfil, status)"
            " VALUES (:id, :nome, :email, 'servidor', 'ativo')"
        ),
        {"id": uid, "nome": nome, "email": f"{nome.lower()}-{uid.hex[:8]}@sc.gov.br"},
    )
    return uid


def _count(db_session: Session, uid: uuid.UUID) -> int:
    return int(
        db_session.execute(
            text("SELECT count(*) FROM historico_movimentacao WHERE entidade_id = :i"),
            {"i": uid},
        ).scalar_one()
    )


def test_the_row_is_written_in_the_callers_transaction(db_session: Session) -> None:
    """RN06 — the row lands in the caller's transaction, not one of its own."""
    uid = _create_user(db_session)
    record(
        db_session,
        Event(entidade_tipo="usuario", entidade_id=uid, acao="usuario.convidado"),
        correlation_id=uuid.uuid4(),
    )
    db_session.commit()
    assert _count(db_session, uid) == 1


def test_rolling_the_mutation_back_takes_the_audit_with_it(db_session: Session) -> None:
    """The first half of the promise: no orphan audit row."""
    uid = _create_user(db_session)
    record(
        db_session,
        Event(entidade_tipo="usuario", entidade_id=uid, acao="usuario.convidado"),
        correlation_id=uuid.uuid4(),
    )
    db_session.rollback()
    assert _count(db_session, uid) == 0
    exists = db_session.execute(
        text("SELECT count(*) FROM usuario WHERE id = :i"), {"i": uid}
    ).scalar_one()
    assert exists == 0


def test_a_failed_audit_brings_the_mutation_down(db_session: Session) -> None:
    r"""The second half, and the one that is easy to leave untested.

    `acao` must match `^[a-z_]+\\.[a-z_]+$`, so a malformed one is refused by the
    database. What this asserts is not the refusal — that is the migration's
    test — but that the mutation made moments earlier does **not** survive it.
    """
    uid = _create_user(db_session, "Bruno")
    with pytest.raises(DBAPIError):
        record(
            db_session,
            Event(entidade_tipo="usuario", entidade_id=uid, acao="UsuarioConvidado"),
            correlation_id=uuid.uuid4(),
        )
    db_session.rollback()
    left_over = db_session.execute(
        text("SELECT count(*) FROM usuario WHERE id = :i"), {"i": uid}
    ).scalar_one()
    assert left_over == 0, "a mutação sobreviveu à falha da auditoria"


def test_a_row_without_an_ator_is_allowed(db_session: Session) -> None:
    """A row with no actor is allowed.

    AC-0001-20 and AC-0001-21 both audit callers who have no account at all,
    which is why `usuario_id` is nullable.
    """
    target = uuid.uuid4()
    record(
        db_session,
        Event(
            entidade_tipo="usuario",
            entidade_id=target,
            acao="auth.oidc_recusada",
            user_id=None,
            dados_anteriores={"motivo": "sem_conta", "dominio": "sc.gov.br"},
        ),
        correlation_id=uuid.uuid4(),
    )
    db_session.commit()
    assert _count(db_session, target) == 1


def test_the_correlation_id_is_recorded(db_session: Session) -> None:
    """RNF12 — the correlation id reaches the row, so a log line can be tied to it."""
    uid, correlation = uuid.uuid4(), uuid.uuid4()
    record(
        db_session,
        Event(entidade_tipo="usuario", entidade_id=uid, acao="auth.login"),
        correlation_id=correlation,
    )
    db_session.commit()
    recorded = db_session.execute(
        text("SELECT correlation_id FROM historico_movimentacao WHERE entidade_id = :i"),
        {"i": uid},
    ).scalar_one()
    assert recorded == correlation


@pytest.mark.parametrize(
    "payload",
    [
        {"email_asserido": "ana@sc.gov.br"},
        {"motivo": "sem_conta", "detalhe": {"quem": "ana@sc.gov.br"}},
        {"tentativas": [{"endereco": "ana@sc.gov.br"}]},
    ],
    ids=["raso", "aninhado", "dentro-de-lista"],
)
def test_the_guard_refuses_an_address_in_dados_anteriores(
    db_session: Session, payload: dict
) -> None:
    """An address in `dados_anteriores` is refused.

    `lgpd.md` promises the audit table carries no personal data, and the table
    can never be corrected — so the promise is enforced rather than written down.

    The check is a heuristic, which is why the message names the remedy instead
    of only refusing.
    """
    with pytest.raises(PersonalDataInHistory) as exc:
        record(
            db_session,
            Event(
                entidade_tipo="usuario",
                entidade_id=uuid.uuid4(),
                acao="auth.oidc_recusada",
                dados_anteriores=payload,
            ),
            correlation_id=uuid.uuid4(),
        )
    assert "secrets_hmac.digest_secret" in str(exc.value)


def test_the_guard_lets_the_correct_payload_through(db_session: Session) -> None:
    """What SPEC-0001 §8 actually prescribes: the HMAC and the bare domain."""
    from app.core.secrets_hmac import digest_secret

    record(
        db_session,
        Event(
            entidade_tipo="usuario",
            entidade_id=uuid.uuid4(),
            acao="auth.falha",
            dados_anteriores={
                "motivo": "credenciais_invalidas",
                "email_hmac": digest_secret("ana@sc.gov.br").hex(),
                "dominio": "sc.gov.br",
            },
        ),
        correlation_id=uuid.uuid4(),
    )
    db_session.commit()
