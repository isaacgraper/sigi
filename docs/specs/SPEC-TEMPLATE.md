---
id: SPEC-XXXX
title: <capability in Portuguese domain terms>
status: Draft            # Draft | Review | Approved | Implemented | Superseded
version: 0.1
owner: <name>
satisfies: [RFxx, RNxx]
depends_on: [SPEC-XXXX]
milestone: Mx
---

# SPEC-XXXX — <title>

## 1. Purpose

Two or three sentences. What capability this adds and which user problem from
`product/vision.md` it addresses. If you cannot connect it to a persona's
problem, question whether it belongs in the MVP.

## 2. Scope

**In scope**
- …

**Out of scope**
- … (say where it went instead: another spec, or the post-MVP backlog)

## 3. Domain model touched

Entities created or modified, and the invariants this spec is responsible for
upholding. Reference `architecture/data-model.md`; do not restate the schema.

## 4. Behaviour

### 4.1 <Flow name>

Prose description, then the criteria.

**AC-XXXX-01** — <short name>
```gherkin
Given <precondition, stated in domain terms>
When  <a single actor performs a single action>
Then  <an externally observable outcome>
And   <a second observable outcome, e.g. an audit row or an e-mail>
```

Every criterion must be:
- **observable** — assertable from an API response, a database row, an e-mail, or the DOM;
- **atomic** — one Given/When/Then per criterion; if you need "and also", write another;
- **negative where it matters** — permission denials, invalid transitions and
  validation failures each get their own criterion. Happy-path-only specs
  produce happy-path-only tests.

## 5. Errors and edge cases

| Condition | HTTP | Error code | Message (pt-BR, user-facing) |
| --- | --- | --- | --- |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |

## 7. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |

Full conventions in `architecture/api-conventions.md`.

## 8. Audit events

Every mutation must name the `HISTORICO_MOVIMENTACAO` row it produces.

| Action | `entidade_tipo` | `acao` | Captured in `dados_anteriores` |
| --- | --- | --- | --- |

## 9. Open questions

Link to `open-questions.md` entries. A spec may be `Approved` with open
questions only if none of them block the criteria listed above.

## 10. Implementation plan

_Filled by `/plan`. Empty until the spec is Approved._

- Migration:
- Modules:
- Tests:

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | YYYY-MM-DD | Initial draft from RFC v1.6 |
