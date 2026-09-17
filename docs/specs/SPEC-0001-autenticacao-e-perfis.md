---
id: SPEC-0001
title: Autenticação, perfis e gestão de membros
status: Approved
version: 0.5
owner: Isaac Kleimann Graper
satisfies: [RF01, RF02, RF18, RN01, RN04, RN06, RN16]
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
because a gestor invited them.

*(v0.5)* **Password reset is in scope, and was missing.** v0.3's scope line read
"password self-service reset beyond a token e-mail" — declaring the token-e-mail
flow in scope by exception and then never giving it a criterion. Worse, v0.3 cut
"change own password" from the permission matrix *and* added AC-0001-28, which
refuses inviting an address that already has an account **in any status**.
Between them, a servidor who forgot a local password had no path at all: no
self-service, no re-invite, only database access. AC-0001-30 through -32 close
it.

**The audit substrate arrives with this spec.** Four criteria here require an
audit row (AC-0001-03, -07, -12, -18), so the append-only history table and its
immutability enforcement land in this slice rather than waiting for SPEC-0007.
SPEC-0007 keeps what it always owned: the history queries, the per-entity
timeline and the auditor's screens. This spec only writes rows.

## 3. Domain model touched

`USUARIO` (created, read, anonymised), `TOKEN_CREDENCIAL` (created, redeemed —
invitations and password resets share one grant mechanism),
`SESSAO_FAMILIA` and `SESSAO` (created, rotated, revoked),
`TENTATIVA_LOGIN` and `LIMITE_TAXA` (the two throttles),
`HISTORICO_MOVIMENTACAO` (append).

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
And   the same holds at the lockout threshold: a sixth attempt returns 429 for
      both addresses, so counting attempts never reveals which one exists
```
*(v0.4)* The last line was added because it was **false** as v0.3 specified it.
The lockout was keyed on the account, so an unknown address had no counter and
answered 401 forever while a known one switched to 429 — six requests
distinguished them. That is why the counter is keyed on the submitted address
rather than on the usuario (AC-0001-03).

**AC-0001-03** — Repeated failures lock the address and are audited
```gherkin
Given 5 failed local login attempts for one e-mail address, each within 15
      minutes of the previous one
When  a sixth attempt is made, even with the correct password
Then  the response is 429 with error code "TENTATIVAS_EXCEDIDAS"
And   the message states when the address may try again
And   an audit row records the lockout with the attempt count
And   15 minutes after the last attempt, the correct password authenticates normally
Given 4 failed attempts whose last one was more than 15 minutes ago
When  a fifth attempt fails
Then  it counts as the first, not the fifth, and no lockout occurs
Given a locked-out address belonging to an "ativo" usuario
When  that usuario authenticates through institutional OIDC
Then  the response is 200 and a session is issued
```
*(v0.4)* Three things this now pins that v0.3 left ambiguous or wrong:

- **The counter is keyed on the submitted address, not on the usuario.** Keying
  it on the account made AC-0001-02 false, and an unknown address unlockable.
- **The window decays by inactivity.** "Five within fifteen minutes" and
  "unlocked fifteen minutes after the last attempt" are not the same rule; the
  decay is the one implemented, and the fourth `Given` above is what proves it.
  A stored counter with no timestamp expresses only "five failures ever", which
  would lock an account over failures spread across days.
- **The lockout does not reach institutional OIDC.** Otherwise anyone who knows
  the last gestor's e-mail could deny member management in fifteen-minute
  blocks, indefinitely and anonymously — the outcome AC-0001-29 exists to
  prevent, reached by a route it does not guard. With OIDC as the primary
  mechanism (ADR-0010) the gestor still gets in; with local login disabled in
  production the attack surface does not exist at all.

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
When  the token is redeemed with a password meeting the policy
Then  the usuario's status becomes "ativo"
And   a session is issued, so activation and first login are one step
And   an audit row records the activation
```

**AC-0001-25** — An invitation is single-use and time-boxed
```gherkin
Given an invitation token that has already been redeemed
When  it is redeemed again
Then  the response is 409 with error code "CONVITE_JA_UTILIZADO"
And   the usuario's credential is unchanged
Given an invitation token issued more than 72 hours earlier
When  it is redeemed
Then  the response is 409 with error code "CONVITE_EXPIRADO"
And   the usuario's status remains "pendente"
```

**AC-0001-26** — The password policy is enforced on activation
```gherkin
Given a usuario with status "pendente" and a valid invitation token
When  the token is redeemed with a password shorter than 12 characters
Then  the response is 422 with error code "SENHA_FRACA"
And   the message states the length rule
And   the token remains unredeemed, so a second attempt with a valid password succeeds
```
The token surviving a rejected password is the point: a typo must not burn the
invitation and force the gestor to issue another.

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

