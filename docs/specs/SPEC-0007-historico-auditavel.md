---
id: SPEC-0007
title: Histórico auditável imutável
status: Draft
version: 0.2
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
the history (AC-0007-08, -09) and the cycle of an insumo (AC-0007-07).

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

## 2.1 API, permissions and errors

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| GET | `/api/v1/historico` | Filters `entidade_tipo`, `entidade_id`, `usuario_id`, `de`, `ate`; paginated | 08, 09 |
| GET | `/api/v1/insumos/{id}/ciclo` | The cycle of an insumo | 07 |

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

## 4. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF10, §2.5 RN06, §6.1 A09 |
| 0.2 | 2026-10-27 | By the product owner's review: criteria in Given/When/Then; AC-0007-02 to -04 and -06 point to the SPEC-0001 tests that already prove them; "delete-attempt" becomes a refused write; AC-0007-08 is the history query, AC-0007-09 keeps it from the servidor, and §2.1 adds the API, the permissions and the errors. Depends on SPEC-0004 and SPEC-0005 for the cycle |
