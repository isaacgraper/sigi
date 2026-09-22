# SIGI — Sistema Integrado de Governança de Insumos

> Project constitution. Claude Code loads this file at the start of every session.
> Keep it under ~250 lines. Detail belongs in `docs/`, not here.

## What this system is

SIGI tracks the **administrative supply cycle** of a Brazilian state government
entity end to end: `ATA → NE → NF → conclusão`, and gives the team the
**coverage view** that drives the decision to buy. It is a traceability,
governance and decision-support platform. It is **not** the system of record for
physical stock, and **not** a financial/accounting system.

**Source of truth for scope, in descending authority (ADR-0009):**

1. Operational data the entity supplies — mapped in `docs/architecture/data-sources.md`.
2. Direct stakeholder statements — meeting transcripts, Eduardo's `HUB` annotations.
3. This repository's specs and ADRs.
4. RFC v1.6 — historical context, and the artifact submitted to the evaluation
   panel. No longer the arbiter of scope.

A conflict between the data and a spec is a **defect in the spec**: fix it, cite
the evidence in the changelog. Do not file it as an open question.

## Current state of the repository

*(Rewritten 2026-09-22, after SPEC-0001 finished. The previous text said "the
behaviour does not exist" and called `app/services/` empty weeks after ten
modules landed there, and pinned the spec at v0.5 when it was at v1.2. This
section ages faster than any other: check a sentence here before acting on it.)*

**SPEC-0001 is implemented.** `backend/` serves local login with refresh
rotation and logout, per-address lockout, institutional OIDC, member invitations
and activation, member management with anonymised deactivation,
gestor-triggered password reset, a permission matrix checked when the app is
assembled, and per-source rate limiting. The audit trail is written in the
caller's transaction and is append-only at the database level. 157 tests run
against a real PostgreSQL 16.

`frontend/` is still a Next.js skeleton. Nothing consumes the API yet.

**Two database roles are not optional.** The application connects as a
restricted role; migrations run as the owner. ADR-0004's append-only guarantee
is void with a single role, because an owner can `ALTER TABLE ... DISABLE
TRIGGER`. `infra/postgres/init/01-roles.sh` provisions the app role and the
migration refuses to run without it.

**One migration.** `0001_baseline` creates `usuario`, `token_credencial`,
`tentativa_login`, `limite_taxa`, `sessao_familia`, `sessao` and
`historico_movimentacao` with seven yearly partitions to 2032. `alembic check`
is asserted by a test, so a model that drifts from the schema fails the suite
instead of producing a migration that drops tables. Nothing since the baseline
has needed a second one.

**Specs:** `SPEC-0001` is at **v1.2**, `Approved`. Everything else is `Draft`,
and **a spec at `Draft` may not be implemented** — audited: no test references
an AC from SPEC-0002 to SPEC-0009.

**What is left:**

- **AC-0001-30**, self-service reset — blocked by design, not missed. No mail
  transport, so no channel to the requester; returning the token in the response
  would let anyone reset anyone's password.
- **OQ-17** — the live prototype JWT in RFC Appendix 9.1 is still unrevoked.
  Blocks nothing mechanically and everything ethically.
- **OQ-28** — superseded `rfc-sigi-v1.7.md` still defines a second `RF05` and
  `RN11`, so no test may be named after either.
- **OQ-31** — AC-0001-32 no longer guarantees a gestor cannot take over an
  account; with no mail transport they receive the reset link. Detectable
  through the audit row and the session revocation, not impossible.
- **OQ-32** — the throttle ignores `X-Forwarded-For`, so behind a reverse proxy
  every request shares one ceiling. Needs the deployment topology.
- Traceability gaps nobody has closed: `RN07` is meant to land in SPEC-0003 but
  its `satisfies` does not claim it, `RF15` is implemented in SPEC-0002's body
  but absent from its `satisfies` and from `traceability.md`, and `RF16` maps to
  no spec.

## Non-negotiable domain rules

These are invariants. If a task appears to require breaking one, **stop and ask**.

1. **Never translate domain vocabulary.** `ATA`, `Nota de Empenho` (NE),
   `Nota Fiscal` (NF), `empenho`, `saldo`, `insumo`, `fornecedor`, `vigência`,
   `aditivo`, `reajuste`, `Processo SEI` stay in Portuguese in code, database,
   API paths and UI. See `docs/product/glossary.md`.
2. **An NF binds to an NE, never directly to an ATA.** The ATA link is inherited
   through the NE. (RN02)
3. **The NE flow is sequential and complete.** `demanda → validacao_saldo →
   pre_empenho → envio_fornecedor → ne_emitida`. No step may be skipped. (RN08)
4. **Reversal requires a justification and the `gestor` role.** It is recorded,
   never silent. (RN03)
