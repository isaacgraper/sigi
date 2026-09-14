"""Member management — AC-0001-12, -13, -14 and -29.

AC-0001-29 is the expensive one. "At least one active gestor exists" is an
aggregate across rows, so two concurrent requests can each see two gestores and
both commit — write skew, which snapshot isolation does not prevent. A test that
runs the race once proves nothing.
"""

from __future__ import annotations

import concurrent.futures
import datetime
import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.usuario import Usuario
from app.services import membros
from app.services.erros import UltimoGestor
from tests.conftest import _para_sqlalchemy

SENHA = "SenhaCorreta-12345"
USUARIOS = "/api/v1/usuarios"


def _entrar(aplicacao: TestClient, usuario: Usuario) -> dict[str, str]:
    response = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_ac_0001_12_bloqueio(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-12 — blocking kills the login and the token already in hand."""
    gestor = criar_usuario(perfil="gestor")
    alvo = criar_usuario(perfil="servidor")
    assert alvo.email
    token_do_alvo = _entrar(aplicacao, alvo)

    response = aplicacao.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=_entrar(aplicacao, gestor))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "bloqueado"

    # The token still carries a valid signature and is no longer accepted.
    assert aplicacao.get("/api/v1/auth/me", headers=token_do_alvo).status_code == 401
    assert (
        aplicacao.post("/api/v1/auth/login", json={"email": alvo.email, "senha": SENHA}).status_code
        == 401
    )

    sessao.rollback()
    auditoria = sessao.execute(
        text(
            "SELECT usuario_id FROM historico_movimentacao"
            " WHERE acao = 'usuario.bloqueado' AND entidade_id = :alvo"
        ),
        {"alvo": alvo.id},
    ).scalar_one()
    assert auditoria == gestor.id

    # Their sessions are marked ended rather than left dangling.
    vivas = sessao.execute(
        text("SELECT count(*) FROM sessao WHERE usuario_id = :u AND revogado_em IS NULL"),
        {"u": alvo.id},
    ).scalar_one()
    assert vivas == 0


def test_ac_0001_13_servidor_e_auditor_nao_gerenciam(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-13 — 403, nothing changes, and the refusal becomes an audit row (AC-18)."""
    alvo = criar_usuario(perfil="servidor")
    before = sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one()

    for perfil in ("servidor", "auditor"):
        quem = criar_usuario(perfil=perfil)
        headers = _entrar(aplicacao, quem)

        convite = aplicacao.post(
            USUARIOS,
            json={"email": f"x-{perfil}@sc.gov.br", "perfil": "servidor"},
            headers=headers,
        )
        bloqueio = aplicacao.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=headers)
        desativacao = aplicacao.post(f"{USUARIOS}/{alvo.id}/desativar", headers=headers)

        for response in (convite, bloqueio, desativacao):
            assert response.status_code == 403, response.text
            assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"

        sessao.rollback()
        negadas = sessao.execute(
            text(
                "SELECT count(*) FROM historico_movimentacao"
                " WHERE acao = 'auth.negada' AND usuario_id = :u"
            ),
            {"u": quem.id},
        ).scalar_one()
        assert negadas == 3, f"{perfil} devia ter 3 recusas auditadas"

    sessao.rollback()
    # The two usuarios the test created, and none from the invitations.
    assert sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one() == before + 2
    assert (
        sessao.execute(
            text("SELECT status FROM usuario WHERE id = :u"), {"u": alvo.id}
        ).scalar_one()
        == "ativo"
    )


