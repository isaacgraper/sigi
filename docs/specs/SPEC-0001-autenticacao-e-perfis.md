---
id: SPEC-0001
title: Autenticação, perfis e gestão de membros
status: Review
version: 0.3
owner: Isaac Kleimann Graper
satisfies: [RF01, RF02, RF18, RN01, RN04, RN16]
depends_on: []
milestone: M2
---

# SPEC-0001 — Autenticação, perfis e gestão de membros

## 1. Purpose

Establishes identity and authorisation. Every other spec assumes an
authenticated actor with a profile; this one creates that actor. It also owns
the RBAC enforcement point, which is the mitigation for OWASP A01 — the risk the
RFC's own threat table ranks first.

## 2. Scope

**In scope** — institutional OIDC login and local-credential login (ADR-0010),
session issuance and refresh, session invalidation, three profiles, member
management (invite, activate, block, deactivate), and the server-side
authorisation rule every other spec depends on.

**Out of scope** — Gov.br, which ADR-0010 cuts rather than defers. Directory
synchronisation: SIGI never reads the tenant's user list, and accounts exist only
because a gestor invited them. Password self-service reset beyond a token e-mail.

**The audit substrate arrives with this spec.** Four criteria here require an
audit row (AC-0001-03, -07, -12, -18), so the append-only history table and its
immutability enforcement land in this slice rather than waiting for SPEC-0007.
SPEC-0007 keeps what it always owned: the history queries, the per-entity
timeline and the auditor's screens. This spec only writes rows.

## 3. Domain model touched

`USUARIO` (created, read, anonymised), `CONVITE` (created, redeemed),
`SESSAO` (created, rotated, revoked), `HISTORICO_MOVIMENTACAO` (append).

Invariants this spec owns:

- **I1** — a session is only ever issued for a `USUARIO` whose status is `ativo`.
- **I2** — the `perfil` that governs authorisation is the one stored on the
  `USUARIO`. No external assertion grants privilege (AC-0001-22).
- **I3** — no `USUARIO` is ever created by an authentication attempt. Accounts
  come from a gestor's invite, and from nowhere else (AC-0001-21).
- **I4** — an audit row referencing a `usuario_id` outlives anonymisation of that
  usuario and never becomes a dangling reference (AC-0001-14).

## 4. Behaviour

### 4.1 Session and token

**AC-0001-01** — Local login issues a token pair
```gherkin
Given an "ativo" usuario whose e-mail is on the institutional domain allowlist
When  local login is requested with the correct password
Then  the response is 200 carrying an access token whose expiry is 15 minutes ahead
And   a refresh token is set as a cookie marked httpOnly, Secure and SameSite=Lax, expiring in 7 days
And   the refresh token value does not appear anywhere in the response body
```
The cookie flags are the criterion, not an implementation note: a refresh token
readable by script is a refresh token stealable by XSS (RNF03).

**AC-0001-02** — A failed login does not disclose whether the e-mail exists
```gherkin
Given an "ativo" usuario "ana@sc.gov.br"
When  local login is requested for "ana@sc.gov.br" with the wrong password
Then  the response is 401 with error code "CREDENCIAIS_INVALIDAS"
When  local login is requested for "naoexiste@sc.gov.br" with any password
Then  the response is 401 with the same code and byte-identical message
```

**AC-0001-03** — Repeated failures lock the account and are audited
```gherkin
Given 5 failed local login attempts for one account within 15 minutes
When  a sixth attempt is made, even with the correct password
Then  the response is 429 with error code "TENTATIVAS_EXCEDIDAS"
And   the message states when the account may try again
And   an audit row records the lockout with the account and the attempt count
And   15 minutes after the last attempt the correct password authenticates normally
```

**AC-0001-04** — Only allowlisted institutional domains may authenticate locally
```gherkin
Given the institutional domain allowlist contains "sc.gov.br"
When  local login is requested for "alguem@gmail.com"
Then  the response is 401 with error code "CREDENCIAIS_INVALIDAS"
And   the response is indistinguishable from a wrong-password response
```

