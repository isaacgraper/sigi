---
description: Implement an approved spec that already has a plan
argument-hint: SPEC-XXXX [AC-XXXX-NN ...]
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Implement $ARGUMENTS.

Preconditions — verify all three and stop if any fails:
- the spec status is `Approved`;
- it has an `## Implementation plan` section;
- its `depends_on` specs are `Implemented`.

If specific AC IDs were given, implement only those. Otherwise implement the
whole spec.

Order, committing at each step:

1. Migration and model (`domain-modeler` for review if the schema changes).
2. Failing tests from the AC list (`test-author`).
3. Service layer until the tests pass (`backend-implementer`).
4. API layer.
5. Frontend, if the spec includes screens (`frontend-implementer`).

Then run `ruff check`, `mypy`, `pytest --cov`, and `/trace SPEC-XXXX`.

If the spec turns out to be wrong or incomplete — which happens — **stop
coding**, amend the spec, bump its version, add a changelog line explaining what
you learned, then resume. Never leave code and spec disagreeing.

Report: commits made, ACs passing, ACs remaining, spec amendments made.
