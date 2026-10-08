# ADR-0005 — NE flow as an explicit transition table

- **Status:** Accepted
- **Date:** 2026-05-22
- **Related:** RF13, RN03, RN08, SPEC-0004

## Context

The NE flow has five stages, a guard between stage two and three, role-dependent
reversal, and a cancellation path. Encoding this as scattered `if
status == ...` checks across service methods is the default outcome and makes
RN08 ("steps may not be skipped") unprovable: you can only test the paths
someone remembered to write.

## Decision

One declarative structure defines every legal transition, its required role, its
guards and its audit action. All movement goes through a single
`transicionar(ne, destino, actor, justificativa)` function. Anything absent from
the table is rejected by default.

Transitions are exposed as sub-resource actions (`/avancar`, `/reverter`,
`/cancelar`) rather than a status `PATCH`, so guards and required justifications
are part of the API contract.

## Consequences

**Positive** — RN08 is provable: the test suite enumerates all 36 (from, to)
pairs and asserts each is accepted or rejected. Adding a stage is a table edit
plus tests, not an audit of every call site. Deny-by-default means a forgotten
case fails closed.

**Negative** — More indirection than inline checks, which will feel like
over-engineering for the first two stages and vindicated by the fifth. The
`cancelada` state is an addition not present in the RFC and needs stakeholder
confirmation (OQ-07).

**Follow-up** — The table in SPEC-0004 §4.1 and the code structure must stay in
lockstep; `/trace` checks that every cell has a corresponding test.