**AC-0001-05** — The stored credential never leaves the database
```gherkin
Given a usuario whose password has been set
When  that usuario is returned by any endpoint, or named in any log line or error body
Then  no field carrying the password hash is present
And   the stored credential is a bcrypt hash at cost 12 or higher
```

**AC-0001-06** — An expired access token is refused; refresh renews without credentials
```gherkin
Given an access token whose expiry has passed
When  it is presented to any authenticated endpoint
Then  the response is 401 with error code "TOKEN_EXPIRADO"
When  the refresh endpoint is called carrying the valid refresh cookie
Then  the response is 200 with a new access token and a rotated refresh cookie
And   no credentials are requested
```

**AC-0001-07** — Logout invalidates the refresh token; a replay is audited
```gherkin
Given a usuario who has logged out
When  the refresh token issued before the logout is replayed
Then  the response is 401 with error code "REFRESH_INVALIDO"
And   an audit row records the replay with the usuario and the token identifier
And   every refresh token descended from the same login is invalidated
```
Rotation plus family invalidation is what makes a stolen refresh token detectable
rather than merely expiring in seven days.

**AC-0001-08** — Deactivation takes effect immediately, not at token expiry
```gherkin
Given an "ativo" usuario holding an access token that has not expired
When  a gestor deactivates that usuario
And   the usuario presents the same unexpired access token
Then  the response is 401 with error code "USUARIO_INATIVO"
```
The active check therefore runs on every request, not only at login (RN01). A
deactivation that waits fifteen minutes is not a deactivation.

**AC-0001-09** — Only the server's own signature is accepted
```gherkin
Given an access token signed RS256 with a key that is not the server's
When  it is presented to any authenticated endpoint
Then  the response is 401
When  a token carrying header "alg": "none" and an otherwise valid payload is presented
Then  the response is 401
And   neither attempt is treated as authenticated
```

### 4.2 Members and invitations

**AC-0001-10** — A gestor invites a member
```gherkin
Given a gestor
When  a member is invited with an institutional e-mail and a perfil
Then  a usuario is created with status "pendente" and no credential
And   a single-use invitation token valid 72 hours is sent to that e-mail
And   the token value does not appear in the response body
And   an audit row records the invite with the gestor as actor and the perfil granted
```

**AC-0001-11** — An invited user activates and sets a password
```gherkin
Given a usuario with status "pendente" and an unredeemed invitation token
When  the token is redeemed with a password of at least 12 characters
Then  the usuario's status becomes "ativo" and a session is issued
And   an audit row records the activation
When  the same token is redeemed again
Then  the response is 409 with error code "CONVITE_JA_UTILIZADO"
When  a token issued more than 72 hours earlier is redeemed
Then  the response is 409 with error code "CONVITE_EXPIRADO"
When  the password is shorter than 12 characters
Then  the response is 422 with error code "SENHA_FRACA" naming the length rule
```

**AC-0001-12** — A gestor blocks an account
```gherkin
Given an "ativo" usuario holding an unexpired access token
When  a gestor blocks the account
Then  the usuario's status becomes "bloqueado"
And   local login returns 401 and the unexpired access token returns 401
And   an audit row records the block with the gestor as actor
```

**AC-0001-13** — A servidor or auditor cannot manage members
```gherkin
Given a servidor, and separately an auditor
When  either attempts to invite, block or deactivate a member
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
And   no usuario row is created or changed
And   the denial produces the audit row AC-0001-18 requires
```

**AC-0001-14** — Deactivation anonymises the person and preserves the history
```gherkin
Given a usuario referenced by at least one audit row
When  a gestor deactivates that usuario
Then  the usuario's nome and email no longer carry the original values
And   the moment of anonymisation is recorded on the usuario
And   every audit row that referenced that usuario still exists
And   each of those rows still resolves to the same usuario_id, never to a dangling reference
And   those rows present a stable pseudonym in place of the original nome
```
`cpf` is deliberately absent: no entity carries it, no requirement needs it, and
`lgpd.md` recommends against collecting it (OQ-10, settled by ADR-0010).
RN16 and LGPD art. 16, I.

