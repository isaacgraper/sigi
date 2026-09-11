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

from app.services.auditoria import DadoPessoalNoHistorico, Evento, registrar


def _criar_usuario(sessao: Session, nome: str = "Ana") -> uuid.UUID:
    uid = uuid.uuid4()
    sessao.execute(
        text(
            "INSERT INTO usuario (id, nome, email, perfil, status)"
            " VALUES (:id, :nome, :email, 'servidor', 'ativo')"
        ),
        {"id": uid, "nome": nome, "email": f"{nome.lower()}-{uid.hex[:8]}@sc.gov.br"},
    )
    return uid


def _contar(sessao: Session, uid: uuid.UUID) -> int:
    return int(
        sessao.execute(
            text("SELECT count(*) FROM historico_movimentacao WHERE entidade_id = :i"),
            {"i": uid},
        ).scalar_one()
    )


def test_linha_e_gravada_na_transacao_de_quem_chama(sessao: Session) -> None:
    uid = _criar_usuario(sessao)
    registrar(
        sessao,
        Evento(entidade_tipo="usuario", entidade_id=uid, acao="usuario.convidado"),
        correlation_id=uuid.uuid4(),
    )
    sessao.commit()
    assert _contar(sessao, uid) == 1


def test_rollback_da_mutacao_leva_a_auditoria_junto(sessao: Session) -> None:
    """The first half of the promise: no orphan audit row."""
    uid = _criar_usuario(sessao)
    registrar(
        sessao,
        Evento(entidade_tipo="usuario", entidade_id=uid, acao="usuario.convidado"),
        correlation_id=uuid.uuid4(),
    )
    sessao.rollback()
    assert _contar(sessao, uid) == 0
    existe = sessao.execute(
        text("SELECT count(*) FROM usuario WHERE id = :i"), {"i": uid}
    ).scalar_one()
    assert existe == 0


def test_falha_da_auditoria_derruba_a_mutacao(sessao: Session) -> None:
    """The second half, and the one that is easy to leave untested.

    `acao` must match `^[a-z_]+\\.[a-z_]+$`, so a malformed one is refused by the
    database. What this asserts is not the refusal — that is the migration's
    test — but that the mutation made moments earlier does **not** survive it.
    """
    uid = _criar_usuario(sessao, "Bruno")
    with pytest.raises(DBAPIError):
        registrar(
            sessao,
            Evento(entidade_tipo="usuario", entidade_id=uid, acao="UsuarioConvidado"),
            correlation_id=uuid.uuid4(),
        )
    sessao.rollback()
    sobrou = sessao.execute(
        text("SELECT count(*) FROM usuario WHERE id = :i"), {"i": uid}
    ).scalar_one()
    assert sobrou == 0, "a mutação sobreviveu à falha da auditoria"


def test_linha_sem_ator_e_permitida(sessao: Session) -> None:
    """AC-0001-20 and AC-0001-21 both audit callers who have no account at all,
    which is why `usuario_id` is nullable."""
    alvo = uuid.uuid4()
    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=alvo,
            acao="auth.oidc_recusada",
            usuario_id=None,
            dados_anteriores={"motivo": "sem_conta", "dominio": "sc.gov.br"},
        ),
        correlation_id=uuid.uuid4(),
    )
    sessao.commit()
    assert _contar(sessao, alvo) == 1


def test_correlation_id_e_gravado(sessao: Session) -> None:
    uid, correlacao = uuid.uuid4(), uuid.uuid4()
    registrar(
        sessao,
        Evento(entidade_tipo="usuario", entidade_id=uid, acao="auth.login"),
        correlation_id=correlacao,
    )
    sessao.commit()
    gravado = sessao.execute(
        text("SELECT correlation_id FROM historico_movimentacao WHERE entidade_id = :i"),
        {"i": uid},
    ).scalar_one()
    assert gravado == correlacao


@pytest.mark.parametrize(
    "payload",
    [
        {"email_asserido": "ana@sc.gov.br"},
        {"motivo": "sem_conta", "detalhe": {"quem": "ana@sc.gov.br"}},
        {"tentativas": [{"endereco": "ana@sc.gov.br"}]},
    ],
    ids=["raso", "aninhado", "dentro-de-lista"],
)
def test_guarda_recusa_endereco_em_dados_anteriores(sessao: Session, payload: dict) -> None:
    """`lgpd.md` promises the audit table carries no personal data, and the table
    can never be corrected — so the promise is enforced rather than written down.

    The check is a heuristic, which is why the message names the remedy instead
    of only refusing.
    """
    with pytest.raises(DadoPessoalNoHistorico) as exc:
        registrar(
            sessao,
            Evento(
                entidade_tipo="usuario",
                entidade_id=uuid.uuid4(),
                acao="auth.oidc_recusada",
                dados_anteriores=payload,
            ),
            correlation_id=uuid.uuid4(),
        )
    assert "segredos.digerir" in str(exc.value)


def test_guarda_deixa_passar_o_payload_correto(sessao: Session) -> None:
    """What SPEC-0001 §8 actually prescribes: the HMAC and the bare domain."""
    from app.core.segredos import digerir

    registrar(
        sessao,
        Evento(
            entidade_tipo="usuario",
            entidade_id=uuid.uuid4(),
            acao="auth.falha",
            dados_anteriores={
                "motivo": "credenciais_invalidas",
                "email_hmac": digerir("ana@sc.gov.br").hex(),
                "dominio": "sc.gov.br",
            },
        ),
        correlation_id=uuid.uuid4(),
    )
    sessao.commit()
