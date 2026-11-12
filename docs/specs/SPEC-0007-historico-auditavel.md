---
id: SPEC-0007
title: Histórico auditável imutável
status: Approved
version: 1.1
owner: Isaac Kleimmann Graper
satisfies: [RF06, RF10, RN06, RNF08]
depends_on: [SPEC-0001, SPEC-0004, SPEC-0005]
milestone: M2
---

# SPEC-0007 — Histórico auditável imutável

## 1. Purpose

Prestação de contas is the reason this system exists. The audit trail is
therefore not a feature but a constraint on every other feature: any write path
that does not produce a history row is a defect, regardless of what it does correctly.

## 2. Behaviour

Most of this was built with SPEC-0001, which every later spec reuses. Those
criteria are marked with the test that proves them; what is new here is reading
the history (AC-0007-08, -09), the cycle of an insumo (AC-0007-07) and what each
event changed (AC-0007-10).

**AC-0007-01** — Every write leaves one row
```gherkin
When  an ATA, ITEM_ATA, insumo, NE, NF, fornecedor or usuario is created, changed,
      moved to another status, or a write on it is refused
Then  one HISTORICO_MOVIMENTACAO row exists with entidade_tipo, entidade_id, acao,
      usuario_id, ocorrido_em and dados_anteriores
```
A refused write is `auth.negada` or the entity's `*.bloqueada`. Each spec's audit
table names its rows.

**AC-0007-02** — Same transaction. *Covered:* `test_audit.py`
(`test_a_failed_audit_brings_the_mutation_down`).

**AC-0007-03** and **AC-0007-04** — `UPDATE` and `DELETE` fail at the database
level (RN06). *Covered by SPEC-0001 AC-0001-27:* `test_audit_immutability.py`.

**AC-0007-05** — `dados_anteriores` holds the prior state, never the new one.
Each spec's audit table lists the keys.

**AC-0007-06** — Personal data survives anonymisation without a rewrite (RN16).
*Covered by SPEC-0001 AC-0001-14.*

**AC-0007-07** — The cycle of an insumo (RF06)
```gherkin
Given an insumo on an ATA, with an NE that went through its stages and an NF launched against it
When  any authenticated user reads its cycle
Then  the response lists, in order, the ATA, the ITEM_ATA, the NE with each transition and the NF with its events
```

**AC-0007-08** — Querying the history (RF10)
```gherkin
Given 1 million history rows
When  a gestor or an auditor reads the history filtered by entidade_tipo and entidade_id, by usuario_id, or by a period
Then  the rows come newest first, a page at a time, under 300 ms
```
Served by the indexes on `(entidade_tipo, entidade_id, ocorrido_em)` and
`(usuario_id, ocorrido_em)`.

**AC-0007-09** — A servidor does not read the whole history
```gherkin
When  a servidor reads /api/v1/historico
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
The servidor sees what happened to an insumo through its cycle (AC-0007-07).

**AC-0007-10** — What each event changed
```gherkin
Given an ATA whose vigência_fim was moved by an aditivo de prazo, and later edited
When  a gestor or an auditor reads its history, or anyone reads the cycle of one of its insumos
Then  each event carries a pt-BR label of its acao, the list of fields it changed,
      each with its pt-BR label, its type, the value before and the value after,
      and the context it recorded that is not a field, as labelled details