### 4.3 Authorisation by profile

**AC-0001-15** — The permission matrix holds for `gestor`
```gherkin
Given the permission matrix and the application's route table
When  every write route is called as an "ativo" gestor
Then  no route is refused for reasons of perfil
```

**AC-0001-16** — The permission matrix holds for `servidor`
```gherkin
Given the permission matrix and the application's route table
When  every write route is called as an "ativo" servidor
Then  each route the matrix denies to servidor returns 403 with "PERFIL_NAO_AUTORIZADO"
And   no route the matrix permits is refused for reasons of perfil
```

**AC-0001-17** — The permission matrix holds for `auditor`
```gherkin
Given the permission matrix and the application's route table
When  every write route is called as an "ativo" auditor
Then  every write route returns 403 with "PERFIL_NAO_AUTORIZADO"
And   read routes the matrix permits are not refused for reasons of perfil
```
The auditor is read-only by construction, which is why the criterion is stated
as "every write route" rather than as a list that could fall out of date.

**AC-0001-18** — Every refusal by profile is audited
```gherkin
Given any authenticated caller
When  a request is refused because the caller's perfil does not permit it
Then  an audit row records the attempted route, the HTTP method, the actor and the timestamp
And   the row is written even though the request changed nothing
```
A 403 that leaves no trace is indistinguishable from an attack that was never
attempted (RFC §3.2).

### 4.4 Institutional OIDC *(new in v0.3 — ADR-0010)*

**AC-0001-19** — The authorization request carries PKCE, state and nonce
```gherkin
Given OIDC is configured with a provider, a client identifier and a redirect URI
When  institutional login is started
Then  the response redirects to the provider's authorization endpoint
And   the redirect carries response_type=code, a PKCE challenge using method S256, a state and a nonce
And   the state and the PKCE verifier are bound to that caller and expire within 10 minutes
When  a callback presents a state that was never issued, or one that has expired
Then  the response is 401 with error code "ESTADO_INVALIDO"
```

**AC-0001-20** — The provider's assertion is verified before it is trusted
```gherkin
Given a callback carrying an authorization code
When  the identity token returned by the provider is verified
Then  a token whose signature does not verify against the provider's published keys returns 401
And   a token whose issuer or audience does not match the configuration returns 401
And   a token whose expiry has passed returns 401
And   a token whose nonce does not match the one issued returns 401
And   a token carrying header "alg": "none" returns 401
And   every rejection is audited with the reason for the rejection
```

**AC-0001-21** — Authentication never creates an account
```gherkin
Given an identity token that verifies, asserting a subject with no usuario in SIGI
When  the callback completes
Then  the response is 403 with error code "USUARIO_NAO_PROVISIONADO"
And   no usuario row is created
And   an audit row records the refused authentication and the asserted e-mail
When  the same happens for a usuario whose status is "pendente", "bloqueado" or "desativado"
Then  the response is 403 and no session is issued
```
Just-in-time provisioning would let anyone in the tenant grant themselves an
account, which would make RF02 and RN01 decorative (I3).

**AC-0001-22** — The profile comes from the usuario record, never from the provider
```gherkin
Given a usuario stored with perfil "servidor"
When  that usuario authenticates through OIDC and the provider asserts a group claim mapping to "gestor"
Then  the session carries perfil "servidor"
And   the asserted claim is recorded on the login's audit row
And   no authorisation decision anywhere consults the asserted claim
```
The 17/08 meeting asked for *"página de administração para atribuir acesso por
usuário"* — the entity assigns the profile, in SIGI. Deriving it from a tenant
group would mean a directory edit silently escalates privilege in a system whose
whole purpose is an auditable trail (I2).

### 4.5 Mechanism selection and route-table completeness

