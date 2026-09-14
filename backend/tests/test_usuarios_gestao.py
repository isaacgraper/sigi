"""Gestão de membros — AC-0001-12, -13, -14 e -29.

O AC-0001-29 é o caro. "Existe ao menos um gestor ativo" é um agregado entre
linhas, então duas requisições simultâneas podem cada uma ver dois gestores e
ambas comitarem — write skew, que isolamento por snapshot não impede. Um teste
que roda a corrida uma vez não prova nada.
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
    resposta = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_ac_0001_12_bloqueio(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-12 — bloquear derruba o login e o token que já estava na mão."""
    gestor = criar_usuario(perfil="gestor")
    alvo = criar_usuario(perfil="servidor")
    assert alvo.email
    token_do_alvo = _entrar(aplicacao, alvo)

    resposta = aplicacao.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=_entrar(aplicacao, gestor))
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "bloqueado"

    # O token continua com assinatura válida e mesmo assim não vale mais.
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

    # As sessões da pessoa ficam marcadas como encerradas, e não penduradas.
    vivas = sessao.execute(
        text("SELECT count(*) FROM sessao WHERE usuario_id = :u AND revogado_em IS NULL"),
        {"u": alvo.id},
    ).scalar_one()
    assert vivas == 0


def test_ac_0001_13_servidor_e_auditor_nao_gerenciam(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-13 — 403, nada muda, e a recusa vira linha de auditoria (AC-18)."""
    alvo = criar_usuario(perfil="servidor")
    antes = sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one()

    for perfil in ("servidor", "auditor"):
        quem = criar_usuario(perfil=perfil)
        cabecalhos = _entrar(aplicacao, quem)

        convite = aplicacao.post(
            USUARIOS,
            json={"email": f"x-{perfil}@sc.gov.br", "perfil": "servidor"},
            headers=cabecalhos,
        )
        bloqueio = aplicacao.post(f"{USUARIOS}/{alvo.id}/bloquear", headers=cabecalhos)
        desativacao = aplicacao.post(f"{USUARIOS}/{alvo.id}/desativar", headers=cabecalhos)

        for resposta in (convite, bloqueio, desativacao):
            assert resposta.status_code == 403, resposta.text
            assert resposta.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"

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
    # Os dois usuários criados pelo próprio teste, e nenhum pelos convites.
    assert sessao.execute(text("SELECT count(*) FROM usuario")).scalar_one() == antes + 2
    assert (
        sessao.execute(
            text("SELECT status FROM usuario WHERE id = :u"), {"u": alvo.id}
        ).scalar_one()
        == "ativo"
    )


def test_ac_0001_14_anonimizacao_preserva_historico(
    aplicacao: TestClient, criar_usuario: Callable[..., Usuario], sessao: Session
) -> None:
    """AC-0001-14 — o nome sai, o registro do que a pessoa fez fica."""
    gestor = criar_usuario(perfil="gestor")
    alvo = criar_usuario(perfil="servidor", nome="Pessoa Real", email="pessoa@sc.gov.br")
    _entrar(aplicacao, alvo)  # gera linha de histórico em nome dela

    sessao.rollback()
    antes = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE usuario_id = :u"),
        {"u": alvo.id},
    ).scalar_one()
    assert antes >= 1
    pseudonimo = sessao.execute(
        text("SELECT pseudonimo FROM usuario WHERE id = :u"), {"u": alvo.id}
    ).scalar_one()

    resposta = aplicacao.post(f"{USUARIOS}/{alvo.id}/desativar", headers=_entrar(aplicacao, gestor))
    assert resposta.status_code == 200, resposta.text

    sessao.rollback()
    depois = sessao.execute(
        text(
            "SELECT nome, email, senha_hash, oidc_subject, anonimizado_em, pseudonimo, status"
            " FROM usuario WHERE id = :u"
        ),
        {"u": alvo.id},
    ).one()
    assert depois.nome is None
    assert depois.email is None
    assert depois.senha_hash is None
    assert depois.anonimizado_em is not None
    assert depois.status == "desativado"
    # Estável: é coluna gerada a partir do id, então o histórico continua
    # resolvendo para o mesmo nome sem a tabela imutável ser reescrita.
    assert depois.pseudonimo == pseudonimo

    restantes = sessao.execute(
        text("SELECT count(*) FROM historico_movimentacao WHERE usuario_id = :u"),
        {"u": alvo.id},
    ).scalar_one()
    assert restantes >= antes
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
    """AC-0001-29 — o único gestor ativo não pode ser removido, nem por si mesmo.

    Banco próprio: a invariante é global, então este teste brigaria com qualquer
    outro que criasse gestores.
    """
    motor = create_engine(_para_sqlalchemy(banco_isolado[1]))
    try:
        with sessionmaker(bind=motor, expire_on_commit=False)() as s:
            unico = criar_usuario_em(s, perfil="gestor", email="unico@sc.gov.br")
            agora = datetime.datetime.now(datetime.UTC)

            for acao in (membros.bloquear, membros.desativar):
                try:
                    acao(
                        s,
                        ator=unico,
                        usuario_id=unico.id,
                        agora=agora,
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

            # Com dois, a desativação passa.
            segundo = criar_usuario_em(s, perfil="gestor", email="segundo@sc.gov.br")
            membros.desativar(
                s, ator=unico, usuario_id=segundo.id, agora=agora, correlation_id=uuid.uuid4()
            )
            s.commit()
            assert (
                s.execute(
                    text("SELECT status FROM usuario WHERE id = :u"), {"u": segundo.id}
                ).scalar_one()
                == "desativado"
            )
    finally:
        motor.dispose()


def test_ac_0001_29_corrida_entre_dois_gestores(
    banco_isolado: tuple[str, str], criar_usuario_em: Callable[..., Usuario]
) -> None:
    """Dois gestores desativados ao mesmo tempo: exatamente um sobra.

    Repetido, não uma vez só: write skew é probabilístico e uma passagem verde
    não distingue "está correto" de "não houve concorrência desta vez".
    """
    url = _para_sqlalchemy(banco_isolado[1])
    motor = create_engine(url, pool_size=8, max_overflow=8)
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)

    def desativar(alvo_id: uuid.UUID, ator_id: uuid.UUID) -> str:
        with fabrica() as s:
            try:
                ator = s.get(Usuario, ator_id)
                assert ator is not None
                membros.desativar(
                    s,
                    ator=ator,
                    usuario_id=alvo_id,
                    agora=datetime.datetime.now(datetime.UTC),
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
        for rodada in range(12):
            with fabrica() as s:
                a = criar_usuario_em(s, perfil="gestor", email=f"a{rodada}@sc.gov.br")
                b = criar_usuario_em(s, perfil="gestor", email=f"b{rodada}@sc.gov.br")
                ids = (a.id, b.id)
                # Deixa exatamente dois gestores ativos: o sobrevivente da
                # rodada anterior sai agora, enquanto `a` e `b` já existem e
                # seguram a invariante. Tentar removê-lo *depois* da corrida
                # seria pedir para remover o último gestor ativo, que é
                # justamente o que o gatilho recusa — e com razão.
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

            assert resultados.count("ok") == 1, f"rodada {rodada}: {resultados}"

            with fabrica() as s:
                vivos = s.execute(
                    text(
                        "SELECT count(*) FROM usuario WHERE perfil = 'gestor' AND status = 'ativo'"
                    )
                ).scalar_one()
                assert vivos == 1, f"rodada {rodada}: {vivos} gestores ativos"
    finally:
        motor.dispose()
