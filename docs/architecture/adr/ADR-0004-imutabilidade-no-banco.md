# ADR-0004 — Audit immutability enforced in the database

- **Status:** Accepted
- **Date:** 2026-05-22
- **Related:** RF10, RN06, RNF08, SPEC-0007

## Context

RNF08 requires immutable audit logs retained five years, and prestação de contas
is the system's justification for existing. The RFC describes the table as
"append-only" without saying what enforces that.

## Decision

Immutability is enforced by PostgreSQL, not by application code:

- `REVOKE UPDATE, DELETE ON historico_movimentacao FROM <app_role>`.
- A `BEFORE UPDATE OR DELETE` trigger raising an exception, as defence in depth.
- The application role also lacks `TRUNCATE` and DDL on that table; migrations
  run under a separate role.
- Yearly partitioning from the first migration.

## Consequences

**Positive** — Immutability survives ORM mistakes, careless `psql` sessions and
future developers who have not read this document. It can be demonstrated to an
auditor in one command rather than argued from code review.

**Negative** — Corrections are impossible by design. A row written with wrong
data stays, and the correction is a new compensating row. Schema evolution on
the audit table is constrained; `dados_anteriores` is JSONB partly so the shape
can evolve without altering the table. It also collides with LGPD erasure
rights, resolved by storing personal data pseudonymised in `dados_anteriores`
(AC-0007-06) so that anonymising a user never requires touching audit rows.

**Follow-up** — Tests must run against real PostgreSQL. SQLite has neither the
privilege model nor the triggers, so a test suite on SQLite would pass while
proving nothing.
