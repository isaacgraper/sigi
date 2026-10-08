# Threat Model

Source: RFC v1.6 §6.1, revised where the RFC's controls do not match the actual
architecture.

## Trust boundaries

1. **Browser → API** — hostile. Everything is validated server-side. Frontend
   role checks are UX, never enforcement.
2. **API → PostgreSQL** — trusted network, restricted role. The application role
   cannot `UPDATE`/`DELETE` audit rows or run DDL.
3. **Human → CSV import** — semi-trusted. Files are user-supplied input from
   outside the system and are parsed defensively.
4. **API → SMTP** — outbound only, no user-controlled destinations.

There is **no** SIGI → DOMS/e-Publica boundary. See ADR-0002.

## OWASP Top 10 (2021)

| # | Risk | Control | Verified by |
| --- | --- | --- | --- |
| A01 | Broken Access Control | RBAC dependency on every route; 403 audited; generated test enumerating the route table against the permission matrix | AC-0001-15..18 |
| A02 | Cryptographic Failures | TLS 1.2+, HSTS; bcrypt cost 12; JWT RS256; refresh token httpOnly/Secure | AC-0001-01, 05, 09 |
| A03 | Injection | SQLAlchemy parameterised queries; no string-built SQL; Pydantic validation before persistence; CSV cells never evaluated | Static check + tests |
| A04 | Insecure Design | Sequential NE machine with deny-by-default transitions; saldo guard under row lock; append-only audit | AC-0004-05, 12, 13 |
| A05 | Security Misconfiguration | `python:3.12-slim`; secrets via env/secret manager; CORS allowlist; security headers middleware; debug off outside dev | Deploy checklist |
| A06 | Vulnerable Components | Dependabot; `pip-audit` and `npm audit` fail the CI build on high severity | CI |
| A07 | Auth & Session Failures | 15-min access token; server-side refresh invalidation; login rate limit; active-status check on every request | AC-0001-03, 06, 07, 08 |
| A08 | Software & Data Integrity | Signed CI artifacts; atomic, validated, idempotent CSV import | AC-0002-07, AC-0003-07/08 |
| A09 | Logging & Monitoring Failures | Append-only history; structured logs with correlation ID; alerts on repeated 403 and on `SALDO_INSUFICIENTE` clusters | AC-0007-01..04 |
| A10 | SSRF | **Not applicable.** SIGI makes no outbound HTTP requests to user-influenced destinations. The RFC's allowlist control presupposes an integration that does not exist. | ADR-0002 |

## Risks the RFC does not cover

| Risk | Why it matters here | Mitigation |
| --- | --- | --- |
| **CSV injection on export** | A cell beginning `=`, `+`, `-` or `@` executes as a formula when an auditor opens the export in Excel. Reports are exported constantly by design. | Prefix such cells with `'` on export; test with a malicious insumo description. |
| **CSV import bombs** | Import is the main ingestion path. A 500 MB file or a zip-bomb-style row count exhausts memory. | Size cap, row cap, streaming parser, timeout. |
| **PDF generation SSRF/RCE** | Report engines that render HTML can fetch remote resources. | Disable remote fetching in the PDF renderer; render from data, never from user-supplied HTML. |
| **Insider misuse by a gestor** | A gestor can advance, reverse and cancel. The threat is a legitimate user acting improperly — precisely what prestação de contas exists to detect. | Justification mandatory on every reversal/cancellation; alerting on unusual reversal frequency per user. |
| **Leaked prototype credentials** | The RFC appendix embeds a live Lovable JWT in a public document. | Revoke that token; add a secret scanner (`gitleaks`) to CI; never copy the appendix URL into the repository. |
| **Audit-log denial by exhaustion** | If the audit insert can fail, an attacker forcing failures could suppress records. | Audit insert shares the mutation transaction, so suppression means the mutation also fails (AC-0007-02). |

## Immediate actions

1. Revoke the prototype token published in RFC Appendix 9.1.
2. Add `gitleaks` to CI before the first commit of real configuration.
3. Decide the Gov.br OAuth path early — it has an institutional lead time that
   no amount of engineering compresses (OQ-09).