def test_ac_0001_14_anonimizacao_preserva_historico(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-14 — the name goes, the record of what they did stays."""
    gestor = criar_usuario(perfil="gestor")
    alvo = criar_usuario(perfil="servidor", nome="Pessoa Real", email="pessoa@sc.gov.br")
    _entrar(aplicacao, alvo)  # gera linha de histórico em nome dela

    sessao.rollback()
    before = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE usuario_id = :u"),
        {"u": alvo.id},
    ).scalar_one()
    assert before >= 1
    pseudonimo = sessao.execute(
        text("SELECT pseudonimo FROM usuario WHERE id = :u"), {"u": alvo.id}
    ).scalar_one()

    response = aplicacao.post(f"{USUARIOS}/{alvo.id}/desativar", headers=_entrar(aplicacao, gestor))
    assert response.status_code == 200, response.text

    sessao.rollback()
    after = sessao.execute(
        text(
            "SELECT nome, email, senha_hash, oidc_subject, anonimizado_em, pseudonimo, status"
            " FROM usuario WHERE id = :u"
        ),
        {"u": alvo.id},
    ).one()
    assert after.nome is None
    assert after.email is None
    assert after.senha_hash is None
    assert after.anonimizado_em is not None
    assert after.status == "desativado"
    # Stable: a column generated from the id, so the history keeps resolving
    # to the same name without the immutable table being rewritten.
    assert after.pseudonimo == pseudonimo

    restantes = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE usuario_id = :u"),
        {"u": alvo.id},
    ).scalar_one()
    assert restantes >= before
    orfas = sessao.execute(
        text(
            "SELECT count(*) FROM historico_movimentacao h"
            " LEFT JOIN usuario u ON u.id = h.usuario_id"
            " WHERE h.usuario_id IS NOT NULL AND u.id IS NULL"
        )
    ).scalar_one()
    assert orfas == 0


def test_ac_0001_29_ultimo_gestor(
    banco_isolado: tuple[str, str], criar_usuario_em: Callable[..., Usuario]
) -> None:
    """AC-0001-29 — the only active gestor cannot be removed, not even by itself.

    Its own database: the invariant is global, so this test would fight any
    other that creates gestores.
    """
    engine = create_engine(_para_sqlalchemy(banco_isolado[1]))
    try:
        with sessionmaker(bind=engine, expire_on_commit=False)() as s:
            unico = criar_usuario_em(s, perfil="gestor", email="unico@sc.gov.br")
            now = datetime.datetime.now(datetime.UTC)

            for acao in (membros.bloquear, membros.desativar):
                try:
                    acao(
                        s,
                        ator=unico,
                        usuario_id=unico.id,
                        now=now,
                        correlation_id=uuid.uuid4(),
                    )
                    raise AssertionError(f"{acao.__name__} devia ter sido recusada")
                except UltimoGestor:
                    s.rollback()

            s.rollback()
            estado = s.execute(
                text("SELECT perfil, status FROM usuario WHERE id = :u"), {"u": unico.id}
            ).one()
            assert estado.perfil == "gestor"
            assert estado.status == "ativo"

            # With two, the deactivation goes through.
            segundo = criar_usuario_em(s, perfil="gestor", email="segundo@sc.gov.br")
            membros.desativar(
                s, ator=unico, usuario_id=segundo.id, now=now, correlation_id=uuid.uuid4()
            )
            s.commit()
            assert (
                s.execute(
                    text("SELECT status FROM usuario WHERE id = :u"), {"u": segundo.id}
                ).scalar_one()
                == "desativado"
            )
    finally:
        engine.dispose()


def test_ac_0001_29_corrida_entre_dois_gestores(
    banco_isolado: tuple[str, str], criar_usuario_em: Callable[..., Usuario]
) -> None:
    """Two gestores deactivated at once: exactly one survives.

    Repeated, not run once: write skew is probabilistic, and a single green pass
    does not distinguish "correct" from "no concurrency happened this time".
    """
    url = _para_sqlalchemy(banco_isolado[1])
    engine = create_engine(url, pool_size=8, max_overflow=8)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def desativar(alvo_id: uuid.UUID, ator_id: uuid.UUID) -> str:
        with factory() as s:
            try:
                ator = s.get(Usuario, ator_id)
                assert ator is not None
                membros.desativar(
                    s,
                    ator=ator,
                    usuario_id=alvo_id,
                    now=datetime.datetime.now(datetime.UTC),
                    correlation_id=uuid.uuid4(),
                )
                s.commit()
                return "ok"
            except UltimoGestor:
                s.rollback()
                return "recusado"
            except Exception:
                s.rollback()
                raise

    try:
        for round_ in range(12):
            with factory() as s:
                a = criar_usuario_em(s, perfil="gestor", email=f"a{round_}@sc.gov.br")
                b = criar_usuario_em(s, perfil="gestor", email=f"b{round_}@sc.gov.br")
                ids = (a.id, b.id)
                # Leave exactly two active gestores: the previous round's
                # survivor goes now, while `a` and `b` already exist and hold
                # the invariant. Removing it *after* the race would be asking to
                # remove the last active gestor, which is what the trigger
                # refuses — rightly.
                s.execute(
                    text(
                        "UPDATE usuario SET status = 'desativado', nome = NULL,"
                        " email = NULL, senha_hash = NULL, oidc_subject = NULL,"
                        " anonimizado_em = now()"
                        " WHERE perfil = 'gestor' AND status = 'ativo'"
                        "   AND id <> :a AND id <> :b"
                    ),
                    {"a": ids[0], "b": ids[1]},
                )
                s.commit()

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                resultados = list(
                    pool.map(lambda par: desativar(*par), [(ids[0], ids[1]), (ids[1], ids[0])])
                )

            assert resultados.count("ok") == 1, f"round_ {round_}: {resultados}"

            with factory() as s:
                vivos = s.execute(
                    text(
                        "SELECT count(*) FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'"
                    )
                ).scalar_one()
                assert vivos == 1, f"round_ {round_}: {vivos} gestores ativos"
    finally:
        engine.dispose()
