"""A matriz de permissão — AC-0001-15, -16, -17 e -23.

Os três primeiros critérios falam da *tabela de rotas da aplicação*, não de uma
lista escrita à mão. Então os testes também: eles percorrem o que a aplicação
montada expõe e crescem sozinhos a cada rota nova. Uma lista literal aqui
envelheceria exatamente como a tabela paralela que o AC-0001-23 existe para
proibir.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.autorizacao import (
    METODOS_DE_ESCRITA,
    Decisao,
    Exige,
    RotaSemDecisao,
    decisoes_da_rota,
    rotas_da_aplicacao,
    verificar_cobertura,
)
from app.main import create_app
from app.models.usuario import PERFIS, Usuario

SENHA = "SenhaCorreta-12345"


def _rotas_com_decisao() -> list[tuple[str, str, Decisao]]:
    return [
        (metodo, caminho, decisoes[0])
        for caminho, rota in rotas_da_aplicacao(create_app())
        if (decisoes := decisoes_da_rota(rota))
        for metodo in sorted(rota.methods or set())
        if metodo != "HEAD"
    ]


def _concretizar(caminho: str) -> str:
    """Trocar `{id}` por um uuid qualquer.

    O recurso não precisa existir: a decisão de perfil vem antes de qualquer
    busca, e é justamente isso que se está afirmando.
    """
    partes = [str(uuid.uuid4()) if p.startswith("{") else p for p in caminho.strip("/").split("/")]
    return "/" + "/".join(partes)


def _autenticar(aplicacao: TestClient, usuario: Usuario) -> dict[str, str]:
    resposta = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.mark.parametrize("perfil", PERFIS)
def test_matriz_por_perfil(
    perfil: str,
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
) -> None:
    """AC-0001-15 (gestor), AC-0001-16 (servidor) e AC-0001-17 (auditor).

    A afirmação é sobre o motivo da recusa, não sobre o código de sucesso: um
    corpo vazio faz a rota permitida responder 422, e 422 é "passou pela
    autorização". O que nenhuma rota permitida pode devolver é 403.
    """
    usuario = criar_usuario(perfil=perfil)
    cabecalhos = _autenticar(aplicacao, usuario)

    verificadas = 0
    for metodo, caminho, decisao in _rotas_com_decisao():
        resposta = aplicacao.request(metodo, _concretizar(caminho), json={}, headers=cabecalhos)
        nega = isinstance(decisao, Exige) and bool(decisao.perfis) and perfil not in decisao.perfis
        if nega:
            assert resposta.status_code == 403, f"{metodo} {caminho} devia recusar {perfil}"
            assert resposta.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"
        else:
            assert resposta.status_code != 403, f"{metodo} {caminho} recusou {perfil} sem motivo"
        verificadas += 1

    assert verificadas, "nenhuma rota declarou decisão de acesso — o teste passaria vazio"


def test_ac_0001_23_toda_rota_de_escrita_tem_entrada() -> None:
    """A aplicação real sobe: nenhuma rota de escrita sem decisão."""
    aplicacao = create_app()
    verificar_cobertura(aplicacao)

    escritas = [
        f"{metodo} {caminho}"
        for caminho, rota in rotas_da_aplicacao(aplicacao)
        for metodo in (rota.methods or set()) & METODOS_DE_ESCRITA
    ]
    assert escritas, "sem rota de escrita, o critério passaria por vacuidade"


def test_ac_0001_23_rota_sem_decisao_quebra_o_build() -> None:
    """Controle negativo, e é ele que dá sentido ao teste acima.

    Sem isto, um `verificar_cobertura` que não verificasse nada deixaria os dois
    verdes — que é o modo de falha exato que este critério tenta impedir.
    """
    aplicacao = FastAPI()

    @aplicacao.post("/api/v1/esqueceram")
    def esqueceram() -> dict[str, str]:
        return {}

    with pytest.raises(RotaSemDecisao) as exc:
        verificar_cobertura(aplicacao)
    assert "POST /api/v1/esqueceram" in str(exc.value)


def test_leitura_sem_decisao_nao_quebra() -> None:
    """O critério fala de rotas que *mudam estado*. `/health` é GET e não
    precisa declarar nada — exigir declaração de toda leitura transformaria a
    verificação em ruído, e ruído é o que se aprende a ignorar."""
    aplicacao = FastAPI()

    @aplicacao.get("/health")
    def saude() -> dict[str, str]:
        return {"status": "ok"}

    verificar_cobertura(aplicacao)


def test_perfil_inexistente_na_matriz_e_recusado_na_montagem() -> None:
    """`Exige("gestro")` recusaria todo mundo, para sempre, em silêncio."""
    with pytest.raises(ValueError, match="gestro"):
        Exige("gestro")


# No nível do módulo, e não dentro do teste: com `from __future__ import
# annotations` as anotações viram texto, e o FastAPI as resolve contra o
# namespace do módulo — uma dependência declarada numa variável local não seria
# encontrada, e o teste falharia por um motivo que não é o que ele investiga.
GUARDA = Exige("gestor")


def _intermediaria(usuario: Annotated[Usuario, Depends(GUARDA)]) -> Usuario:
    return usuario


def test_decisao_aninhada_e_encontrada() -> None:
    """A decisão pode estar sob outra dependência, e a busca precisa descer.

    Se não descesse, uma rota protegida passaria por desprotegida e o
    AC-0001-23 acusaria justamente a rota errada.
    """
    aplicacao = FastAPI()

    @aplicacao.post("/api/v1/coisa")
    def coisa(usuario: Annotated[Usuario, Depends(_intermediaria)]) -> dict[str, str]:
        return {}

    rota = next(r for c, r in rotas_da_aplicacao(aplicacao) if c.endswith("coisa"))
    assert decisoes_da_rota(rota) == [GUARDA]
    verificar_cobertura(aplicacao)
