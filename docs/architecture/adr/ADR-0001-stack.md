# ADR-0001 — FastAPI + Next.js + PostgreSQL

- **Status:** Accepted
- **Date:** 2026-05-22
- **Related:** RFC §5.3

## Context

A single developer building a 16-week MVP for on-premise deployment in a state
entity, with an auditability requirement (immutable history, 5-year retention)
and a modest concurrency target (50 users, RNF05).

## Decision

Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic; Next.js App Router
in TypeScript; PostgreSQL 16; Docker Compose on-premise; GitHub Actions.

## Consequences

**Positive** — OpenAPI generated from Pydantic schemas doubles as living API
documentation and as a traceability artifact. PostgreSQL provides table
partitioning, JSONB, row-level locking and privilege revocation, all of which the
audit and saldo requirements depend on directly. On-premise satisfies the
implicit data-residency expectation for state government data.

**Negative** — On-premise means the team owns backups, TLS certificates, uptime
and the 99.5% availability target (RNF02) with no managed platform underneath.
That operational load is invisible in the milestone plan and is the most likely
source of schedule overrun. Two languages for one developer doubles the tooling
surface.

**Follow-up** — RNF11 (backup and rehearsed restore) exists because of the
on-premise choice and must not be dropped from M5.
