# ADR-0002 — No API integration with DOMS or e-Publica

- **Status:** Accepted
- **Date:** 2026-05-22
- **Related:** RF07, RF08, SPEC-0002, SPEC-0003, RFC §3.2

## Context

The RFC is internally inconsistent on this point, and the inconsistency is worth
naming because it changes the architecture:

- §5.1 draws DOMS and e-Publica as external systems SIGI "validates" and
  "imports" from, and §6.1 A10 specifies an SSRF allowlist for outbound calls.
- RF07, RF08 and §3.2 state plainly that there is no automatic API integration.
- The mockups (9.2.2.1, 9.2.2.2) show **file upload dialogs**, not lookups.

Neither system offers a documented API available to this project, and obtaining
one would require institutional agreements outside the team's control and
outside the 16-week window.

## Decision

SIGI makes **no network calls** to DOMS or e-Publica. Interoperability is
achieved by two mechanisms only:

1. **Format validation** of shared keys — `codigo` against the DOMS pattern,
   `processo_sei` against the SEI pattern — with in-app guidance on filling them.
2. **CSV import** of files a human exports from those systems.

## Consequences

**Positive** — No coupling to systems the team cannot test, version or monitor.
No credential management for third-party platforms. No SSRF surface, so OWASP
A10 is not applicable and is removed from the threat model rather than mitigated
theatrically. The 16-week plan becomes achievable.

**Negative** — Consistency is only as good as the human doing the export. Data
can drift between the systems between imports, and SIGI cannot detect it. The
"retrabalho de registrar a mesma informação em diferentes sistemas" the
stakeholders complained about is reduced but not eliminated: SIGI removes
duplicate *typing*, not duplicate *systems*. This should be stated honestly to
stakeholders rather than described as "integração".

**Follow-up** — Every import produces a per-row report; imports are atomic and
idempotent (AC-0002-07, AC-0003-07/08). Language matters: the term "integração"
is banned in UI copy and documentation in favour of "consistência operacional"
and "importação". A periodic manual reconciliation is a process obligation of
the entity, and must be written into the user manual, not assumed.
