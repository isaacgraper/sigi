# ADR-0010 — Two authentication mechanisms: institutional OIDC and local credentials

- **Status:** Accepted
- **Date:** 2026-09-10
- **Deciders:** Isaac Kleimann Graper (product owner), 2026-09-10
- **Related:** SPEC-0001, RF01, RN01, RNF03, OQ-09, OQ-10, ADR-0002, ADR-0009

## Context

`RF01` reads "autenticação segura com credenciais institucionais **ou Gov.br**".
That wording is frozen RFC v1.6 contract and is not edited. But under ADR-0009
the RFC no longer arbitrates scope, and the evidence contradicts half of it.

**Gov.br was never mentioned.** In the 17/08 meeting the stakeholders described
servidores who *already* hold credentials provisioned by the entity's own TI —
*"já foi feito um processo da TI, no usuário de vocês"* — and the mechanism
discussed was **Microsoft Entra ID**: *"É uma Entra, né?"*, answered *"Dá pra
colocar. É possível."* Gov.br is citizen-to-state federation; SIGI's audience is
internal public servants with an institutional identity. Keeping Gov.br promises
an integration nobody asked for.

Meanwhile SPEC-0001 v0.2's acceptance criteria describe **local credentials**:
bcrypt at cost 12 (AC-0001-05), lockout after five failures (AC-0001-03), an
institutional domain allowlist (AC-0001-04). Those were written before the
meeting was analysed.

And the practical constraint: the entity's TI has not delivered a tenant ID,
client ID or redirect URI. Nothing can be authenticated against the real Entra
tenant today.

## Is this a reversal of ADR-0002?

No, and it is worth saying so explicitly because it will be asked in review.
`ADR-0002` and `CLAUDE.md` invariant 7 forbid HTTP clients for **DOMS and
e-Publica** — the systems that supply *domain data*, where an API contract would
create a second source of truth for ATAs, insumos and stock. An identity
provider is not a data source: it asserts who the caller is and supplies no
insumo, ATA, NE or NF. OIDC discovery and JWKS retrieval are therefore outside
ADR-0002's scope. Consistency with DOMS and e-Publica remains format validation
and CSV import, unchanged.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Local credentials only | Buildable and testable today; no external dependency; the ACs already describe it | Not what the entity described. Every servidor gets a second password to manage, in an organisation that already solved identity. A second login story has to be built later anyway |
| OIDC only | Exactly what the meeting asked for; no password hashes held by SIGI at all, which is the smaller LGPD surface | Blocked on the entity's TI for tenant/client/redirect. No way into the system if the tenant is misconfigured or unreachable — a real risk for an on-premise deployment. The test suite would have nothing to run against |
| **Both** (chosen) | The entity gets the login it described, and there is a way in when the IdP is unavailable or not yet registered. The contingency path is also what makes the suite runnable without a tenant | Two authentication surfaces in the project's first slice: two sets of failure modes, two sets of tests, and a configuration flag whose wrong value silently changes who can log in |

## Decision

1. **OIDC against Entra ID is the primary mechanism.** Authorization code with
   PKCE, `state` and `nonce`; provider metadata from
   `.well-known/openid-configuration`; `id_token` verified against the
   provider's JWKS, keyed by `kid`.
2. **Local credentials are retained as contingency**, and can be **disabled by
   configuration**. When disabled, the local login route does not exist —
   404, not 403, so a disabled mechanism is indistinguishable from one that was
   never built.
3. **Gov.br is cut from scope, not deferred.** It leaves the roadmap's M4
   entirely. Its lead-time risk was imaginary.
4. **No just-in-time provisioning.** A successful OIDC authentication for an
   account that does not exist, or is not `ativo`, is refused and audited — it
   never creates a user. Accounts are born from a gestor's invite (AC-0001-10);
   JIT would let anyone in the tenant provision themselves and would make RF02
   and RN01 decorative.
5. **Claim to `perfil` mapping is explicit and closed.** An unmapped or absent
   group claim resolves to the least-privileged profile, never `gestor`.
6. **Both paths converge on one session.** The same RS256 access token (15 min)
   and the same httpOnly/Secure/SameSite=Lax refresh cookie (7 days), per RNF03.
   Downstream authorisation cannot tell which mechanism authenticated a caller,
   which is what keeps the RBAC surface single.
7. **`usuario.ativo` is checked on every token validation**, regardless of
   mechanism (RN01). A deactivation that waits fifteen minutes is not a
   deactivation, and federating identity does not change that.

## Consequences

**Positive** — The product matches what the entity described, and it still boots
for a demo or a UAT session before the TI finishes the app registration. Because
the local path exists, every OIDC failure mode can be tested against a stub
provider without a tenant. Cutting Gov.br removes a milestone risk that was
never real.

**Negative** — Two mechanisms in the first slice is real cost, and it was
accepted deliberately after being raised: two sets of failure modes, two sets of
tests, and one configuration flag that silently decides who can authenticate.
Getting that flag wrong in production is a security incident, not a bug, which is
why AC-0001-24 pins its observable behaviour.

There is also a privacy cost that a pure-OIDC design would have avoided: keeping
local credentials means SIGI holds password hashes it otherwise would not. That
is a new row in the LGPD register under art. 7, IX (legitimate interest, system
security) — already recorded in `docs/security/lgpd.md`, now load-bearing rather
than incidental.

**Follow-up**

- `OQ-09` becomes `Assumed`. It still needs the entity's TI to confirm Entra ID
  and to deliver tenant ID, client ID and redirect URI. Nothing blocks on it.
- Decide **before go-live** whether local login stays enabled in production. The
  honest default is disabled, with a documented break-glass procedure.
- `OQ-10` is settled in passing: **CPF is not collected.** AC-0001-14 anonymised
  a `cpf` field that exists in no entity and that `lgpd.md` recommends against
  holding. Corrected in SPEC-0001 v0.3.