**AC-0001-23** — A write route with no permission entry fails the build
```gherkin
Given the application's route table and the permission matrix
When  the test suite runs
Then  it fails if any write route has no entry in the matrix
And   the failure names the offending route
```
This is what keeps AC-0001-15/-16/-17 honest as the system grows: an endpoint
added without a permission decision is a hole nobody chose to open.

**AC-0001-24** — Local login can be switched off
```gherkin
Given local login is disabled by configuration
When  the local login endpoint is requested with valid credentials
Then  the response is 404
And   institutional OIDC login continues to work
When  local login is enabled
Then  the same request authenticates normally
```
404 rather than 403: a mechanism that is switched off should be
indistinguishable from one that was never built.

## 5. Errors and edge cases

| Condition | HTTP | Error code | Message (pt-BR) |
| --- | --- | --- | --- |
| Wrong password, unknown e-mail, or off-allowlist domain | 401 | `CREDENCIAIS_INVALIDAS` | "E-mail ou senha inválidos." |
| Too many attempts | 429 | `TENTATIVAS_EXCEDIDAS` | "Muitas tentativas. Tente novamente em {minutos} minutos." |
| Access token expired | 401 | `TOKEN_EXPIRADO` | "Sua sessão expirou. Entre novamente." |
| Refresh token invalid or replayed | 401 | `REFRESH_INVALIDO` | "Sua sessão não é mais válida. Entre novamente." |
| Usuario not `ativo` | 401 | `USUARIO_INATIVO` | "Esta conta não está ativa. Procure o gestor da sua unidade." |
| Profile does not permit | 403 | `PERFIL_NAO_AUTORIZADO` | "Seu perfil não permite esta ação." |
| OIDC state absent or expired | 401 | `ESTADO_INVALIDO` | "A tentativa de entrada expirou. Comece novamente." |
| OIDC subject has no account | 403 | `USUARIO_NAO_PROVISIONADO` | "Seu acesso ainda não foi liberado. Procure o gestor da sua unidade." |
| Invitation already redeemed | 409 | `CONVITE_JA_UTILIZADO` | "Este convite já foi utilizado. Peça um novo ao gestor." |
| Invitation older than 72 h | 409 | `CONVITE_EXPIRADO` | "Este convite expirou. Peça um novo ao gestor." |
| Password below the minimum | 422 | `SENHA_FRACA` | "A senha precisa ter ao menos 12 caracteres." |
| E-mail already invited or registered | 409 | `EMAIL_JA_CADASTRADO` | "Já existe uma conta para este e-mail." |

Every `message` is addressed to a servidor, not to a developer, and says what to
do next — which for an access problem is naming who can fix it.

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Invite / activate / block / deactivate members | ✅ | ❌ | ❌ |
| View member list | ✅ | ❌ | ✅ read-only |
| Change own password | ✅ | ✅ | ✅ |
| Authenticate, refresh, log out | ✅ | ✅ | ✅ |

## 7. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | Local login; absent when disabled | 01–05, 24 |
| POST | `/api/v1/auth/refresh` | Rotate the token pair | 06, 07 |
| POST | `/api/v1/auth/logout` | Invalidate the refresh family | 07 |
| GET | `/api/v1/auth/me` | The caller's identity, perfil and scope | 08, 22 |
| GET | `/api/v1/auth/oidc/authorize` | Start institutional login | 19 |
| GET | `/api/v1/auth/oidc/callback` | Complete institutional login | 19–22 |
| GET\|POST | `/api/v1/usuarios` | List members; invite a member | 10, 13, 15–17 |
| POST | `/api/v1/usuarios/{id}/bloquear` | Block | 12, 13 |
| POST | `/api/v1/usuarios/{id}/desativar` | Deactivate and anonymise | 13, 14 |
| POST | `/api/v1/convites/{token}/ativar` | Redeem an invitation | 11 |

