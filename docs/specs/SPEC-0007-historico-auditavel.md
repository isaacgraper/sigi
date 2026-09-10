---
id: SPEC-0007
title: Histórico auditável imutável
status: Draft
version: 0.1
owner: Isaac Kleimann Graper
satisfies: [RF06, RF10, RN06, RNF08]
depends_on: [SPEC-0001]
milestone: M2
---

# SPEC-0007 — Histórico auditável imutável

## 1. Purpose

Prestação de contas is the reason this system exists. The audit trail is
therefore not a feature but a constraint on every other feature: any write path
that does not produce a history row is a defect, regardless of what it does correctly.

## 2. Behaviour

**AC-0007-01** — Every create, update, transition and delete-attempt on ATA,
ITEM_ATA, Insumo, NE, NF, Fornecedor and Usuario writes one
`HISTORICO_MOVIMENTACAO` row containing `entidade_tipo`, `entidade_id`, `acao`,
`usuario_id`, `ocorrido_em` and `dados_anteriores` (JSONB). *(The column was
called `timestamp` until 2026-09-10; renamed because `TIMESTAMP` is a type name
and the table is partitioned by that column — see `data-model.md`.)*

**AC-0007-02** — The history row is written in the **same transaction** as the
mutation. If the history insert fails, the mutation rolls back. A test injects a
history failure and asserts the entity is unchanged.

**AC-0007-03** — `UPDATE` on `historico_movimentacao` raises a database-level
exception, not an application error. A test issues raw SQL as the application
role and asserts failure (RN06).

**AC-0007-04** — `DELETE` on `historico_movimentacao` likewise fails at the
database level.

Implementation: `REVOKE UPDATE, DELETE ON historico_movimentacao FROM app_user`
plus a `BEFORE UPDATE OR DELETE` trigger raising an exception. Application-level
immutability enforced only in Python is one careless ORM call away from being
untrue, and an audit trail whose immutability depends on developer discipline is
not evidence.

**AC-0007-05** — `dados_anteriores` stores the prior state, never the new one.
The current state is in the entity; the history's job is to say what was lost.

**AC-0007-06** — Personal data in `dados_anteriores` is stored pseudonymised, so
that a data-subject anonymisation request (RN16) does not require mutating an
immutable table. This tension between LGPD erasure and audit immutability is
resolved once, here, rather than discovered during M4.

**AC-0007-07** — The cycle view for an insumo returns the ordered chain
`ATA → ITEM_ATA → NE (with all transitions) → NF (with conference events)`,
visible to any authenticated user (RF06).

**AC-0007-08** — History is queryable by `entidade_tipo` + `entidade_id`, by
`usuario_id`, and by time range, each under 300 ms on 1 million rows, with a
composite index on `(entidade_tipo, entidade_id, ocorrido_em DESC)`.

## 3. Retention

Five years minimum (RNF08). Partitioning by year from day one; retrofitting
partitions onto a large append-only table is painful and always happens at the
worst moment.

## 4. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF10, §2.5 RN06, §6.1 A09 |
