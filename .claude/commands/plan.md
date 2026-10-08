---
description: Produce an implementation plan for an approved spec
argument-hint: SPEC-XXXX
allowed-tools: Read, Grep, Glob, Edit
---

Produce the implementation plan for $ARGUMENTS and append it to that spec under
`## Implementation plan`.

1. Read the spec, `docs/architecture/data-model.md`,
   `docs/architecture/api-conventions.md` and `CLAUDE.md`.
2. If the spec is not `Approved`, stop and say so.
3. Use the `domain-modeler` subagent for anything touching persistence.
4. Produce:
   - **Migration** — DDL, Alembic upgrade and downgrade, what the downgrade loses.
   - **Modules** — files created or modified, by layer.
   - **Endpoints** — method, path, request/response schema, ACs covered.
   - **Tests** — the test file and function name for every AC, so an unmapped AC
     is visible now rather than at merge.
   - **Sequence** — the commit-by-commit order.
   - **Risks** — what could invalidate this plan, and the cheapest way to find out early.
   - **New dependencies** — each with a justification. None by default.

Do not write code. Stop after the plan and wait for review — this is the cheapest
place to catch a wrong design.