**AC-0001-28** — An invitation is refused for a duplicate or off-domain e-mail
```gherkin
Given a usuario already exists for "ana@sc.gov.br", in any status
When  a gestor invites "ana@sc.gov.br"
Then  the response is 409 with error code "EMAIL_JA_CADASTRADO"
And   no second usuario row and no second invitation is created
When  a gestor invites "alguem@gmail.com", which is not on the institutional allowlist
Then  the response is 422 with error code "DOMINIO_NAO_INSTITUCIONAL"
And   the message names the allowed domains
```
*(v0.5)* The duplicate-e-mail rule is right — a second account for one person
would split their audit trail — but until v0.5 it was also the reason a
forgotten password had no remedy, because re-inviting was the only workaround
anyone would reach for. The remedy is AC-0001-30/-32, and
`EMAIL_JA_CADASTRADO`'s message now says so.

**AC-0001-29** — The last active gestor cannot be locked out
```gherkin
Given exactly one usuario with perfil "gestor" and status "ativo"
When  a gestor blocks or deactivates that usuario, including themselves
Then  the response is 409 with error code "ULTIMO_GESTOR"
And   the usuario remains "ativo" with perfil "gestor"
When  that usuario's perfil is changed to "servidor" or "auditor"
Then  the response is 409 with the same code
Given two "ativo" gestores
When  one is deactivated
Then  the operation succeeds
Given two gestores being deactivated concurrently, one per request
Then  exactly one succeeds and at least one "ativo" gestor remains
```
Without this, one sequence of two permitted actions leaves the entity with no
one able to manage members — and because there is no self-registration
(AC-0001-21), there is no way back in without database access.

*(v0.4)* Two additions. **Demotion is the same hole**: changing the last
gestor's perfil empties the role exactly as blocking it does, and no endpoint
exposes that today, which is the cheapest moment to close it. And the
**concurrency criterion** is there because this is a cross-row condition, so two
simultaneous requests can each observe two active gestores and both commit —
write skew, which snapshot isolation does not prevent. A test that runs the race
once proves nothing; it has to run many times.

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

**On RN04.** RN04 — "only `gestor` may issue and close ATAs" — names endpoints
that do not exist in this slice. This spec satisfies it by **owning the
mechanism**: the server-side authorisation dependency, the permission matrix, and
AC-0001-23's guarantee that no write route escapes it. Each spec that adds
routes proves RN04 for its own, with the per-role test its own criteria demand.
Contrast RN07, which this spec does *not* claim: RN07 constrains which *insumos*
a servidor may see, and that is a resource-level rule with no mechanism to own
here (see §9).

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

**AC-0001-23** — Every write route carries a permission decision
```gherkin
Given the application's route table, as the running application reports it
When  it is compared against the permission matrix
Then  every route that mutates state has an entry in the matrix
And   a route without one is reported by name
```
This is a property of the assembled application, so it is assertable the moment
the app is constructed — which is what keeps AC-0001-15/-16/-17 honest as the
system grows. An endpoint added without a permission decision is a hole nobody
chose to open, and the default for a missing entry is refusal, never permission.

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

### 4.6 Password reset *(new in v0.5)*

**AC-0001-30** — Requesting a reset never discloses whether the address exists
```gherkin
Given local login is enabled
When  a reset is requested for an address with an "ativo" account and a local credential
Then  the response is 202 and a single-use token valid 1 hour is sent to that address
When  a reset is requested for an address with no account at all
Then  the response is 202 with a byte-identical body, and no token is issued
When  a reset is requested for an account that authenticates only through OIDC,
      or whose status is not "ativo"
Then  the response is 202 with the same body, no token is issued,
      and an audit row records the refusal and its reason
And   in all three cases the response does not wait on the e-mail transport,
      so how long it takes reveals nothing either
```
The uniform 202 is the whole point: a reset form that answers differently for a
known address is an account-enumeration endpoint with a helpful error message.

**AC-0001-31** — Redeeming a reset token replaces the credential and ends every session
```gherkin
Given a valid, unredeemed reset token for an "ativo" usuario holding two active sessions
When  the token is redeemed with a password meeting the policy
Then  the usuario's credential is replaced
And   every session of that usuario is revoked with reason "redefinicao"
And   an audit row records the reset
When  the same token is redeemed again
Then  the response is 409 with error code "REDEFINICAO_JA_UTILIZADA"
When  a token issued more than 1 hour earlier is redeemed
Then  the response is 409 with error code "REDEFINICAO_EXPIRADA"
When  the password is shorter than the policy allows
Then  the response is 422 with "SENHA_FRACA" and the token remains unredeemed
```
Revoking every session is not optional and cuts both ways deliberately. If the
person reset because they suspect theft, it evicts the thief; if a thief with
mailbox access did the reset, it evicts the owner, who then notices. Leaving old
sessions alive would make the reset cosmetic in the case that matters.

