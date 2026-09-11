"""Writing the audit trail (RN06, RNF08, SPEC-0001 §8).

The contract, from `CLAUDE.md`: every mutation writes a history row **in the
same transaction as the mutation**, and if the history write fails, the mutation
fails. That is why this takes the caller's `Session` and never opens or commits
one of its own — a writer with its own transaction could leave a mutation
without its record, which in an auditability product is the defect the product
exists to prevent.
"""

from __future__ import annotations

import datetime
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.historico import HistoricoMovimentacao
from app.repositories.historico import inserir


class DadoPessoalNoHistorico(RuntimeError):
    """A caller tried to write personal data into an immutable table.

    Not an `ErroDominio`: no user caused this and no message would help them.
    It is a bug, and the right outcome is a 500 plus a fix.
    """


@dataclass(frozen=True)
class Evento:
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


def registrar(
    sessao: Session,
    evento: Evento,
    *,
    correlation_id: uuid.UUID,
    momento: datetime.datetime | None = None,
) -> None:
    _recusar_dado_pessoal(evento.dados_anteriores)
    inserir(
        sessao,
        HistoricoMovimentacao(
            ocorrido_em=momento or datetime.datetime.now(datetime.UTC),
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


def _recusar_dado_pessoal(dados: Mapping[str, Any] | None) -> None:
    if dados is None:
        return
    for caminho, valor in _percorrer(dados):
        if isinstance(valor, str) and _PARECE_EMAIL.search(valor):
            raise DadoPessoalNoHistorico(
                f"dados_anteriores[{caminho}] parece conter um endereço de e-mail. "
                "A tabela de auditoria nunca pode ser corrigida, então ela não "
                "carrega dado pessoal: use app.core.segredos.digerir() e grave o "
                "HMAC mais o domínio, como manda a SPEC-0001 §8."
            )


def _percorrer(valor: Any, caminho: str = "") -> list[tuple[str, Any]]:
    if isinstance(valor, Mapping):
        return [
            item
            for chave, sub in valor.items()
            for item in _percorrer(sub, f"{caminho}.{chave}" if caminho else str(chave))
        ]
    if isinstance(valor, list | tuple):
        return [item for i, sub in enumerate(valor) for item in _percorrer(sub, f"{caminho}[{i}]")]
    return [(caminho, valor)]
