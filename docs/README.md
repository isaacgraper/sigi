# SIGI — Documentation

Documentation is the source of truth for system behaviour. Code implements what
these documents describe. When the two disagree, the document is right until it
is deliberately changed.

## Map

| Path | What lives there | Changes when |
| --- | --- | --- |
| `product/vision.md` | Problem, users, personas, scope boundaries, KPIs | Rarely. Requires stakeholder agreement. |
| `product/glossary.md` | Domain vocabulary. Read this first. | A new domain concept appears. |
| `requirements/functional.md` | RF01–RF21, verbatim from RFC v1.6 | The RFC is revised. Notes column: whenever evidence contradicts a requirement. |
| `requirements/non-functional.md` | RNF01–RNF10 with measurable targets | The RFC is revised. |
| `requirements/business-rules.md` | RN01–RN16, expanded into enforceable form — the RFC stated ten, the operation needs sixteen | A rule is clarified or added. |
| `requirements/traceability.md` | RF/RN → SPEC → test mapping | Every spec merge. |
| `specs/SPEC-XXXX-*.md` | Implementable behaviour with acceptance criteria | Before any code changes behaviour. |
| `architecture/overview.md` | C4 context/container/component | Structure changes. |
| `architecture/data-model.md` | Entities, constraints, invariants | Schema changes (with a migration). |
| `architecture/data-sources.md` | Field-level mapping from the entity's real CSV exports to the model | A source export changes, or a new one is offered. |
| `architecture/api-conventions.md` | REST, errors, pagination, auth headers | Rarely. |
| `architecture/adr/` | Decisions and their consequences | A decision is made or reversed. |
| `security/threat-model.md` | OWASP Top 10 controls, trust boundaries | New surface is added. |
| `security/lgpd.md` | Data inventory, legal basis, data-subject rights | Personal data handling changes. |
| `process/sdd-workflow.md` | How a change moves from idea to merged code | The team changes how it works. |
| `process/definition-of-done.md` | Merge checklist | The team raises the bar. |
| `open-questions.md` | What the evidence does not answer: policies, lead times, intentions. A contradiction the **data** answers is a defect in the spec, not an entry here (ADR-0009). | Continuously. |
| `roadmap.md` | M1–M5 milestones and spec sequencing | Planning sessions. |

## Reading order for a new contributor

1. `product/glossary.md` — you will not understand anything else without it.
2. `product/vision.md`
3. `process/sdd-workflow.md`
4. `specs/SPEC-0004-notas-de-empenho.md` — the core of the product.
5. `architecture/data-model.md`

## Document status values

`Draft` → `Review` → `Approved` → `Implemented` → `Superseded`

A spec at `Draft` may not be implemented. A spec at `Approved` may not be
changed without a new version line in its changelog.
