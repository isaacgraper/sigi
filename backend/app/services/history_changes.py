"""What each event of an entity changed, before and after (SPEC-0007 AC-0007-10).

A row stores only the value before (AC-0007-05). The value after is the value
before of the next row, and for the newest row the entity as it is now, so the
rows of one entity are walked from the newest to the oldest, rewinding a copy
of its state at each one. Pure: no session, unit-tested without a database.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.constants.historico import (
    ACAO_ROTULO,
    ACRESCIMO_KEYS,
    CREATION_ACOES,
    DETAILS_ONLY,
    DETALHE_ROTULO,
    FIELDS,
    IMPLIED_PRIOR,
    ITEM_LINE_KEY,
    ITEM_QUANTIDADE_KEY,
    NUMERIC_TIPOS,
    REMOVAL_ACOES,
    RENAMED_KEY,
    STATUS_KEY,
    TIPO_ITENS,
)


@dataclass(frozen=True)
class Change:
    """A field the event changed."""

    campo: str
    rotulo: str
    tipo: str
    antes: Any
    depois: Any


@dataclass(frozen=True)
class Detail:
    """A recorded key that is not a change: context, or a field left as it was."""

    campo: str
    rotulo: str
    valor: Any


@dataclass(frozen=True)
class EventChanges:
    """The label of an event, what it changed and what else it recorded."""

    acao_rotulo: str
    alteracoes: Sequence[Change]
    detalhes: Sequence[Detail]


@dataclass(frozen=True)
class Entry:
    """One row of an entity, with the acréscimo of its aditivo when it has one."""

    id: uuid.UUID
    acao: str
    ocorrido_em: datetime.datetime
    dados: Mapping[str, Any] | None
    acrescimo: decimal.Decimal | None = None


def label_of(acao: str) -> str:
    """The pt-BR label of an acao, or the acao itself."""
    return ACAO_ROTULO.get(acao, acao)


def details_only(entidade: str, entry: Entry) -> EventChanges:
    """An event read without any state: every recorded key is a detail."""
    fields: Mapping[str, tuple[str, str]] = FIELDS.get(entidade) or {}
    return EventChanges(
        acao_rotulo=label_of(entry.acao),
        alteracoes=(),
        detalhes=tuple(_detail(fields, key, value) for key, value in (entry.dados or {}).items()),
    )


def walk(
    entidade: str, entries: Sequence[Entry], state: Mapping[str, Any] | None
) -> dict[uuid.UUID, EventChanges]:
    """What each row of one entity changed, given the entity as it is now.

    `state` holds the entity's fields as `jsonable` stores them; `None`, or an
    entidade with no fields, means SIGI holds no state for it and every event
    carries only details.
    """
    fields = FIELDS.get(entidade)
    if fields is None or state is None:
        return {entry.id: details_only(entidade, entry) for entry in entries}
    current = dict(state)
    result: dict[uuid.UUID, EventChanges] = {}
    for entry in sorted(entries, key=lambda e: (e.ocorrido_em, e.id), reverse=True):
        result[entry.id] = _rewind(entidade, fields, entry, current)
    return result


def _rewind(
    entidade: str,
    fields: Mapping[str, tuple[str, str]],
    entry: Entry,
    state: dict[str, Any],
) -> EventChanges:
    """The changes of one event; `state` goes from after it to before it."""
    dados = dict(entry.dados or {})
    label = label_of(entry.acao)
    if entry.acao in DETAILS_ONLY:
        return details_only(entidade, entry)
    if entry.acao in CREATION_ACOES:
        created = [
            Change(key, rotulo, tipo, None, _normal(tipo, state[key], entidade))
            for key, (rotulo, tipo) in fields.items()
            if state.get(key) not in (None, [], "")
        ]
        return EventChanges(label, tuple(created), _details(fields, dados, skip=()))
    if entry.acao in REMOVAL_ACOES:
        removed = [
            Change(key, rotulo, tipo, _normal(tipo, value, entidade), None)
            for key, value in dados.items()
            if key in fields
            for rotulo, tipo in (fields[key],)
        ]
        for key in dados:
            if key in fields:
                state[key] = dados[key]
        state[REMOVAL_ACOES[entry.acao]] = None
        return EventChanges(label, tuple(removed), _details(fields, dados, skip=fields.keys()))

    status_after = state.get(STATUS_KEY)
    recorded = {RENAMED_KEY.get((entry.acao, key), key): value for key, value in dados.items()}
    implied: Mapping[str, Any] = (
        IMPLIED_PRIOR.get((entry.acao, status_after)) or IMPLIED_PRIOR.get((entry.acao, None)) or {}
    )
    for key, value in implied.items():
        recorded.setdefault(key, value)

    changes: list[Change] = []
    details: list[Detail] = []
    for key, antes in recorded.items():
        if key not in fields:
            details.append(_detail(fields, key, antes))
            continue
        rotulo, tipo = fields[key]
        if key in ACRESCIMO_KEYS:
            if entry.acrescimo is None:
                details.append(_detail(fields, key, antes))
                continue
            depois: Any = str(decimal.Decimal(str(antes)) + entry.acrescimo)
        else:
            depois = state.get(key)
            state[key] = antes
        if _same(tipo, antes, depois, entidade):
            if key not in implied or key in dados:
                details.append(Detail(key, rotulo, _normal(tipo, antes, entidade)))
            continue
        before, after = _normal(tipo, antes, entidade), _normal(tipo, depois, entidade)
        changes.append(Change(key, rotulo, tipo, before, after))
    return EventChanges(label, tuple(changes), tuple(details))


def _details(
    fields: Mapping[str, tuple[str, str]], dados: Mapping[str, Any], *, skip: Any
) -> tuple[Detail, ...]:
    return tuple(_detail(fields, key, value) for key, value in dados.items() if key not in skip)


def _detail(fields: Mapping[str, tuple[str, str]], key: str, value: Any) -> Detail:
    rotulo = DETALHE_ROTULO.get(key) or (fields[key][0] if key in fields else key)
    return Detail(key, rotulo, value)


def _same(tipo: str, antes: Any, depois: Any, entidade: str) -> bool:
    return _normal(tipo, antes, entidade) == _normal(tipo, depois, entidade)


def _normal(tipo: str, value: Any, entidade: str) -> Any:
    """A value in the form two of them compare in, and the screen reads."""
    if value is None:
        return None
    if tipo in NUMERIC_TIPOS:
        return _number(value)
    if tipo == TIPO_ITENS:
        line_key = ITEM_LINE_KEY.get(entidade)
        lines = [
            {str(k): (_number(v) if k == ITEM_QUANTIDADE_KEY else str(v)) for k, v in line.items()}
            for line in value
        ]
        return sorted(lines, key=lambda line: str(line.get(line_key or "", "")))
    if isinstance(value, bool):
        return value
    return str(value)


def _number(value: Any) -> str:
    try:
        number = decimal.Decimal(str(value))
    except decimal.InvalidOperation:
        return str(value)
    return format(number.normalize(), "f")
