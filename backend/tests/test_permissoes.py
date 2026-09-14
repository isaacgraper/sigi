"""The permission matrix — AC-0001-15, -16, -17 and -23.

The first three criteria speak of the *application's route table*, not of a
hand-written list. So do these tests: they walk what the assembled app exposes
and grow on their own with each new route. A literal list here would age exactly
like the parallel table AC-0001-23 exists to forbid.
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
    app_routes,
    route_decisions,
    verify_coverage,
)
from app.main import create_app
from app.models.usuario import PERFIS, Usuario

SENHA = "SenhaCorreta-12345"


def _rotas_com_decisao() -> list[tuple[str, str, Decisao]]:
    return [
        (metodo, path, decisoes[0])
        for path, rota in app_routes(create_app())
        if (decisoes := route_decisions(rota))
        for metodo in sorted(rota.methods or set())
        if metodo != "HEAD"
    ]


def _concretizar(path: str) -> str:
    """Swap `{id}` for any uuid.

    The resource need not exist: the perfil decision comes before any lookup,
    and that is precisely what is being asserted.
    """
    partes = [str(uuid.uuid4()) if p.startswith("{") else p for p in path.strip("/").split("/")]
    return "/" + "/".join(partes)


def _autenticar(aplicacao: TestClient, usuario: Usuario) -> dict[str, str]:
    response = aplicacao.post("/api/v1/auth/login", json={"email": usuario.email, "senha": SENHA})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize("perfil", PERFIS)
def test_matriz_por_perfil(
    perfil: str,
    aplicacao: TestClient,
    criar_usuario: Callable[..., Usuario],
) -> None:
    """AC-0001-15 (gestor), AC-0001-16 (servidor) and AC-0001-17 (auditor).

    The assertion is about the reason for refusal, not the success code: an
    empty body makes a permitted route answer 422, and 422 means "got past
    authorisation". What no permitted route may return is 403.
    """
    usuario = criar_usuario(perfil=perfil)
    headers = _autenticar(aplicacao, usuario)

    verificadas = 0
    for metodo, path, decisao in _rotas_com_decisao():
        response = aplicacao.request(metodo, _concretizar(path), json={}, headers=headers)
        nega = isinstance(decisao, Exige) and bool(decisao.perfis) and perfil not in decisao.perfis
        if nega:
            assert response.status_code == 403, f"{metodo} {path} devia recusar {perfil}"
            assert response.json()["error"]["code"] == "PERFIL_NAO_AUTORIZADO"
        else:
            assert response.status_code != 403, f"{metodo} {path} recusou {perfil} sem motivo"
        verificadas += 1

    assert verificadas, "nenhuma rota declarou decisão de acesso — o teste passaria vazio"


def test_ac_0001_23_toda_rota_de_escrita_tem_entrada() -> None:
    """The real application starts: no write route without a decision."""
    aplicacao = create_app()
    verify_coverage(aplicacao)

    escritas = [
        f"{metodo} {path}"
        for path, rota in app_routes(aplicacao)
        for metodo in (rota.methods or set()) & METODOS_DE_ESCRITA
    ]
    assert escritas, "sem rota de escrita, o critério passaria por vacuidade"


def test_ac_0001_23_rota_sem_decisao_quebra_o_build() -> None:
    """The negative control, and what gives the test above its meaning.

    Without it, a `verify_coverage` that verified nothing would leave both
    green — the exact failure mode this criterion tries to prevent.
    """
    aplicacao = FastAPI()

    @aplicacao.post("/api/v1/esqueceram")
    def esqueceram() -> dict[str, str]:
        return {}

    with pytest.raises(RotaSemDecisao) as exc:
        verify_coverage(aplicacao)
    assert "POST /api/v1/esqueceram" in str(exc.value)


def test_leitura_sem_decisao_nao_quebra() -> None:
    """The criterion speaks of routes that *change state*. `/health` is a GET
    and declares nothing — requiring a declaration on every read would turn the
    check into noise, and noise is what people learn to ignore."""
    aplicacao = FastAPI()

    @aplicacao.get("/health")
    def saude() -> dict[str, str]:
        return {"status": "ok"}

    verify_coverage(aplicacao)


def test_perfil_inexistente_na_matriz_e_recusado_na_montagem() -> None:
    """`Exige("gestro")` would refuse everybody, for ever, silently."""
    with pytest.raises(ValueError, match="gestro"):
        Exige("gestro")


# At module level rather than inside the test: with `from __future__ import
# annotations` the annotations become text, and FastAPI resolves them against
# the module namespace — a dependency declared in a local would not be found,
# and the test would fail for a reason other than the one it investigates.
GUARDA = Exige("gestor")


def _intermediaria(usuario: Annotated[Usuario, Depends(GUARDA)]) -> Usuario:
    return usuario


def test_decisao_aninhada_e_encontrada() -> None:
    """The decision can sit under another dependency, and the search must descend.

    If it did not, a protected route would pass for unprotected and AC-0001-23
    would report the wrong route.
    """
    aplicacao = FastAPI()

    @aplicacao.post("/api/v1/coisa")
    def coisa(usuario: Annotated[Usuario, Depends(_intermediaria)]) -> dict[str, str]:
        return {}

    rota = next(r for c, r in app_routes(aplicacao) if c.endswith("coisa"))
    assert route_decisions(rota) == [GUARDA]
    verify_coverage(aplicacao)