```
`dados_anteriores` holds only the value before (AC-0007-05). The value after is
not stored either: it is derived by walking the entity's rows from the newest to
the oldest, starting from the entity as it is now, so the newest event's "after"
is the live value and each older event's "after" is the "before" of the next
one. A creation event lists the fields the entity was created with, with no
value before. A removal lists the fields with no value after. An acao that sets a
field without recording its prior value (the NE's números at their stage, the
NF's quarentena and devolução reasons) has `null` before. An aditivo de valor or de
quantidade has as its "after" the "before" plus the acréscimo recorded with it.
A field that did not change, and every key that is not a field (the saldo
available when an NE was refused, the motivo of a cancellation), is a detail, not
a change. An event on an entity SIGI holds no state for (a usuario, a refused
route, an exported report) carries only details.

## 2.1 API, permissions and errors

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| GET | `/api/v1/historico` | Filters `entidade_tipo`, `entidade_id`, `usuario_id`, `de`, `ate`; paginated | 08, 09, 10 |
| GET | `/api/v1/insumos/{id}/ciclo` | The cycle of an insumo | 07, 10 |

Each event in both responses carries, besides the row's own fields:

| Field | Content |
| --- | --- |
| `acao_rotulo` | The acao in pt-BR, or the acao itself when it has no label |
| `alteracoes` | `[{campo, rotulo, tipo, antes, depois}]`; `tipo` is `data`, `dinheiro`, `quantidade`, `texto`, `status`, `referencia` or `itens` |
| `detalhes` | `[{campo, rotulo, valor}]`, the recorded keys that are not a change |

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Read the history | ✅ | ❌ | ✅ |
| Read the cycle of an insumo | ✅ | ✅ | ✅ |

| Condition | HTTP | Error code | Message (pt-BR) |
| --- | --- | --- | --- |
| Wrong role | 403 | `PERFIL_NAO_AUTORIZADO` | "Seu perfil não permite esta ação. Peça a um gestor." |
| Insumo not found | 404 | `NOT_FOUND` | "Insumo não encontrado." |
| Invalid filter or period | 422 | `INVALID_DATA` | Per field, in `fields`. |

## 3. Retention

Five years minimum (RNF08). Partitioning by year from day one; retrofitting
partitions onto a large append-only table is painful and always happens at the
worst moment.

## 4. Implementation plan

No migration: `historico_movimentacao` and its indexes exist since `0001_baseline`.

1. `app/constants/historico.py`: the `entidade_tipo` values a filter admits.
2. `app/repositories/audit_log.py`: a page of the history, newest first, and the
   rows of an insumo's cycle.
3. `app/services/historico.py`: the filters checked (422 per field), the period
   in `America/Sao_Paulo` days, and the cycle resolved through the insumo's
   ITEM_ATA rows, their ATAs, the NEs on those items and the NFs of those NEs.
   The ATA rows keep only its own events and those of the insumo's items. The
   insumo is resolved with the RN07 scope of SPEC-0003, so a servidor outside its
   grupo gets 404.
4. `app/schemas/historico.py`, `app/api/historico.py` for `GET /api/v1/historico`
   (gestor, auditor) and `GET /api/v1/insumos/{id}/ciclo` in `app/api/insumos.py`
   (every perfil).
5. Tests per AC in `tests/test_historico.py`, against PostgreSQL.
6. *(v1.1)* `app/constants/historico.py`: the label and type of each field per
   entidade, the label of each acao and of each detail key, the creation and
   removal acoes and the fields an acao sets with no prior value recorded.
7. *(v1.1)* `app/services/history_changes.py`: the walk, pure, over the rows of
   one entity and its state now; unit-tested without a database.
8. *(v1.1)* `app/repositories/audit_log.py`: every row of a set of entities, and
   batch reads of the ATAs, NEs, NFs, items, insumos, grupos and aditivos they
   name; `app/services/historico.py` joins them so a page costs a fixed number of
   queries, not one per row.

No new dependency.

## 5. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF10, §2.5 RN06, §6.1 A09 |
| 0.2 | 2026-10-27 | By the product owner's review: criteria in Given/When/Then; AC-0007-02 to -04 and -06 point to the SPEC-0001 tests that already prove them; "delete-attempt" becomes a refused write; AC-0007-08 is the history query, AC-0007-09 keeps it from the servidor, and §2.1 adds the API, the permissions and the errors. Depends on SPEC-0004 and SPEC-0005 for the cycle |
| 1.0 | 2026-10-27 | Approved by the product owner after the review of v0.2. No criterion changed; OQ-50 to OQ-54 stand as assumed |
| 1.1 | 2026-11-10 | By the product owner's request ("o historico ainda nao entendi, tipo o aditivo, o que mudou?") and approval of the plan on 2026-11-10: AC-0007-10, each event says what it changed, before and after, with pt-BR labels; §2.1 lists the fields; §4 steps 6 to 8. No migration |
