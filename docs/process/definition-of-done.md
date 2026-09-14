# Definition of Done

A change is done when **all** of the following are true. This list is the merge
gate; `/spec-review` checks it mechanically where it can.

`sop-qualidade.md` says which of these a machine actually enforces and where —
and names the ones nothing enforces, so that this list is read as a checklist
rather than mistaken for a pipeline.

## Specification

- [ ] A spec exists at `docs/specs/SPEC-XXXX-*.md` and its status is `Approved`.
- [ ] Every acceptance criterion touched is listed in the PR description by ID.
- [ ] `docs/requirements/traceability.md` updated (RF/RN → SPEC → test).
- [ ] If a design decision was made, an ADR exists in `docs/architecture/adr/`.

## Code

- [ ] Layering respected: no business rule in a router or repository.
- [ ] No `float` for monetary values.
- [ ] Domain exceptions used; no `HTTPException` raised below the API layer.
- [ ] `ruff check` and `ruff format --check` clean; `mypy` clean.
- [ ] No new dependency without a justification in the spec's plan.

## Data

- [ ] Alembic migration present, reversible, and tested against a seeded database.
- [ ] Any new write path emits a `HISTORICO_MOVIMENTACAO` row in the same transaction.
- [ ] Constraints expressed in the database, not only in Python (`CHECK`, `UNIQUE`, `FK`).

## Tests

- [ ] Each `AC-` has at least one test whose name references it.
- [ ] Invalid-transition and permission-denied paths tested, not only happy paths.
- [ ] Coverage ≥ 70% overall (RNF10); ≥ 90% in `app/services/`.
- [ ] Tests run against real PostgreSQL.

## Security & privacy

- [ ] Authorisation checked server-side for every new endpoint, with a test per role.
- [ ] No personal data (CPF, SIAPE, e-mail) in logs, fixtures or error messages.
- [ ] Anything new touching personal data reflected in `docs/security/lgpd.md`.

## Observability

- [ ] Structured log on every state transition, including actor and reason.
- [ ] p95 latency of new endpoints measured and under 300 ms (RNF01) on seed data.
