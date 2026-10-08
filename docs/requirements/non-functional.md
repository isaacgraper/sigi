# Non-Functional Requirements

Each entry states how it is verified. An NFR with no verification method is an
aspiration, not a requirement.

| ID | Requirement | Verification | Gate |
| --- | --- | --- | --- |
| RNF01 | API response < 300 ms at p95, **except the two routes that verify a credential** (ADR-0011), which have a provisional budget of 500 ms | k6 load script against seeded DB (10k NEs, 500 ATAs); APM in production; the auth script reports login's p95 separately | CI performance job on the 10 hottest endpoints |
| RNF02 | 99.5% monthly availability, excluding planned maintenance | Uptime monitoring; monthly report | Post-deploy |
| RNF03 | JWT/OAuth2, 15-minute access token, secure refresh token | Test asserting `exp`; test that an expired token yields 401 | CI |
| RNF04 | All traffic over HTTPS/TLS 1.2+ | Deployment config review; HSTS header test | Deploy checklist |
| RNF05 | ≥ 50 concurrent users in MVP | k6 with 50 VUs, error rate < 1% | Pre-M5 |
| RNF06 | Responsive UI on Chrome, Firefox, Edge | Playwright at 360/768/1440 px on the three engines | CI |
| RNF07 | LGPD compliance for servidor personal data | `security/lgpd.md` review each milestone | M4 |
| RNF08 | Audit logs immutable, retained ≥ 5 years | Test asserting UPDATE/DELETE on the audit table fails at DB level; documented backup retention | CI + deploy checklist |
| RNF09 | Containerised via Docker | `docker compose up` from a clean clone reaches a healthy `/health` | CI |
| RNF10 | ≥ 70% automated test coverage | `pytest --cov`, CI fails below threshold | CI |

## Additions the RFC omits

| ID | Requirement | Rationale |
| --- | --- | --- |
| RNF11 | Backup: nightly full + WAL archiving; restore rehearsed at least once before M5 | A 5-year immutable retention claim (RNF08) is meaningless without a proven restore path. |
| RNF12 | Structured JSON logs with correlation ID per request; no personal data in log bodies | Required to investigate an audit discrepancy without violating RNF07. |
| RNF13 | All timestamps stored `TIMESTAMPTZ` in UTC, presented in `America/Sao_Paulo` | Audit ordering across DST is otherwise ambiguous. |
| RNF14 | Accessibility: WCAG 2.1 AA on the primary flows | Public-sector systems in Brazil are subject to accessibility expectations (eMAG/LBI); retrofitting is expensive. |
| RNF15 | Monetary values `NUMERIC(15,2)`, never floating point, rounding `ROUND_HALF_UP` | Saldo is derived by summation; float drift becomes an audit finding. |
| RNF16 | Every unauthenticated or credential-bearing route is rate-limited per source and per route, with configurable ceilings and a higher ceiling for institutional ranges | Test per route asserting 429 with `Retry-After` at the configured limit; k6 asserting a trusted range is not locked out under normal load | *(2026-09-10, ADR-0012)* Attacks against authentication paths are routine, and one of them — the OIDC callback — makes SIGI call the entity's own identity provider once per request. |
