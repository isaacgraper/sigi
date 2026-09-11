"""Who is calling, and whether they still may.

AC-0001-08 is the whole point of this module: `usuario.ativo` is checked on
**every** request, not only at login. That costs one indexed lookup per
authenticated call, and it is the difference between a deactivation that takes
effect now and one that takes effect in up to fifteen minutes — which is not a
deactivation.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Sequence
from typing import Annotated

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.applications import Starlette

from app.core.correlacao import atual
from app.core.db import obter_sessao
from app.core.seguranca import TokenInvalido, verificar_access_token
from app.models.usuario import PERFIS, Usuario
from app.repositories import usuario as repo
from app.services.erros import PerfilNaoAutorizado, UsuarioInativo

ESQUEMA = "bearer"


def _token_do_cabecalho(request: Request) -> str:
    cabecalho = request.headers.get("authorization", "")
    tipo, _, valor = cabecalho.partition(" ")
    if tipo.lower() != ESQUEMA or not valor.strip():
        raise TokenInvalido("Sua sessão não é válida. Entre novamente.")
    return valor.strip()


def usuario_atual(request: Request, sessao: Annotated[Session, Depends(obter_sessao)]) -> Usuario:
    claims = verificar_access_token(_token_do_cabecalho(request))
    usuario = repo.por_id(sessao, claims.usuario_id)
    if usuario is None or not usuario.ativo:
        # Same response whether the account was deleted, blocked or deactivated:
        # the caller holds a valid signature, so they already know the account
        # existed, but they learn nothing further about its state.
        raise UsuarioInativo()
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]


# ── A matriz de permissão (AC-0001-15 a -18, -23) ───────────────────────────
#
# A decisão vive na própria rota, não numa tabela paralela. Uma tabela separada
# é a que envelhece: alguém acrescenta um endpoint, esquece a linha, e o
# endpoint fica sem decisão nenhuma. Aqui a rota não sobe sem declarar uma — e o
# AC-0001-23 é literalmente essa verificação, feita quando a aplicação é
# montada.


class Decisao:
    """Base das declarações de acesso. A existência dela é o contrato."""

    def descricao(self) -> str:  # pragma: no cover - sobrescrito
        raise NotImplementedError


class Publica(Decisao):
    """Rota deliberadamente sem autenticação.

    Existe para ser explícita: sem ela, "não tem decisão" e "decidiram que é
    pública" seriam o mesmo estado, e o padrão de quem esquece viraria acesso
    aberto. O default de uma entrada ausente é recusa, nunca permissão.
    """

    def __call__(self) -> None:
        return None

    def descricao(self) -> str:
        return "pública"


class Exige(Decisao):
    """Exige autenticação, e opcionalmente um conjunto de perfis."""

    def __init__(self, *perfis: str) -> None:
        desconhecidos = set(perfis) - set(PERFIS)
        if desconhecidos:
            # Um perfil com erro de digitação recusaria todo mundo para sempre,
            # silenciosamente. Melhor não subir.
            raise ValueError(f"perfis inexistentes na matriz: {sorted(desconhecidos)}")
        self.perfis = frozenset(perfis)

    def __call__(self, request: Request, usuario: UsuarioAtual) -> Usuario:
        if self.perfis and usuario.perfil not in self.perfis:
            _auditar_recusa(request, usuario)
            raise PerfilNaoAutorizado()
        return usuario

    def descricao(self) -> str:
        return ", ".join(sorted(self.perfis)) if self.perfis else "autenticado"


def _auditar_recusa(request: Request, usuario: Usuario) -> None:
    """AC-0001-18 — um 403 sem rastro é indistinguível de um ataque que nunca
    houve. Em transação própria, porque a requisição vai levantar e levar a dela
    junto — e o pedido não mudou nada, então não há mutação a que se agarrar."""
    from app.services.auditoria import Evento, registrar_avulso

    rota = request.scope.get("route")
    registrar_avulso(
        Evento(
            entidade_tipo="usuario",
            entidade_id=usuario.id,
            acao="auth.negada",
            usuario_id=usuario.id,
            dados_anteriores={
                # O caminho declarado, não o concreto: um id na rota é dado de
                # negócio e a tabela de auditoria não pode ser corrigida depois.
                "rota": getattr(rota, "path", request.url.path),
                "metodo": request.method,
                "perfil": usuario.perfil,
            },
        ),
        correlation_id=_correlation_id(request),
    )


def _correlation_id(request: Request) -> uuid.UUID:
    bruto = request.scope.get("state", {}).get("correlation_id")
    return bruto if isinstance(bruto, uuid.UUID) else atual()


METODOS_DE_ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def decisoes_da_rota(rota: APIRoute) -> list[Decisao]:
    """Toda `Decisao` alcançável a partir da rota, inclusive aninhada."""

    def descer(dependente: Dependant) -> list[Decisao]:
        encontradas: list[Decisao] = (
            [dependente.call] if isinstance(dependente.call, Decisao) else []
        )
        return encontradas + [d for sub in dependente.dependencies for d in descer(sub)]

    return descer(rota.dependant)


class RotaSemDecisao(RuntimeError):
    """Uma rota de escrita subiu sem declarar quem pode chamá-la."""


def rotas_da_aplicacao(app: Starlette) -> Iterator[tuple[str, APIRoute]]:
    """Todo `APIRoute` da aplicação, com o caminho já completo.

    Descer é obrigatório: desde o FastAPI 0.141 um `include_router` não achata
    as rotas em `app.routes` — deixa lá um wrapper com o router original dentro.
    Uma varredura rasa não veria nenhuma rota de escrita e o AC-0001-23 passaria
    por vacuidade, dizendo "está tudo coberto" sobre uma lista vazia. O acesso é
    por duck typing de propósito: a forma interna disso já mudou uma vez.
    """

    def descer(rotas: Sequence[object], prefixo: str = "") -> Iterator[tuple[str, APIRoute]]:
        for rota in rotas:
            if isinstance(rota, APIRoute):
                yield prefixo + rota.path, rota
                continue
            interno = getattr(rota, "original_router", None)
            if interno is not None:
                contexto = getattr(rota, "include_context", None)
                yield from descer(interno.routes, prefixo + getattr(contexto, "prefix", ""))
            elif hasattr(rota, "routes"):
                yield from descer(rota.routes, prefixo + str(getattr(rota, "path", "")))

    yield from descer(app.routes)


def verificar_cobertura(app: Starlette) -> None:
    """AC-0001-23 — nenhuma rota de escrita sobe sem decisão de acesso.

    Roda na montagem da aplicação, então quebra o build e não a produção. É o
    que mantém AC-0001-15/-16/-17 honestos conforme o sistema cresce: um
    endpoint acrescentado sem decisão é um buraco que ninguém escolheu abrir.
    """
    faltantes = [
        f"{metodo} {caminho}"
        for caminho, rota in rotas_da_aplicacao(app)
        for metodo in sorted((rota.methods or set()) & METODOS_DE_ESCRITA)
        if not decisoes_da_rota(rota)
    ]
    if faltantes:
        raise RotaSemDecisao(
            "rotas de escrita sem decisão de acesso: "
            + ", ".join(faltantes)
            + ". Declare uma: Depends(Exige('gestor')) ou Depends(Publica()) "
            "quando a rota é deliberadamente aberta."
        )
