---
description: Review a spec for completeness before approving it
argument-hint: SPEC-XXXX
allowed-tools: Read, Grep, Glob
---

Review $ARGUMENTS for readiness to move from Draft to Approved.

Check and report on each:

1. **Frontmatter** — id, status, version, owner, satisfies, depends_on, milestone.
2. **Criteria quality** — every AC has an ID, is Given/When/Then, is atomic, and
   is observable from outside the system. List any that are vague.
3. **Negative coverage** — for every happy path, is there a matching failure,
   permission-denial and validation criterion? Name the gaps.
4. **Rule consistency** — does any AC contradict an RN in
   `docs/requirements/business-rules.md`?
5. **Dependencies** — are all `depends_on` specs at Approved or later?
6. **Audit** — does every mutation name the `HISTORICO_MOVIMENTACAO` row it writes?
7. **Permissions** — is the matrix complete for all three profiles?
8. **Errors** — does every error have a code and a pt-BR message that tells the
   user what to do next?
9. **Open questions** — are any of them blocking for the criteria listed?

Verdict: APPROVE, or a numbered list of what must change. Be specific; "add more
detail" is not actionable feedback.
