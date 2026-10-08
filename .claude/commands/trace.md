---
description: Audit requirement-to-test traceability
argument-hint: [SPEC-XXXX or blank for all]
allowed-tools: Read, Grep, Glob, Bash
---

Audit traceability for $ARGUMENTS (all specs if blank).

Delegate to the `traceability-auditor` subagent, then update
`docs/requirements/traceability.md` with the results.

Report, per spec: AC count, tested, passing; missing tests by ID; failing tests
by ID; unmapped RF/RN; orphan tests that reference no AC.

Verdict must be one of: CLEAN, or BLOCKED with the specific reasons. An
`Approved` spec with an untested AC is BLOCKED. Do not fix anything — report only.
