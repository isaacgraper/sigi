# ADR-0011 — Credential verification sits outside RNF01's latency budget

- **Status:** Accepted
- **Date:** 2026-09-10
- **Deciders:** Isaac Kleimann Graper (product owner), 2026-09-10
- **Related:** RNF01, RNF05, AC-0001-05, SPEC-0001, ADR-0010

## Context

`RNF01` requires "API response < 300 ms at p95". `AC-0001-05` requires the
stored credential to be a bcrypt hash at cost 12. A cost-12 verification costs
roughly 250–400 ms on ordinary server hardware — **by design**. The cost *is* the
mitigation: it is what makes an offline attack against a leaked hash table
expensive. So `POST /api/v1/auth/login` cannot satisfy both requirements, and no
amount of tuning changes that.

This surfaced while writing SPEC-0001's implementation plan, before any code
existed — which is the cheapest moment for a requirement conflict to appear.

**Where RNF01's number came from.** The product owner states plainly that the
300 ms figure was never derived from a benchmark, a measurement, or a stated user
expectation. It came into the RFC as a round number. That does not make it
worthless — a latency budget is worth having — but it does mean it carries no
evidence that would outweigh a security parameter that does.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Lower the bcrypt cost until login fits 300 ms | RNF01 stays universal | Weakens the one control protecting credentials at rest, to satisfy a number nobody measured. This is the option that looks like tuning and is actually a security downgrade |
| Drop RNF01 | Honest about its provenance | Throws away a useful budget for the 40-odd endpoints where 300 ms is both achievable and meaningful |
| **Carve out credential verification** (chosen) | Keeps the budget where it applies; keeps the security parameter where it matters; makes the exception explicit and testable | Two budgets to track, and an exception that could quietly widen if nobody guards its scope |

## Decision

1. **RNF01 does not apply to routes that verify a credential.** Concretely:
   `POST /api/v1/auth/login` and `POST /api/v1/convites/{token}/ativar` — the two
   routes that run bcrypt. Every other route, including `refresh`, `logout`,
   `/me` and the whole OIDC flow, stays inside RNF01.
2. **Those routes get their own budget: p95 under 500 ms**, recorded as
   **provisional**. The number is deliberately loose, and the product owner's
   instruction is explicit: leave it open and settle it by stressing the
   authentication API rather than by asserting a figure.
3. **The bcrypt cost stays 12.** It is not a tuning knob for this problem.
4. **The exception is enumerated, never a category.** A new route joins it only
   by amending this ADR. "Auth is slow" must not become a licence.

## Consequences

**Positive** — The conflict is on the record instead of being resolved by
whoever writes the code first, which in practice would have meant a quietly
lowered bcrypt cost. The 500 ms figure is honest about being provisional, and
`RNF05`'s k6 harness already exists to settle it with a measurement.

**Negative** — Two latency budgets is more to hold in your head than one, and an
exception list is a thing that grows if nobody watches it. Worse, "provisional"
is how a number lives forever: nobody is ever forced to replace it.

So this ADR names the deadline rather than trusting good intentions: **the
provisional 500 ms must be replaced by a measured figure before the M5 load-test
phase closes.** If the measurement shows login sitting comfortably under 300 ms
on the entity's hardware, the carve-out is withdrawn and RNF01 becomes universal
again — that is a legitimate outcome, not a failure of this decision.

**Follow-up**

- `non-functional.md` records the carve-out on RNF01 itself, so nobody reads the
  table and concludes login is in breach.
- The k6 script for the auth endpoints is written in M5, alongside RNF05's, and
  reports p95 for login separately from the aggregate.
- Argon2id is the better algorithm and is *not* adopted here: AC-0001-05 already
  names bcrypt, and changing it is a spec decision with a migration attached
  (every stored hash must be rehashed on next login). Worth revisiting when
  there is a reason beyond preference.