One hour, against the invitation's 72: an invitation waits for someone to get
around to joining, while a reset is requested by a person sitting at the screen.
The exposure window should match the intent.

**AC-0001-32** — A gestor can trigger a reset for a member
```gherkin
Given a gestor and an "ativo" member with a local credential
When  the gestor triggers a reset for that member
Then  a single-use token valid 1 hour is sent to the member's own address
And   the response carries no token
And   an audit row records the gestor as actor and the member as target
When  a servidor or an auditor triggers a reset for another member
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
The token still goes only to the member's own address — a gestor triggers the
reset, never learns the token, and cannot set the password. That keeps the
support path (a servidor telephones the gestor, which is what actually happens)
without turning a gestor into someone who can take over an account silently.

### 4.7 Rate limiting *(new in v0.5)*

**AC-0001-33** — Every authentication route is rate-limited per source
```gherkin
Given a per-route ceiling and window taken from configuration
When  one source exceeds the ceiling within the window on any route under
      "/api/v1/auth" or "/api/v1/convites"
Then  the response is 429 with error code "LIMITE_DE_TAXA" and a Retry-After header
And   the body says nothing about which throttle fired, nor how many attempts remain
And   an audit row records the event with no address in clear
Given a source inside a configured institutional range
When  it exceeds the ordinary ceiling but stays below that range's own, higher ceiling
Then  requests continue to be served
And   exceeding the higher ceiling also returns 429
Given the application's route table
When  it is compared against the configured ceilings
Then  every route under those two prefixes has one, and a route without is reported by name
```
This is a second, independent throttle, not a replacement for AC-0001-03. That
one asks "is someone attacking this account?" and is keyed on the submitted
address; this one asks "is someone abusing this endpoint?" and is keyed on the
source. Neither contains the other: the first misses a spray across many
addresses, the second misses a slow, patient attack on one.

The higher ceiling for institutional ranges rather than an exemption is
deliberate, and so is its direction: whole unidades sit behind one NAT address,
so a ceiling tuned for the open internet would lock out a building on its first
busy morning — while an exemption would mean an attacker inside the network
faces no limit at all. ADR-0012 carries the reasoning.

### 4.8 The audit substrate *(new in v0.3)*

**AC-0001-27** — The history table refuses to be rewritten
```gherkin
Given an audit row written by any of the criteria above
When  an UPDATE is issued against it as the application's database role
Then  the statement fails
When  a DELETE is issued against it as the application's database role
Then  the statement fails
And   both failures originate in the database, not in application code
And   the row is unchanged afterwards
```
Enforced twice on purpose (ADR-0004): the privilege stops the application, and
the trigger stops whatever the privilege does not — a superuser session, or a
`GRANT` someone adds later. RN06 and RNF08.

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
| Reset token already used | 409 | `REDEFINICAO_JA_UTILIZADA` | "Este link de redefinição já foi usado. Solicite outro." |
| Reset token older than 1 hour | 409 | `REDEFINICAO_EXPIRADA` | "Este link de redefinição expirou. Solicite outro." |
| Rate limit exceeded | 429 | `LIMITE_DE_TAXA` | "Muitas requisições. Tente novamente em instantes." |
| E-mail already invited or registered | 409 | `EMAIL_JA_CADASTRADO` | "Já existe uma conta para este e-mail. Se a pessoa esqueceu a senha, use 'redefinir senha' em vez de convidar de novo." |
| Invited e-mail outside the institutional domains | 422 | `DOMINIO_NAO_INSTITUCIONAL` | "Use um e-mail institucional. Domínios aceitos: {dominios}." |
| Would leave no active gestor | 409 | `ULTIMO_GESTOR` | "Esta é a única conta de gestor ativa. Promova outro gestor antes de bloquear ou desativar esta." |

Every `message` is addressed to a servidor, not to a developer, and says what to
do next — which for an access problem is naming who can fix it.

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Invite / activate / block / deactivate members | ✅ | ❌ | ❌ |
| Trigger a password reset for another member | ✅ | ❌ | ❌ |
| View member list | ✅ | ❌ | ✅ read-only |
| Authenticate, refresh, log out | ✅ | ✅ | ✅ |
| Request a reset for one's own address | unauthenticated — see AC-0001-30 | | |

*(2026-09-10)* **"Change own password" left this matrix.** v0.2 granted it to all
three profiles while specifying no criterion and no endpoint for it — a matrix
entry that permits something the spec never defined. It is now explicitly out of
scope: institutional OIDC is the primary mechanism and the honest production
default is local login disabled (ADR-0010), so a self-service password change
serves only the break-glass path. A servidor who needs a new local credential
gets a fresh invitation from a gestor, which is auditable and already specified
(AC-0001-10/11). Revisit if local login is ever the primary mechanism.

## 7. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | Local login; absent when disabled | 01–05, 24 |
| POST | `/api/v1/auth/refresh` | Rotate the token pair | 06, 07 |
| POST | `/api/v1/auth/logout` | Invalidate the refresh family | 07 |
| GET | `/api/v1/auth/me` | The caller's identity, perfil and scope | 08, 22 |
| GET | `/api/v1/auth/oidc/authorize` | Start institutional login | 19 |
| GET | `/api/v1/auth/oidc/callback` | Complete institutional login | 19–22 |
| GET\|POST | `/api/v1/usuarios` | List members; invite a member | 10, 13, 15–17, 28 |
| POST | `/api/v1/usuarios/{id}/bloquear` | Block | 12, 13, 29 |
| POST | `/api/v1/usuarios/{id}/desativar` | Deactivate and anonymise | 13, 14, 29 |
| POST | `/api/v1/convites/{token}/ativar` | Redeem an invitation | 11, 25, 26 |
| POST | `/api/v1/auth/redefinicoes` | Request a reset; always 202 | 30, 33 |
| POST | `/api/v1/auth/redefinicoes/{token}/confirmar` | Set a new password | 31 |
| POST | `/api/v1/usuarios/{id}/redefinir-senha` | Gestor triggers a reset | 32 |

All auth routes live under `/api/v1`, resolving a divergence in v0.2, which
listed them at the root while `api-conventions.md` states the prefix is
`/api/v1`.

## 8. Audit events

| Action | `entidade_tipo` | `acao` | `dados_anteriores` |
| --- | --- | --- | --- |
| Successful login | `usuario` | `auth.login` | `{mecanismo, claim_asserido}` |
| Failed login | `usuario` | `auth.falha` | `{motivo, email_hmac, dominio}` |
| Lockout | `usuario` | `auth.bloqueio_tentativas` | `{tentativas}` |
| Refresh replay | `usuario` | `auth.refresh_replay` | `{token_id}` |
| OIDC rejection | `usuario` | `auth.oidc_recusada` | `{motivo, email_hmac, dominio}` |
| Invite | `usuario` | `usuario.convidado` | `null` |
| Activation | `usuario` | `usuario.ativado` | `{status}` |
| Block | `usuario` | `usuario.bloqueado` | `{status}` |
| Deactivation | `usuario` | `usuario.desativado` | `{status}` |
| Refusal by profile | `usuario` | `auth.negada` | `{rota, metodo, perfil}` |
| Blocked attempt to remove the last gestor | `usuario` | `usuario.ultimo_gestor` | `{alvo_id}` |
| Reset requested | `usuario` | `auth.redefinicao_solicitada` | `{email_hmac, dominio}` |
| Reset refused (no account, or not `ativo`, or OIDC-only) | `usuario` | `auth.redefinicao_recusada` | `{motivo, email_hmac, dominio}` |
| Reset completed | `usuario` | `auth.redefinicao_concluida` | `{sessoes_revogadas}` |
| Reset triggered by a gestor | `usuario` | `usuario.redefinicao_disparada` | `{alvo_id}` |
| Rate limit exceeded | `usuario` | `auth.limite_excedido` | `{rota, origem_hmac}` |

No row carries a password, a token value, or a `nome` in `dados_anteriores` —
`lgpd.md`'s resolution of the erasure/immutability tension depends on it.

**And no row carries an e-mail address.** *(v0.4, correcting v0.3.)* v0.3 wrote
`{email_asserido}` into `auth.oidc_recusada`, for a caller who by definition has
**no** `USUARIO` row (AC-0001-21). An institutional e-mail is personal data; the
audit table can never be corrected (AC-0001-27); and there is no account to
anonymise later — so that address would have been permanent, in the one table
`lgpd.md` promises never carries personal data. Replaced by a **peppered HMAC of
the address plus the bare domain**: repeated attempts against one address stay
correlatable for an investigation, and the address itself is not recoverable
from the row. The pepper lives in application configuration, never in the
database, so a leaked dump does not let an attacker confirm a guessed address.

An audit row therefore may have **no actor at all**: `usuario_id` is nullable,
because AC-0001-20 and AC-0001-21 both produce rows for callers with no account.
Invariant I4 still holds — a row that *does* name a `usuario_id` never loses it.

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

*Produced by `/plan SPEC-0001` on 2026-09-10, after the persistence review that
drove v0.4. Not yet executed.*

### New dependencies

| Dependency | Why | Alternative rejected |
| --- | --- | --- |
| `bcrypt` | AC-0001-05 names the algorithm and the cost | argon2 is stronger, but the criterion is already written and changing it is a spec decision, not a plan one |
| `pyjwt[crypto]` | RS256 issuance (AC-0001-09) and verification of the provider's assertion (AC-0001-20) | `authlib` bundles an OIDC client we would use a tenth of |
| `httpx2` | OIDC token exchange, JWKS retrieval, and the `TestClient` Starlette 1.6 now wants | `httpx` 0.28 works, but Starlette then warns on every test that uses `TestClient`, and the auth suite lives there |
| `mypy` *(dev)* | definition-of-done already required a clean run; the pipeline did not run it | — |

**Not** used: `PyJWKClient`, although it ships with `pyjwt`. It fetches JWKS with
`urllib`, which would force the tests' fake provider to bind a real socket
instead of being an ASGI app. Fetching JWKS through the injected `httpx2` client
keeps the provider a fixture and puts the `kid` cache AC-0001-20 needs under
explicit control.

### Migration — `0001_baseline`

The project's first migration; `migrations/versions/` is empty. Tables:
`usuario`, `tentativa_login`, `token_credencial`, `limite_taxa`,
`sessao_familia`, `sessao`, `historico_movimentacao` + seven partitions. Full DDL, constraint names and the
reasoning behind each are in `docs/architecture/data-model.md`, which was
corrected on 2026-09-10 for exactly this migration.

Hand-written `op.execute`, not autogenerate: partitioning, the trigger, the
`SECURITY DEFINER` partition function, generated columns and grants are all
invisible to Alembic's comparison. `env.py` gains an `include_object` filter
excluding `historico_movimentacao_%` so the *next* autogenerate does not propose
dropping every partition.

**`downgrade()` refuses** when `historico_movimentacao` holds any row, raising
`SI002` with the count. It drops the parent (not enumerated partitions), then
the trigger function. What a permitted downgrade loses: every usuario, session,
invitation and lockout counter — acceptable, because it can only run on an empty
audit trail, which means nothing auditable has happened yet.

**Precondition, not a step:** two database roles. See Risks.

### Modules

| Layer | Files |
| --- | --- |
| Migration | `backend/migrations/versions/0001_baseline.py`; `migrations/env.py` (filter) |
| Models | `app/models/usuario.py`, `token_credencial.py`, `sessao.py`, `tentativa_login.py`, `limite_taxa.py`, `historico.py` |
| Repositories | `app/repositories/usuario.py`, `token_credencial.py`, `sessao.py`, `tentativa_login.py`, `limite_taxa.py`, `historico.py` |
| Services | `app/services/autenticacao.py`, `sessoes.py`, `bloqueio.py`, `credenciais.py` (invites and resets share the grant mechanics), `membros.py`, `oidc.py`, `auditoria.py`, `permissoes.py`, `limite_taxa.py` |
| Domain errors | `app/services/erros.py` — one exception per error code in §5 |
| API | `app/api/auth.py`, `oidc.py`, `usuarios.py`, `convites.py`; `app/api/erros.py` (exception→envelope mapping) |
| Dependencies | `app/core/seguranca.py` (token issue/verify, the active check of AC-0001-08), `app/core/autorizacao.py` (the matrix and the route audit), `app/core/limite.py` (the AC-0001-33 throttle, applied to two path prefixes) |
| Schemas | `app/schemas/auth.py`, `usuario.py`, `convite.py` |
| Config | `app/core/config.py` — keys, TTLs, allowlist, `local_login_enabled`, OIDC, HMAC pepper, per-route ceilings and institutional CIDRs |
| Infra | `docker-compose.yml`, `.env.example` (two roles) |

Layering per CLAUDE.md: no `HTTPException` below `app/api/`, no business rule in
a repository, and the audit row written in the same transaction as its mutation.

### Endpoints

| Method | Path | Request → Response | ACs |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | `{email, senha}` → access token + refresh cookie | 01–05, 24 |
| POST | `/api/v1/auth/refresh` | refresh cookie → rotated pair | 06, 07 |
| POST | `/api/v1/auth/logout` | refresh cookie → 204 | 07 |
| GET | `/api/v1/auth/me` | — → `{id, nome, email, perfil}` | 08, 22 |
| GET | `/api/v1/auth/oidc/authorize` | — → 302 to the provider | 19 |
| GET | `/api/v1/auth/oidc/callback` | `?code&state` → session or 401/403 | 19–22 |
| GET | `/api/v1/usuarios` | `?page&size` → paged members | 15–17 |
| POST | `/api/v1/usuarios` | `{email, perfil}` → created `pendente` | 10, 13, 28 |
| POST | `/api/v1/usuarios/{id}/bloquear` | — → 200 or 409 | 12, 13, 29 |
| POST | `/api/v1/usuarios/{id}/desativar` | — → 200 or 409 | 13, 14, 29 |
| POST | `/api/v1/convites/{token}/ativar` | `{senha}` → session | 11, 25, 26 |
| POST | `/api/v1/auth/redefinicoes` | `{email}` → 202, always | 30 |
| POST | `/api/v1/auth/redefinicoes/{token}/confirmar` | `{senha}` → 204, sessions revoked | 31 |
| POST | `/api/v1/usuarios/{id}/redefinir-senha` | — → 202 | 32 |

Errors use the envelope in `api-conventions.md`; `code` from §5, `message` pt-BR.
AC-0001-33's throttle wraps every row above except the three `usuarios` routes,
which are already behind authentication and the permission matrix.

### Tests — every AC mapped

| AC | File · function |
| --- | --- |
| 01 | `test_auth_login.py::test_ac_0001_01_login_emite_par_de_tokens` |
| 02 | `test_auth_login.py::test_ac_0001_02_resposta_identica_para_email_inexistente` |
| 03 | `test_auth_lockout.py::test_ac_0001_03_bloqueio_por_tentativas` · `::test_ac_0001_03_decaimento_da_janela` · `::test_ac_0001_03_oidc_nao_e_afetado` |
| 04 | `test_auth_login.py::test_ac_0001_04_dominio_fora_da_allowlist` |
| 05 | `test_auth_login.py::test_ac_0001_05_hash_nunca_sai_do_banco` |
| 06 | `test_auth_tokens.py::test_ac_0001_06_token_expirado_e_refresh` |
| 07 | `test_auth_tokens.py::test_ac_0001_07_logout_e_replay_derruba_familia` |
| 08 | `test_auth_active_check.py::test_ac_0001_08_desativacao_vale_imediatamente` |
| 09 | `test_auth_tokens.py::test_ac_0001_09_assinatura_alheia_e_alg_none` |
| 10 | `test_usuarios_convites.py::test_ac_0001_10_gestor_convida` |
| 11 | `test_usuarios_convites.py::test_ac_0001_11_ativacao` |
| 12 | `test_usuarios_gestao.py::test_ac_0001_12_bloqueio` |
| 13 | `test_usuarios_gestao.py::test_ac_0001_13_servidor_e_auditor_nao_gerenciam` |
| 14 | `test_usuarios_gestao.py::test_ac_0001_14_anonimizacao_preserva_historico` |
| 15 | `test_permissoes.py::test_ac_0001_15_matriz_gestor` |
| 16 | `test_permissoes.py::test_ac_0001_16_matriz_servidor` |
| 17 | `test_permissoes.py::test_ac_0001_17_matriz_auditor` |
| 18 | `test_permissoes.py::test_ac_0001_18_recusa_por_perfil_e_auditada` |
| 19 | `test_auth_oidc.py::test_ac_0001_19_pkce_state_nonce` |
| 20 | `test_auth_oidc.py::test_ac_0001_20_verificacao_do_id_token` |
| 21 | `test_auth_oidc.py::test_ac_0001_21_sem_provisionamento_jit` |
| 22 | `test_auth_oidc.py::test_ac_0001_22_perfil_vem_do_registro` |
| 23 | `test_permissoes.py::test_ac_0001_23_toda_rota_de_escrita_tem_entrada` |
| 24 | `test_auth_login.py::test_ac_0001_24_login_local_desligavel` |
| 25 | `test_usuarios_convites.py::test_ac_0001_25_convite_uso_unico_e_expiracao` |
| 26 | `test_usuarios_convites.py::test_ac_0001_26_politica_de_senha` |
| 27 | `test_audit_immutability.py::test_ac_0001_27_historico_recusa_update_e_delete` |
| 28 | `test_usuarios_convites.py::test_ac_0001_28_convite_duplicado_ou_fora_do_dominio` |
| 29 | `test_usuarios_gestao.py::test_ac_0001_29_ultimo_gestor` · `::test_ac_0001_29_corrida_entre_dois_gestores` |
| 30 | `test_redefinicao_senha.py::test_ac_0001_30_202_uniforme_para_os_tres_casos` |
| 31 | `test_redefinicao_senha.py::test_ac_0001_31_troca_credencial_e_revoga_sessoes` · `::test_ac_0001_31_uso_unico_e_expiracao` |
| 32 | `test_redefinicao_senha.py::test_ac_0001_32_gestor_dispara_sem_ver_o_token` |
| 33 | `test_limite_taxa.py::test_ac_0001_33_429_com_retry_after` · `::test_ac_0001_33_faixa_institucional_tem_teto_maior` · `::test_ac_0001_33_toda_rota_tem_teto` |

Plus `test_migration_baseline.py`, which proves the schema rather than an AC:
the illegal-PK correction, partition bounds under `TimeZone='America/Sao_Paulo'`,
a per-partition ACL of exactly `{SELECT, INSERT}`, the cloned trigger being
`ENABLE ALWAYS`, an insert into an unpartitioned year raising `23514`, and
`downgrade()` refusing with `SI002` against a non-empty table.

AC-0001-29's race test runs many iterations, not once: write skew is
probabilistic and a single pass proves nothing.

### Sequence

1. Two database roles — `docker-compose.yml`, `.env.example`, `config.py`, and a
   `pg_roles` guard in the migration. **Nothing else can be trusted before this.**
2. `0001_baseline` + `test_migration_baseline.py`.
3. Test harness: `conftest.py` gains a real PostgreSQL fixture and a
   second-role connection, without which AC-0001-27 cannot be asserted.
4. Models and repositories.
5. `auditoria.py` + `test_audit_immutability.py` — the substrate everything else
   writes to.
6. Auth config, key handling, token issue/verify.
7. Local login, refresh, logout, `/me` (AC-01..09, 24).
8. Lockout (AC-03), on its own commit because it owns the committed-on-rollback
   subtlety.
9. Permission matrix, authorisation dependency, route-table check (AC-15..18, 23).
10. Invitations and member management (AC-10..14, 25, 26, 28, 29).
11. OIDC and the fake provider fixture (AC-19..22).
12. Rate limiting (AC-33), last among the features because it wraps routes that
    must already exist — and its route-coverage check then fails loudly if a
    later commit adds an auth route without a ceiling.
13. Password reset (AC-30..32), which reuses the grant mechanics from step 10
    and the throttle from step 12; without the throttle, the request endpoint is
    an e-mail bomb.
14. `/trace`, `security-reviewer`, then the PR.

### Risks

| Risk | Cheapest early detection |
| --- | --- |
| **One database role.** `docker-compose.yml` ships `sigi` as owner *and* application role, and an owner can `ALTER TABLE ... DISABLE TRIGGER`. Until a second role exists, ADR-0004's guarantee is enforced by nothing | Step 1, before any DDL. `test_audit_immutability.py` asserts the failure as `sigi_app`, so a single-role setup fails the suite instead of passing it |
| **RNF01 vs AC-0001-05.** RNF01 demands p95 under 300 ms; a bcrypt cost-12 verification alone costs roughly 250–400 ms, so `POST /auth/login` **cannot** meet it. This is a requirement conflict, not a tuning problem | Measure in step 7 and settle it then: either RNF01 carves out credential verification explicitly, or AC-0001-05's cost changes. Both are spec edits. Do not silently lower the cost |
| **January outage.** Nothing creates next year's partition, and every write depends on the audit insert | Partitions through 2032 in step 2, plus the `23514` test that names the failure mode |
| **Two scheduled jobs, both failing silently.** Partition creation and `limite_taxa` purging. Neither raises an error when it stops running; the first surfaces as a total write outage in January, the second as a table that quietly grows | Partitions through 2032 remove the first from the critical path for six years. For the purge, a row-count check belongs in whatever monitoring RNF02 brings — recorded now so it is a known gap rather than a discovery |
| **HMAC pepper rotation.** Rotating it silently breaks lockout continuity and de-correlates historical audit rows for one address | Document it as a one-way decision in `.env.example` before the first row is written |
| **No Docker locally.** The DB-backed tests, the whole substrate, run only in CI | Accepted; steps 2–5 are validated by CI on the first push, not locally |
| **OIDC against the real tenant is unverifiable** until the entity's TI delivers tenant/client/redirect (OQ-09) | The fake provider covers our side of the contract; the first real login stays a known unknown |

## Revision history

**v0.3 (2026-09-10)** — the spec becomes implementable.

Changes beyond the new OIDC criteria:

1. **Every criterion is now Given/When/Then.** v0.2 stated them as prose
   sentences, which `spec-format` does not accept and from which tests cannot be
   derived mechanically. No criterion changed meaning in the conversion, and
   **no AC was renumbered**.
2. **AC-0001-15/-16/-17 became three criteria.** They were three IDs sharing one
   paragraph — what `spec-format` calls "three criteria wearing one ID".
3. **AC-0001-14 lost `cpf`.** It anonymised a field that exists in no entity and
   that `lgpd.md` recommends never collecting.

`/spec-review` then refused the first draft of v0.3 and found five more, all
fixed here:

4. **AC-0001-11 was four criteria in one ID** — activation, replay, expiry and
   weak password, with three different status codes. Split into -11, -25 and -26.
5. **The audit substrate had no criterion.** This slice builds the `REVOKE` and
   the trigger, so RN06 and RNF08 are proven here, not in SPEC-0007. Now
   AC-0001-27, and RN06 joins `satisfies`.
6. **`EMAIL_JA_CADASTRADO` sat in the error table with no criterion.** Inviting
   the same e-mail twice, or an off-domain address, had no specified behaviour.
   Now AC-0001-28.
7. **Nothing stopped the last gestor being locked out.** Two permitted actions
   in sequence could leave the entity with nobody able to manage members, and
   no way back without database access, because there is no self-registration.
   Now AC-0001-29.
8. **"Change own password" was a permission with no specification.** Removed
   from the matrix and recorded as out of scope, with the reason.

**v0.4 (2026-09-10)** — `/plan`'s persistence review found four defects in v0.3,
three of them in criteria I had just approved. Recorded here rather than fixed
quietly, because a spec that resolves its own contradiction without saying so has
made a decision nobody agreed to.

1. **AC-0001-02 was false.** The lockout was keyed on the account, so an unknown
   e-mail had no counter: six attempts told an attacker which addresses exist.
   The counter moved to the submitted address.
2. **AC-0001-03 stated two different rules** — "five within fifteen minutes" and
   "unlocked fifteen minutes after the last attempt" — and a stored counter with
   no timestamp expresses neither. Now explicitly an inactivity decay, with a
   criterion that proves it.
3. **The lockout was a denial-of-service against member management.** Anyone who
   knew the last gestor's address could deny it in fifteen-minute blocks. The
   lockout now applies to local login only; institutional OIDC is unaffected.
4. **§8 wrote an e-mail address into the audit table**, permanently, for a
   caller with no account to anonymise — contradicting `lgpd.md` outright.
   Replaced by a peppered HMAC plus the bare domain.

AC-0001-29 also grew to cover demotion of the last gestor and to state the
concurrency requirement, since it is a cross-row condition and therefore subject
to write skew.

**v0.5 (2026-09-10)** — two gaps the product owner found by reading the spec,
neither of which `/spec-review` or the persistence review had caught.

1. **There was no way to recover a forgotten password.** v0.3's scope line
   declared the token-e-mail reset in scope "by exception" and then never gave it
   a criterion; the same version cut "change own password" from the permission
   matrix and added AC-0001-28, which refuses inviting an address that already
   has an account in any status. The three together left a servidor with a
   forgotten local credential no path at all — not self-service, not a
   re-invite, only database access. Closed by AC-0001-30/-31/-32.
2. **Only one path was throttled.** AC-0001-03 protected login and nothing else,
   leaving ten endpoints open — among them the OIDC callback, which performs a
   network call to the entity's own identity provider on every request, and the
   invitation redemption, which runs bcrypt and is therefore cheap to send and
   expensive to serve. Closed by AC-0001-33 and ADR-0012.

Also settled here: **ADR-0011** resolves the RNF01/AC-0001-05 conflict rather
than leaving it for whoever writes the endpoint. The 300 ms budget never came
from a measurement, and lowering the bcrypt cost to meet it would have been a
security downgrade wearing the clothes of a performance fix. Credential
verification gets its own provisional 500 ms, to be replaced by a measured
figure before M5's load tests close.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF01–RF02, §6.2, mockup 9.2.3 |
| 0.2 | 2026-09-02 | OQ-09 reframed from the 17/08 meeting: Entra ID, not Gov.br. Candidate axes for RN07 scoping recorded from the data (unidade, grupo de materiais) |
| 0.3 | 2026-09-10 | ADR-0010 adopted: OIDC primary + local contingency, Gov.br cut. AC-19..24 added (PKCE/state/nonce, token verification, no JIT provisioning, perfil never from a claim, route-table completeness, local login switchable). All criteria converted to Given/When/Then; AC-15/16/17 split; AC-14 lost `cpf` (OQ-10 Assumed). Auth routes moved under `/api/v1`. RN07 moved to SPEC-0003 with the reason recorded. Audit substrate scoped into this slice, with AC-0001-27 proving RN06/RNF08. `/spec-review` added AC-0001-25/26 (invitation single-use, password policy), AC-0001-28 (duplicate and off-domain invites) and AC-0001-29 (the last active gestor cannot be locked out); "change own password" left the permission matrix as unspecified |
| 0.4 | 2026-09-10 | `/plan`'s persistence review corrected four defects: the lockout is keyed on the submitted address, not the account (AC-0001-02 was false as written); AC-0001-03 states an inactivity decay rather than two conflicting rules; the lockout no longer reaches institutional OIDC, closing a DoS on member management; and §8 stops writing e-mail addresses into the immutable audit table, using a peppered HMAC plus domain. AC-0001-29 extended to demotion and to the concurrency requirement |
| 0.5 | 2026-09-10 | Password reset specified at last (AC-0001-30/-31/-32): a forgotten local credential had no recovery path, because the scope line promised the flow without a criterion while AC-0001-28 blocked the only workaround. Rate limiting added across every auth route (AC-0001-33, ADR-0012), keyed on the source and independent of the per-address lockout, with a higher ceiling for institutional ranges because whole unidades share one NAT address. RNF01's conflict with AC-0001-05 settled by ADR-0011 instead of by lowering the bcrypt cost |
