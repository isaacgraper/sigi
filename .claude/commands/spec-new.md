---
description: Draft a new SIGI specification from the RFC and existing docs
argument-hint: <slug or short description of the capability>
allowed-tools: Read, Write, Edit, Glob, Grep
---

Draft a new specification for: $ARGUMENTS

Steps:

1. Read `docs/product/glossary.md`, `docs/specs/SPEC-TEMPLATE.md`,
   `docs/requirements/functional.md` and `docs/requirements/business-rules.md`.
2. Determine the next free SPEC number from `docs/specs/`.
3. Identify which RF and RN this capability satisfies. If none, say so and stop —
   a capability that satisfies no requirement is scope creep and needs a decision
   before it needs a spec.
4. Delegate the writing to the `spec-author` subagent.
5. Add the traceability rows to `docs/requirements/traceability.md`.
6. Add any new contradictions or gaps to `docs/open-questions.md`.

Report: the spec path, the AC range, the requirements covered, and every
assumption made. Do not write production code.
