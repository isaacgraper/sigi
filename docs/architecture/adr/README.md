# Architecture Decision Records

One decision per file, numbered sequentially, never deleted. A reversed decision
gets a new ADR that supersedes the old one; the old file stays, with its status
changed to `Superseded by ADR-XXXX`. The value of an ADR is mostly in the
"Consequences" section read two years later by someone asking "why on earth is
it like this?".

Create one with `/adr-new <title>`.

| ADR | Title | Status |
| --- | --- | --- |
| 0001 | FastAPI + Next.js + PostgreSQL stack | Accepted |
| 0002 | No API integration with DOMS or e-Publica | Accepted |
| 0003 | Saldo is derived, never stored | Accepted |
| 0004 | Audit immutability enforced in the database | Accepted |
| 0005 | NE state machine as an explicit transition table | Accepted |
| 0006 | Language split: English code/API envelope, Portuguese domain, pt-BR user text | Accepted |
| 0007 | The Nota de Empenho carries multiple insumos | Accepted |
| 0008 | Ingesting stock signals from DOMS without becoming an inventory system | Accepted |
| 0009 | Operational data supersedes the RFC as the source of truth | Accepted |