All auth routes live under `/api/v1`, resolving a divergence in v0.2, which
listed them at the root while `api-conventions.md` states the prefix is
`/api/v1`.

## 8. Audit events

| Action | `entidade_tipo` | `acao` | `dados_anteriores` |
| --- | --- | --- | --- |
| Successful login | `usuario` | `auth.login` | `{mecanismo, claim_asserido}` |
| Failed login | `usuario` | `auth.falha` | `{motivo}` |
| Lockout | `usuario` | `auth.bloqueio_tentativas` | `{tentativas}` |
| Refresh replay | `usuario` | `auth.refresh_replay` | `{token_id}` |
| OIDC rejection | `usuario` | `auth.oidc_recusada` | `{motivo, email_asserido}` |
| Invite | `usuario` | `usuario.convidado` | `null` |
| Activation | `usuario` | `usuario.ativado` | `{status}` |
| Block | `usuario` | `usuario.bloqueado` | `{status}` |
| Deactivation | `usuario` | `usuario.desativado` | `{status}` |
| Refusal by profile | `usuario` | `auth.negada` | `{rota, metodo, perfil}` |

No row carries a password, a token value, or a `nome` in `dados_anteriores` —
`lgpd.md`'s resolution of the erasure/immutability tension depends on it.

## 9. Open questions

- **OQ-09 — authentication mechanism.** `Assumed` under ADR-0010: institutional
  OIDC as primary, local credentials as a switchable contingency, Gov.br cut.
  Still needs the entity's TI to confirm Entra ID and deliver tenant, client and
  redirect URI. Nothing here blocks on it.
- **OQ-10 — CPF.** `Assumed`: not collected. AC-0001-14 no longer references it.
- **RN07 is not satisfied by this spec.** OQ-04 is resolved — the two axes are
  **unidade** and **grupo de materiais** — but neither `UNIDADE` nor
  `GRUPO_MATERIAL` exists yet, and RN07 constrains which *insumos* a servidor
  may view. A criterion here would assert nothing observable. The scope columns
  and RN07's enforcement therefore land with **SPEC-0003**, the first spec that
  owns a scoped resource. RN07 has been removed from this spec's `satisfies`
  list and `traceability.md` records the move. *(This corrects the plan of
  10/09, which assumed RN07 could be satisfied here.)*
- **Password policy.** Twelve characters is an assumption, not a stakeholder
  statement. It is the observable rule AC-0001-11 needs; if the entity's TI has a
  standard, this is the criterion to revisit.

## 10. Implementation plan

_Filled by `/plan SPEC-0001`._

## Revision history

**v0.3 (2026-09-10)** — the spec becomes implementable. Three changes beyond the
new criteria:

1. **Every criterion is now Given/When/Then.** v0.2 stated them as prose
   sentences, which `spec-format` does not accept and from which tests cannot be
   derived mechanically. No criterion changed meaning in the conversion, and
   **no AC was renumbered**.
2. **AC-0001-15/-16/-17 became three criteria.** They were three IDs sharing one
   paragraph — what `spec-format` calls "three criteria wearing one ID".
3. **AC-0001-14 lost `cpf`.** It anonymised a field that exists in no entity and
   that `lgpd.md` recommends never collecting.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF01–RF02, §6.2, mockup 9.2.3 |
| 0.2 | 2026-09-02 | OQ-09 reframed from the 17/08 meeting: Entra ID, not Gov.br. Candidate axes for RN07 scoping recorded from the data (unidade, grupo de materiais) |
| 0.3 | 2026-09-10 | ADR-0010 adopted: OIDC primary + local contingency, Gov.br cut. AC-19..24 added (PKCE/state/nonce, token verification, no JIT provisioning, perfil never from a claim, route-table completeness, local login switchable). All criteria converted to Given/When/Then; AC-15/16/17 split; AC-14 lost `cpf` (OQ-10 Assumed). Auth routes moved under `/api/v1`. RN07 moved to SPEC-0003 with the reason recorded. Audit substrate scoped into this slice |