5. **`saldo` is derived, never stored as a mutable column.** It is computed from
   the NE ledger — `valor_contratado − valor_reservado − valor_empenhado` —
   aggregated over `ITEM_NOTA_EMPENHO` (ADR-0003, ADR-0007). There is no
   writable saldo anywhere.
   **`estoque` is imported, never computed.** SIGI may hold a dated stock
   snapshot from DOMS (`estoque_atual`, `dias_estoque`, `curva_abc`,
   `estoque_minimo`, `ponto_pedido`) because the entity's loop is
   coverage-driven and DOMS already computes those figures. The importer is the
   only writer: no endpoint, service or UI mutates a snapshot, and there is no
   `entrada de estoque` operation. Every surface shows the snapshot's
   `data_referencia`. (ADR-0008)
   **`saldo` and `estoque` are different things.** Never summed, never shown as
   one number, never used as synonyms.
6. **The audit trail is append-only.** `HISTORICO_MOVIMENTACAO` rows are never
   updated or deleted, at the database level, not just in application code. (RN06, RNF08)
7. **There is no live API integration with DOMS or e-Publica.** Consistency is
   achieved through format validation and CSV import. Do not write HTTP clients
   for these systems. See `docs/architecture/adr/ADR-0002-*.md`.
   *(2026-09-10)* This is about **data sources**, not identity. Talking OIDC to
   the entity's identity provider is in scope (ADR-0010): it asserts who the
   caller is and supplies no ATA, insumo, NE or NF. Do not read that as a
   reversal of this rule, and do not read this rule as forbidding it.
8. **Authorisation is enforced server-side on every endpoint.** Frontend role
   checks are cosmetic only. (A01)

## Stack

| Layer     | Choice                                          |
| --------- | ----------------------------------------------- |
| Backend   | Python 3.12, FastAPI, Pydantic v2               |
| ORM       | SQLAlchemy 2.x + Alembic                        |
| Database  | PostgreSQL 16                                   |
| Frontend  | Next.js (App Router), React, TypeScript         |
| Auth      | JWT RS256 (15 min) + refresh token (httpOnly, 7d) |
| Runtime   | Docker + docker compose, on-premise deploy      |
| CI        | GitHub Actions                                  |
| Tests     | pytest + httpx (backend), Vitest + Playwright (frontend) |

## Repository layout

```
docs/            Specs, ADRs, requirements. The source of truth for behaviour.
.claude/         Agents, commands and skills for this project.
backend/
  app/
    api/         FastAPI routers. Thin. HTTP concerns only.
    services/    Business logic and domain rules. Where RN* rules live.
    repositories/ SQLAlchemy data access. No business logic.
    models/      SQLAlchemy ORM models.
    schemas/     Pydantic request/response models.
    core/        Config, security, dependencies.
  migrations/    Alembic.
  tests/
frontend/
  app/           Next.js App Router routes.
  components/
  lib/
```

## Commands

Backend dependencies are managed with **Poetry**, and the commands below run
from `backend/`. This table matches the allow-list in `.claude/settings.json`;
change one and change the other.

| Task | Command |
| --- | --- |
| Run everything | `docker compose up --build` |
| Install / re-sync deps | `poetry sync --all-groups` |
| Apply migrations | `docker compose exec backend alembic upgrade head` |
| New migration | `docker compose exec backend alembic revision --autogenerate -m "..."` |
| Backend tests | `poetry run pytest` |
| A single test | `poetry run pytest tests/path/to/test_file.py::test_name` |
| Tests for one AC | `poetry run pytest -k AC_0004_07` |
| Coverage gate (RNF10) | `poetry run pytest --cov=app --cov-fail-under=70` |
| Lint / format | `poetry run ruff check .` · `poetry run ruff format .` |
| Every gate at once | `poetry run pre-commit run --all-files` |
| Frontend dev | `npm run dev` |
| Frontend tests | `npm run test` (Vitest) · `npm run test:e2e` (Playwright) |

From the repository root, `poetry -C backend run …` changes into `backend/`
first, while `poetry -P backend run …` finds the project without changing
directory — which is what the pre-commit hooks use, so that the paths pre-commit
appends still resolve.

**The gates run before the commit, not only in CI.** `pre-commit` enforces ruff,
ruff format, mypy, the commit-message convention and the ban on committing
personal data; `pytest` runs at push. `docs/process/sop-qualidade.md` says which
rule is checked where, and names the two that nothing checks.

Backend tests need a real PostgreSQL (testcontainers), not SQLite — see
"Testing expectations". `psql`, `alembic downgrade` and `docker compose down -v`
are denied in `.claude/settings.json` by design, and so is pushing to `dev`,
`main` or with `--force`. Pushing the current branch to itself
(`git push -u origin HEAD`) is permitted; opening the PR is what moves work
towards `dev`.

## Spec-driven workflow (short version)

Full version: `docs/process/sdd-workflow.md`.

```
EVIDENCE → SPEC → PLAN → IMPLEMENT → VERIFY
```

