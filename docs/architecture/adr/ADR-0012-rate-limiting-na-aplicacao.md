# ADR-0012 — Rate limiting in the application, backed by PostgreSQL

- **Status:** Accepted
- **Date:** 2026-09-10
- **Deciders:** Isaac Kleimann Graper (product owner), 2026-09-10
- **Related:** SPEC-0001, AC-0001-03, RNF05, RNF12, ADR-0010, ADR-0011

## Context

SPEC-0001 had exactly one throttle: `AC-0001-03`, a lockout after five failed
logins for one address. That covers credential stuffing against a single
account and nothing else. Every other authentication path was unprotected:

- `POST /auth/refresh` — a rotation oracle, and the path where a stolen refresh
  token gets exercised.
- `GET /auth/oidc/callback` — unauthenticated, and it performs a network call to
  the provider per request. An attacker can make SIGI hammer the entity's own
  identity provider.
- `POST /convites/{token}/ativar` — a token guessing surface, and it runs bcrypt,
  so each request is deliberately expensive (ADR-0011). Cheap to send, costly to
  serve, which is the shape of an amplification attack.
- The password-reset request added in SPEC-0001 v0.5 — an e-mail bomb and an
  address-enumeration surface at the same time.

The product owner's instruction is direct: protect every call, because attacks
against these paths are common. That is correct, and it is the kind of control
that is far cheaper to design in than to retrofit onto eleven endpoints.

## The problem specific to this entity

The obvious key is the source IP. Here that is a trap.

SIGI's users are public servants inside a state health entity, and the CAME
operation spans eleven-odd units. Institutional networks put whole buildings
behind one NAT address. A per-IP limit tuned for the open internet — say 30
requests a minute — would not stop an attacker; it would lock out an entire
unidade the first busy morning, and the symptom would look like a bug in the
login screen.

Meanwhile the genuine attack signal differs from the legitimate burst in shape,
not volume: many attempts against **few addresses** is stuffing, while many
attempts across **many distinct addresses** is a shift starting work.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Reverse proxy (nginx/traefik) | Zero application code; blocks before the request costs anything | A new service in a compose file the entity deploys on-premise, and the limits then live outside the repository — invisible to review and untestable in CI. Also cannot see the submitted e-mail, so it cannot express the shape distinction above |
| Redis | The right tool: atomic counters, native TTL, no table growth | A new infrastructure component for one feature, on an on-premise deployment that today runs two containers. Somebody has to operate, back up and monitor it |
| **PostgreSQL-backed counters in the application** (chosen) | No new infrastructure; the limits are code, so they are reviewed and tested; can key on route + source + submitted address together | A write per throttled request, and rows to purge. Contention on a hot key is a real ceiling |
| Nothing beyond AC-0001-03 | No work | Leaves ten endpoints open, one of which makes SIGI attack its own identity provider |

## Decision

1. **Rate limiting lives in the application**, as an authorisation-layer
   dependency applied to **every** route under `/api/v1/auth` and
   `/api/v1/convites`, backed by a `LIMITE_TAXA` table.
2. **Two independent throttles, because they answer different questions.**
   - The **per-address lockout** of AC-0001-03 stays exactly as specified: five
     failures, fifteen-minute decay, keyed on an HMAC of the submitted address.
     It answers "is someone attacking this account?"
   - A **per-source, per-route limit** answers "is someone abusing this
     endpoint?" Exceeding it returns 429 with `Retry-After`.
   Neither subsumes the other: the first misses a spray across many addresses,
   the second misses a slow, patient attack on one.
3. **Limits are configuration, not constants in code.** Per-route ceilings and
   window lengths come from settings, so the entity can tune them against its
   real traffic without a deploy of new code.
4. **Trusted ranges get a higher ceiling, never an exemption.** A configurable
   list of institutional CIDRs is throttled at its own, much larger limit. An
   exemption would mean an attacker who reaches the internal network faces no
   limit at all, which is precisely when limits matter most.
5. **429 is uniform and says nothing.** The body carries no hint about which
   throttle fired or how close the caller was, because that is a measuring
   instrument handed to the attacker. `Retry-After` is the only signal.
6. **Every throttle event is audited** (`auth.limite_excedido`), so a
   distributed attempt is visible in the history rather than only in logs — and
   with no address written literally, per SPEC-0001 §8.

## Consequences

**Positive** — Eleven endpoints go from unprotected to protected in one
mechanism, with the limits under version control and asserted by tests. The
OIDC callback stops being a way to make SIGI hammer the entity's identity
provider. And because the ceilings are configuration, the entity can raise them
after a false positive instead of waiting for a release.

**Negative** — Every throttled request now performs a database write before it
does anything useful, on exactly the paths ADR-0011 already conceded are the
slow ones. That is a real cost, accepted because auth traffic is low volume: a
few hundred logins a day across eleven unidades, not a few hundred a second.
There is also a table that grows and needs purging, and a hot-key contention
ceiling that Redis would not have.

**The honest failure mode:** if the entity's traffic ever makes this contend,
the symptom will be slow logins under load — which is also what ADR-0011's
carve-out predicts for an unrelated reason. Those two must not be confused, so
the k6 auth script reports throttle-table wait time separately from bcrypt time.
Redis is the documented next step, not a rewrite.

**Follow-up**

- `RNF16` records the requirement so it is verified rather than assumed.
- Purging `LIMITE_TAXA` is a scheduled job, and it must not be the thing that
  keeps the table healthy in production while nobody notices it is not running.
  It is one of the two jobs this project now has, alongside partition creation.
- Revisit the store if p95 on the auth routes is dominated by the throttle write
  rather than by bcrypt.
