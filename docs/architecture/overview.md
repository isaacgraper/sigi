# Architecture Overview

Status: Approved · Source: RFC v1.6 §5

## C4 Level 1 — Context

```
        ┌───────────────────────────────┐
        │ Servidor / Gestor / Auditor   │
        │ (internal, browser, HTTPS)    │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐         ┌──────────────────────┐
        │            SIGI               │────────▶│  SMTP institucional  │
        │  ATA → NE → NF traceability   │  e-mail └──────────────────────┘
        └───────────────────────────────┘
                        ▲
                        │ CSV export (manual, human-initiated)
        ┌───────────────┴───────────────┐
        │   DOMS          e-Publica     │
        │  (no API. no network calls.)  │
        └───────────────────────────────┘
```

The RFC's Level 1 diagram draws arrows to DOMS and e-Publica that suggest live
calls, and its OWASP A10 row describes an SSRF allowlist for outbound requests to
them. RF07/RF08 and §3.2 say the opposite: there is no API integration.
**No network calls are made to DOMS or e-Publica.** Data crosses that boundary as
CSV files a human exports and uploads. The A10 SSRF control is consequently not
applicable to these systems and is removed from the threat model. See ADR-0002.

## C4 Level 2 — Containers

| Container | Technology | Responsibility |
| --- | --- | --- |
| Frontend | Next.js (App Router) | UI, SSR, routing. No business rules. |
| API | Python 3.12 · FastAPI | Domain rules, REST endpoints, authorisation |
| Database | PostgreSQL 16 | Relational persistence + append-only audit |
| Cache | Redis (post-MVP) | Session and hot-read caching. **Not** for saldo. |
| E-mail | SMTP behind a port interface | Async status notifications |
| Runtime | Docker Compose | Portability, on-premise deploy |

Redis is deliberately excluded from the MVP. Caching a derived saldo is the
fastest route to a number that is confidently wrong, and there is no evidence yet
of a read volume that needs it.

## C4 Level 3 — API components

```
  HTTP ──▶ Auth Middleware ──▶ Routers ──▶ Services ──▶ Repositories ──▶ PostgreSQL
           (JWT + RBAC)        (thin)     (domain      (SQLAlchemy,
                                           rules)       no rules)
                                   │
                                   └──▶ Notification port ──▶ SMTP adapter
```

**The layering rule is enforced, not aspirational.** A CI check (`import-linter`)
fails the build if `api` imports `models`, if `repositories` imports `services`,
or if any layer imports `fastapi` below `api`. Architectural boundaries that are
only described in a document erode within weeks.

## Where each business rule lives

| Concern | Layer | Why |
| --- | --- | --- |
| NE transition table | `services/ne_state_machine.py` | A single declarative table, unit-testable without HTTP or DB |
| Saldo computation | `services/saldo.py` + SQL aggregate | Pure function of the NE ledger |
| Saldo guard concurrency | `repositories/ata.py` (`SELECT … FOR UPDATE`) | Correctness needs a row lock, which is a persistence concern |
| Audit row emission | Service layer via a transactional decorator | Must share the mutation's transaction |
| Audit immutability | PostgreSQL privileges + trigger | Must survive application bugs |
| RBAC | FastAPI dependency on every route | Single enforcement point, enumerable by a test |
| Field format validation | Pydantic schemas | Fails fast, before any domain work |

## Deployment

On-premise at the entity, Docker Compose: `frontend`, `api`, `postgres`,
`nginx` (TLS termination). Nightly `pg_dump` plus WAL archiving, with an
annual restore rehearsal (RNF11). The 5-year retention promise in RNF08 is only
as real as the last successful restore test.