`EVIDENCE` is operational data › stakeholder statements › repo docs › RFC v1.6,
per ADR-0009. The loop no longer starts from a frozen document.

**No production code is written without a spec that has a stable ID.**

- Every spec lives in `docs/specs/SPEC-XXXX-*.md` and carries acceptance
  criteria written as Given/When/Then.
- Every acceptance criterion has an ID: `AC-XXXX-NN`.
- Every test references the AC it verifies in its docstring or test name.
- Every commit message references the spec: `feat(ne): ... [SPEC-0004]`.
- Changing behaviour means changing the spec **first**, then the code.

Useful commands: `/spec-new`, `/spec-review`, `/plan`, `/implement`, `/trace`, `/adr-new`.

## Code conventions

**Backend**

- Layering is strict: `api → services → repositories → models`. A router must
  never import a model or open a session directly. A repository must never
  contain an `if` that encodes a business rule.
- Domain rules raise typed domain exceptions (`SaldoInsuficienteError`,
  `TransicaoInvalidaError`); the API layer maps them to HTTP responses. Do not
  raise `HTTPException` from a service.
- All money is `Decimal`, never `float`. Database type `NUMERIC(15,2)`.
- All primary keys are UUIDv4. Never expose sequential IDs.
- Timestamps are `TIMESTAMPTZ`, stored UTC, presented in `America/Sao_Paulo`.
- Every write endpoint records a `HISTORICO_MOVIMENTACAO` row in the same
  transaction as the write. If the history write fails, the write fails.

**Frontend**

- Server Components by default; `"use client"` only when interactivity requires it.
- No business rule is re-implemented in the frontend. Ask the API.
- Currency formatted `pt-BR` / `BRL`; dates `dd/MM/yyyy`.

**Both**

- Comments explain *why*, never *what*.
- No new dependency without a note in the spec's plan section.
- **Language is chosen by who reads the string** (ADR-0013). Ask that first;
  it answers every case, including the ones a vocabulary list cannot reach.

  | Layer | Language | Reader |
  | --- | --- | --- |
  | Database schema: tables, columns, constraints, indexes, DDL, `acao` values, `dados_anteriores` keys | Portuguese | A DBA or a data analyst, querying directly |
  | UI copy, `message`, `fields` values, tooltips | pt-BR | The servidor using the platform |
  | Everything else: folders, filenames, Python, comments, docstrings, logs, JSON payload fields, error codes, route paths, config keys, branch names, commit messages, PR titles and bodies | English | A developer |

- **Glossary vocabulary stays Portuguese in every layer** (invariant 1, which
  ADR-0013 does not narrow): `def calcular_saldo(ata)`, not
  `def calculate_balance(minutes)`. The tie-break for a compound is all or
  nothing: a name built around a glossary noun keeps the whole Portuguese
  expression, a name without one becomes English, and neither is ever
  translated word by word. `SALDO_INSUFICIENTE` stays; `CREDENCIAIS_INVALIDAS`
  becomes `INVALID_CREDENTIALS`; `SALDO_INSUFFICIENT` is wrong.
- A payload field and the column behind it need not share a name, because they
  have different readers. `password` over `senha_hash` is correct.
- A reviewer should not have to switch language between the diff and the message
  that explains it: `add/authentication-spec-0001`, `feat: block advance on
  insufficient saldo [SPEC-0004]`.

## Testing expectations

- Minimum 70% coverage (RNF10), but coverage is a floor, not a goal.
- Every business rule in `docs/requirements/business-rules.md` — `RN01`–`RN16`,
  not only the ten the RFC stated — has at least one test named after it.
- Every state-machine transition, valid and invalid, has a test (SPEC-0004).
- Tests hit a real PostgreSQL via testcontainers, not SQLite. The audit
  triggers and `NUMERIC` semantics do not exist in SQLite.

## Things Claude should not do in this repo

- Do not invent requirements. Ground every one in the operational data or a
  stakeholder statement, and cite it. If neither shows it, add an entry to
  `docs/open-questions.md` and ask.
- Do not "fix" an inconsistency between two specs silently. Flag it. A
  contradiction against the **data**, however, is fixed in the spec with a
  changelog line citing file, sheet and column (ADR-0009).
- The RFC's silence is not a prohibition, and its text is not an argument. What
  the entity demonstrably does is in scope, subject to milestone prioritisation.
- Still out of scope regardless of the data: ML forecasting, mobile apps, a
  public transparency portal, a financial/accounting module, payment execution,
  and live API integrations (ADR-0002 — CSV import only).
- Do not make SIGI the system of record for physical stock. Importing a dated
  snapshot is allowed; computing, adjusting or recounting stock is not.
- Do not commit real CPF, SIAPE numbers, e-mails or tokens. The RFC appendix
  contains a live prototype JWT: it must not be copied into this repository.
- Do not run destructive commands (`drop`, `truncate`, `rm -rf`) without asking.
