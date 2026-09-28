---
id: SPEC-0010
title: Telas de acesso e gestão de membros
status: Draft
version: 0.2
owner: Isaac Kleimann Graper
satisfies: [RF01, RF02, RF18, RNF06, RNF14]
depends_on: [SPEC-0001]
milestone: M2
---

# SPEC-0010 — Telas de acesso e gestão de membros

## 1. Purpose

SPEC-0001 is implemented and nobody can use it, because nothing speaks to the
API. This spec adds the screens through which a servidor enters SIGI, and
through which a gestor brings members in, and out. It is also what the
acceptance gate in `definition-of-done.md` needs: SPEC-0001 is not done until
its owner has used it on a running system, and today that system has no screen.

## 2. Scope

**In scope** — the login page, both mechanisms (institutional OIDC and the
local contingency, ADR-0010); completing institutional login; the authenticated
shell; keeping a session alive and ending it; activating an invitation;
confirming a password reset; the member list and every member action SPEC-0001
serves.

**Out of scope**

- Screens for ATAs, insumos, NEs, NFs, saldo, estoque, reports and
  notifications. SPEC-0002 to SPEC-0009 are `Draft`, and a `Draft` spec may not
  be implemented. Each gets its screens with its own spec.
- Self-service password reset. AC-0001-30 is blocked on a mail transport, and
  its route is not served (OQ-31).
- Self-signup. Accounts exist only because a gestor invited them (SPEC-0001,
  invariant I3).
- Gov.br, cut by ADR-0010.
- "Lembrar sessão". The refresh lifetime is fixed server-side at 7 days; a
  checkbox that changes nothing would be a lie on the login page.
- Unblocking a member. RF18 asks for it, SPEC-0001 does not specify it, and the
  API does not serve it (OQ-34).

## 3. Domain model touched

None. This spec reads and changes state only through the SPEC-0001 API, and owns
no invariant of its own beyond these, which are about the client:

- **C1** — the access token lives only in the page's memory. It is never written
  to `localStorage`, `sessionStorage`, IndexedDB or a cookie script can read.
  The refresh token is the API's httpOnly cookie, and the page never sees it.
- **C2** — hiding a control is cosmetic. Every permission this spec describes
  is enforced by the API (invariant 8, SPEC-0001 §4.3); the screen only avoids
  offering what the API will refuse.
- **C3** — every message a servidor reads about a refusal is the API's
  `message`, shown verbatim. The screen never rewrites, translates or invents
  one, except for the single case the API cannot answer (§5).
- **C4** — a person is identified by `name` when the API returns one and by
  `email` otherwise. Today `name` is null for every account an invitation
  creates, because no route lets anyone set it (OQ-35); a screen that relies on
  it shows blanks.

**Deployment assumption.** The pages and the API share one origin: the frontend
serves `/api/v1` by forwarding it to the API. The refresh cookie
(`SameSite=Lax`, scoped by path) and the OIDC state cookie (scoped to
`/api/v1/auth/oidc`) only reach the API that way.

## 4. Behaviour

Every criterion is observable in the DOM, the URL, browser storage, or a request
the page makes. "Shows the message" means the API's `error.message`, verbatim
(C3).

### 4.1 Login

`/login` shows the institutional button when OIDC is enabled, and the local
form (e-mail, password with show/hide) when local login is enabled. Which
mechanisms are enabled is a frontend setting that mirrors the API's switches,
because no API route reports them (OQ-33).

**AC-0010-01** — Local login lands on the start page
```gherkin
Given an "ativo" usuario and local login enabled
When  they submit their e-mail and password on /login
Then  the browser is at "/"
And   the header identifies them as C4 describes, with their perfil
```

**AC-0010-02** — A refused local login shows the API's message
```gherkin
Given local login enabled
When  a login is submitted and the API answers "INVALID_CREDENTIALS"
Then  the page stays at /login and shows "E-mail ou senha inválidos."
And   the password field is empty and the e-mail field keeps its value
```

**AC-0010-03** — A locked-out address shows the API's message
```gherkin
Given an address the API has locked out
When  a login is submitted and the API answers 429 "ATTEMPTS_EXCEEDED"
Then  the page shows the message from that response
And   the submit button is disabled for the seconds in "Retry-After"
```

**AC-0010-04** — An inactive account shows the API's message
```gherkin
Given a usuario whose status is not "ativo"
When  a login is submitted and the API answers "USUARIO_INATIVO"
Then  the page shows "Esta conta não está ativa. Procure o gestor da sua unidade."
```

**AC-0010-05** — A disabled local login is not offered
```gherkin
Given local login disabled
When  /login is opened
Then  there is no password field on the page
And   the institutional button is the only way in
```

**AC-0010-06** — The institutional button starts the provider's flow
```gherkin
Given OIDC enabled
When  the institutional button is activated
Then  the browser navigates to "/api/v1/auth/oidc/authorize"
```

**AC-0010-07** — No self-service reset or signup is offered
```gherkin
Given any configuration
When  /login is opened
Then  it shows "Esqueceu a senha? Procure o gestor da sua unidade."
And   it contains no link to a signup or self-service reset page
And   opening "/signup" answers the not-found page
```

**AC-0010-08** — A submitting form cannot be submitted twice
```gherkin
Given a login in flight
When  the submit button is activated again
Then  no second login request is sent
And   the button reads "Entrando..."
```

### 4.2 Completing institutional login

The provider returns the browser to `/auth/callback`, the redirect URI the API
is configured with. That page completes the login by calling the API's callback
with the `code` and `state` it received.

**AC-0010-09** — A provisioned account lands on the start page
```gherkin
Given a provider return for an "ativo" usuario
When  /auth/callback loads with its "code" and "state"
Then  the browser is at "/"
And   "code" and "state" are no longer in the address bar
```

**AC-0010-10** — Each refusal shows its message and a way back
```gherkin
Given a provider return the API refuses with "USUARIO_NAO_PROVISIONADO",
      "INVALID_STATE" or "INVALID_ASSERTION"
When  /auth/callback loads
Then  the page shows the message from that response
And   a "Tentar novamente" link leads to /login
```

### 4.3 Session

**AC-0010-11** — A reload keeps the session
```gherkin
Given a signed-in usuario on any authenticated page
When  the page is reloaded
Then  the same page shows, still signed in, without visiting /login
```

**AC-0010-12** — An expired access token is renewed without the user noticing
```gherkin
Given a signed-in usuario whose access token has expired
When  they perform an action that calls the API and the API answers "TOKEN_EXPIRED"
Then  one refresh request is sent
And   the action is retried once and its result is shown
```

The API rotates the refresh token on every use and treats a second use of the
same token as a replay: it revokes the whole family and writes
`auth.refresh_replay` (AC-0001-07). A client that refreshes twice with one
token therefore logs its own user out and raises a false security signal.
AC-0010-46 and -47 exist because of that.

**AC-0010-13** — A dead session returns to login with the reason
```gherkin
Given a signed-in usuario whose refresh the API refuses with "INVALID_REFRESH"
When  any authenticated request needs a new access token
Then  the browser is at /login
And   it shows "Sua sessão não é mais válida. Entre novamente."
```

**AC-0010-14** — Logout ends the session and leaves nothing behind
```gherkin
Given a signed-in usuario
When  they choose "Sair" in the header menu
Then  a logout request is sent and the browser is at /login
And   pressing Back shows /login, not the page they left
```

**AC-0010-15** — A protected page asks for login and returns afterwards
```gherkin
Given no session
When  "/membros?page=2" is opened
Then  the browser is at /login
And   after a successful login it is at "/membros?page=2"
```

**AC-0010-16** — The return address cannot leave SIGI
```gherkin
Given no session
When  /login is opened with a return address that is absolute, protocol-relative
      ("//…") or not a path on this origin
Then  after a successful login the browser is at "/"
```

**AC-0010-17** — The access token is not in browser storage
```gherkin
Given a signed-in usuario
When  localStorage, sessionStorage, IndexedDB and document.cookie are read
Then  none of them contains the access token
```

### 4.4 Activating an invitation

The gestor hands the invited person a link to `/convite?token=…` (AC-0001-10).
The token stays a query parameter by decision (OQ-30); this page limits where it
travels next.

**AC-0010-18** — The token leaves the address bar as soon as it is read
```gherkin
Given an invitation link
When  /convite?token=… loads
Then  the address bar shows "/convite" without the token
And   the response carries "Referrer-Policy: no-referrer"
```

**AC-0010-19** — Activation opens a session
```gherkin
Given an unredeemed invitation
When  the invited person submits a password and its confirmation
Then  the browser is at "/"
And   the header shows their perfil
```

**AC-0010-20** — Mismatched confirmation is caught before the API
```gherkin
Given the activation form
When  the password and its confirmation differ
Then  the page shows "As senhas não conferem." and sends no request
```

**AC-0010-21** — A weak password keeps the invitation usable
```gherkin
Given an unredeemed invitation
When  a password the API refuses with "WEAK_PASSWORD" is submitted
Then  the page shows "A senha precisa ter ao menos 12 caracteres."
And   the form is still there, and a stronger password can be submitted
```

**AC-0010-22** — A spent or expired invitation says what to do
```gherkin
Given an invitation the API refuses with "INVITE_ALREADY_USED" or "INVITE_EXPIRED"
When  a password is submitted
Then  the page shows the message from that response
And   the form is no longer shown
```

**AC-0010-23** — A link without a token is explained
```gherkin
Given no "token" in the address
When  /convite is opened
Then  the page shows "Link de convite incompleto. Peça um novo ao gestor."
And   no form is shown
```

### 4.5 Confirming a password reset

**AC-0010-24** — The reset token leaves the address bar as soon as it is read
```gherkin
Given a reset link
When  /redefinir-senha?token=… loads
Then  the address bar shows "/redefinir-senha" without the token
And   the response carries "Referrer-Policy: no-referrer"
```

**AC-0010-25** — A confirmed reset returns to login, without a session
```gherkin
Given an unredeemed reset token
When  a new password and its confirmation are submitted
Then  the browser is at /login
And   it shows "Senha redefinida. Entre com a nova senha."
And   no session exists (AC-0001-31)
```

**AC-0010-26** — A spent or expired reset link says what to do
```gherkin
Given a reset token the API refuses with "RESET_ALREADY_USED" or "RESET_EXPIRED"
When  a password is submitted
Then  the page shows the message from that response
And   the form is no longer shown
```

`WEAK_PASSWORD`, a mismatched confirmation and a missing token behave as in
AC-0010-20, -21 and -23, with "Link de redefinição incompleto. Peça um novo ao
gestor." for the last.

### 4.6 The shell

**AC-0010-27** — The navigation offers only what exists
```gherkin
Given a signed-in usuario of any perfil
When  any authenticated page is shown
Then  the navigation lists exactly "Início", plus "Membros" for a gestor or an auditor
```

Nothing else is listed until another spec is `Approved` and adds its own entry.

**AC-0010-28** — The start page states who is signed in
```gherkin
Given a signed-in usuario
When  "/" is shown
Then  it shows their e-mail and perfil, and their name when the API returns one
```

### 4.7 Members

**AC-0010-29** — The gestor sees the member list
```gherkin
Given a signed-in gestor and at least one member
When  /membros is opened
Then  a table shows, per member, Nome, E-mail, Perfil, Status and Criado em
And   a null name shows "—" in the Nome cell
And   Criado em is formatted "dd/MM/yyyy" in America/Sao_Paulo
```

**AC-0010-30** — The list is paged by the API
```gherkin
Given more members than one page holds
When  the next page is chosen
Then  the request carries the next "page"
And   the address bar reflects it, so a reload keeps the page
```

**AC-0010-31** — A deactivated member shows the pseudonym
```gherkin
Given a member whose status is "desativado"
When  the list shows them
Then  the Nome cell shows their pseudonym and the E-mail cell shows "—"
```

**AC-0010-32** — The auditor reads without acting
```gherkin
Given a signed-in auditor
When  /membros is opened
Then  the member table shows
And   no invite, block, deactivate or reset control exists on the page
```

**AC-0010-33** — The servidor is told why, not shown an empty page
```gherkin
Given a signed-in servidor
When  /membros is opened directly
Then  the page shows "Seu perfil não permite esta ação."
And   no member data is shown
```

**AC-0010-34** — An empty list is stated
```gherkin
Given a page of the list with no members
When  it is shown
Then  the table shows a single row "Nenhum membro encontrado."
```

### 4.8 Member actions (gestor)

**AC-0010-35** — Inviting shows the link once
```gherkin
Given a signed-in gestor
When  they invite an institutional e-mail with a perfil
Then  a dialog shows the activation link with a "Copiar" button
And   it states "Este link não será mostrado de novo. Envie-o agora à pessoa convidada."
And   after the dialog closes, the list shows the new member as "pendente"
```

**AC-0010-36** — Invitation refusals appear in the dialog
```gherkin
Given the invite dialog
When  the API refuses with "EMAIL_ALREADY_REGISTERED" or "NON_INSTITUTIONAL_DOMAIN"
Then  the dialog stays open and shows the message from that response
```

**AC-0010-37** — Blocking asks first
```gherkin
Given a signed-in gestor and an "ativo" member
When  they choose "Bloquear" and confirm
Then  the member's status reads "bloqueado"
And   choosing "Cancelar" instead sends no request
```

**AC-0010-38** — Deactivating says it cannot be undone
```gherkin
Given a signed-in gestor and a member not "desativado"
When  they choose "Desativar"
Then  the confirmation states that name and e-mail will be erased and that
      this cannot be undone
And   after confirming, the member shows as in AC-0010-31
```

**AC-0010-39** — The last gestor is protected, and says so
```gherkin
Given the only active gestor
When  blocking or deactivating them is confirmed and the API answers "ULTIMO_GESTOR"
Then  the page shows the message from that response
And   the member's status is unchanged in the list
```

**AC-0010-40** — Triggering a reset shows the link once
```gherkin
Given a signed-in gestor and an "ativo" member
When  they choose "Redefinir senha" and confirm
Then  a dialog shows the reset link with a "Copiar" button
And   it states "Este link não será mostrado de novo e expira em 1 hora."
```

**AC-0010-41** — Actions do not apply to states that forbid them
```gherkin
Given a member whose status is "desativado"
When  their row is shown
Then  it offers no block, deactivate or reset control
```

### 4.9 Cross-cutting

**AC-0010-42** — An unanswerable failure shows a reference
```gherkin
Given any request that fails with a 5xx or no response
When  the page reports it
Then  it shows "Não foi possível concluir. Tente novamente em instantes."
And   if the response carried a correlation_id, it shows it as "Código: …"
```

**AC-0010-43** — Every page holds at three widths (RNF06)
```gherkin
Given each page in this spec
When  it is rendered at 360, 768 and 1440 px in Chromium, Firefox and WebKit
Then  nothing overflows the viewport horizontally except inside the member table
```

**AC-0010-44** — No serious accessibility violation (RNF14)
```gherkin
Given each page in this spec, in each of its states above
When  it is checked with axe-core
Then  there is no violation of impact "serious" or "critical"
```

**AC-0010-45** — Login and activation work from the keyboard alone (RNF14)
```gherkin
Given /login and /convite?token=…
When  each is completed using only Tab, Shift+Tab, Enter and Space
Then  the same outcome as AC-0010-01 and AC-0010-19 is reached
And   the focused element is visibly marked at every step
```

### 4.10 Added by the first review

**AC-0010-46** — Concurrent expired requests share one refresh
```gherkin
Given a signed-in usuario whose access token has expired
When  two requests fail with "TOKEN_EXPIRED" at the same time
Then  exactly one refresh request is sent
And   both requests are retried with the new token and succeed
```

**AC-0010-47** — Two tabs do not log each other out
```gherkin
Given a signed-in usuario with SIGI open in two tabs and an expired access token
When  both tabs are reloaded at the same moment
Then  both show the page signed in
And   no "auth.refresh_replay" row is written
```

**AC-0010-48** — A cancelled institutional login is explained
```gherkin
Given the provider returns to /auth/callback with "error" instead of "code"
When  the page loads
Then  it shows "A entrada institucional foi cancelada ou não foi autorizada. Tente novamente."
And   it sends no request to the API's callback
And   a "Tentar novamente" link leads to /login
```

**AC-0010-49** — A malformed field is marked where it is
```gherkin
Given the invite dialog
When  the API refuses with 422 "INVALID_DATA" and a "fields" entry for "email"
Then  that entry's message shows next to the e-mail field
And   the dialog stays open with the values entered
```

**AC-0010-50** — The per-source ceiling is explained
```gherkin
Given /login, /convite or /redefinir-senha
When  a submission is refused with 429 "RATE_LIMITED"
Then  the page shows "Muitas requisições. Tente novamente em instantes."
And   the form keeps its values, except any password field
```

**AC-0010-51** — A signed-in user is not shown the login page
```gherkin
Given a signed-in usuario
When  /login is opened
Then  the browser is at "/"
```

## 5. Errors and edge cases

No new API error codes. Every refusal these screens show is one of SPEC-0001 §5,
displayed verbatim (C3). The strings the screens own:

| Condition | Where | Message (pt-BR) |
| --- | --- | --- |
| 5xx, or no response | any | "Não foi possível concluir. Tente novamente em instantes." (+ "Código: {correlation_id}") |
| Confirmation differs | `/convite`, `/redefinir-senha` | "As senhas não conferem." |
| Invitation link without token | `/convite` | "Link de convite incompleto. Peça um novo ao gestor." |
| Reset link without token | `/redefinir-senha` | "Link de redefinição incompleto. Peça um novo ao gestor." |
| Reset confirmed | `/login` | "Senha redefinida. Entre com a nova senha." |
| Forgotten password | `/login` | "Esqueceu a senha? Procure o gestor da sua unidade." |
| Provider returned an error instead of a code | `/auth/callback` | "A entrada institucional foi cancelada ou não foi autorizada. Tente novamente." |

Two API refusals these screens handle are missing from SPEC-0001 §5 (OQ-37):
`INVALID_DATA` (422, with `fields` naming each bad field and its pt-BR message),
which the API returns for any malformed body; and `RATE_LIMITED` (429,
AC-0001-33), which is listed there but has no criterion on any screen until
this spec.

`USUARIO_INATIVO` on a request after login (the account was blocked
mid-session, AC-0001-08) ends the session as AC-0010-13 does, showing that
code's message instead.

## 6. Permissions

What each perfil is **shown**. SPEC-0001 §6 is what each is **allowed**, and the
API enforces it (C2).

| Screen element | gestor | servidor | auditor |
| --- | --- | --- | --- |
| "Membros" in the navigation | ✅ | ❌ | ✅ |
| Member table | ✅ | ❌ refusal message | ✅ |
| Invite, block, deactivate, trigger reset | ✅ | ❌ | ❌ |
| Start page, logout | ✅ | ✅ | ✅ |

`/login`, `/auth/callback`, `/convite` and `/redefinir-senha` need no session.
The last two are usable by whoever holds the link, which is what the link is
for; the API decides whether its token is still good. A signed-in usuario who
opens `/login` is sent to `/` (AC-0010-51).

## 7. Pages

The paths are pt-BR: the servidor reads them in the address bar and receives
two of them in a link (ADR-0013's reader test). `/auth/callback` is the
exception, because it is the API's configured OIDC redirect URI and no person
types or reads it.

| Page | Purpose | API routes called | AC |
| --- | --- | --- | --- |
| `/login` | Both login mechanisms | `POST /api/v1/auth/login`, `GET /api/v1/auth/oidc/authorize` | 01–08, 15, 16, 50, 51 |
| `/auth/callback` | Complete institutional login | `GET /api/v1/auth/oidc/callback` | 09, 10, 48 |
| `/` | Start page | `GET /api/v1/auth/me` | 27, 28 |
| `/convite` | Activate an invitation | `POST /api/v1/convites/ativar` | 18–23, 45, 50 |
| `/redefinir-senha` | Confirm a reset | `POST /api/v1/auth/redefinicoes/confirmar` | 24–26, 50 |
| `/membros` | List and manage members | `GET\|POST /api/v1/usuarios`, `POST /api/v1/usuarios/{id}/bloquear`, `…/desativar`, `…/redefinir-senha` | 29–41, 49 |
| every authenticated page | Session upkeep | `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` | 11–14, 17, 46, 47 |

## 8. Audit events

None new. Each action produces the SPEC-0001 §8 row of the API route it calls:
login `auth.login` or `auth.falha`, invite `usuario.convidado`, activation
`usuario.ativado`, block `usuario.bloqueado`, deactivation `usuario.desativado`,
triggered reset `usuario.redefinicao_disparada` as SPEC-0001 §8 names it,
confirmed reset `auth.redefinicao_concluida`. The screens never write an audit
row themselves.

*The API writes `usuario.redefinicao_solicitada` for the triggered reset, not the
name §8 gives, and `auth.redefinicao_solicitada` is the name §8 reserves for the
self-service request (OQ-37).*

## 9. Design

Taken from `docs/product/design-reference.md` (the Lovable prototype), which is
a style reference ranked below this spec:

- **Colour.** The green `primary` marks brand, primary actions and completion
  only; nothing "in progress" is green. Member status badges: `ativo` accent,
  `pendente` slate, `bloqueado` amber, `desativado` muted. Status never relies on
  colour alone; the badge text carries it.
- **Components and layout.** The reference's component set, icons and toasts;
  the split-screen login with the brand panel; the shell with a collapsible
  sidebar and a header holding the user menu; confirmation dialogs; the
  single-row empty state; monospace for links and codes.
- **Rejected**, with the rule that rejects it: the signup page and SIAPE
  (SPEC-0001 I3, `lgpd.md`); Gov.br (ADR-0010); "lembrar sessão" (§2); the
  separate admin credential gate and the per-module permission switches (C2,
  SPEC-0001 §6 fixes three perfis); every module screen (§2).

The libraries that implement this are named in the implementation plan, added
by `/plan` after approval.

## 10. Open questions

- **OQ-33 — which login mechanisms are enabled.** No API route reports it, so
  the frontend mirrors the API's two switches in its own configuration. If the
  two drift, the login page offers a mechanism that answers 404, or hides one
  that works. A public `GET /api/v1/auth/mecanismos` would remove the drift,
  but that is a SPEC-0001 change.
- **OQ-34 — unblocking a member.** RF18 says "block/unblock accounts".
  SPEC-0001 specifies only blocking, and the API serves no unblock route, so a
  blocked member can today be restored only by deactivating them, which
  anonymises the account, and inviting the address again, which
  `EMAIL_ALREADY_REGISTERED` refuses. A blocked member is therefore stuck. This
  spec shows no unblock control, because it would have no route behind it.
- **OQ-35 — nobody can set a member's name.** The invitation takes `email` and
  `perfil`, activation takes `password`, and no other route writes `nome`, so
  every invited account has none. C4 works around it. Proposal: an optional
  `name` on the invitation, in a SPEC-0001 revision.
- **OQ-36 — refresh across tabs.** AC-0010-47 is achievable in the browser, by
  letting one tab refresh while the others wait for its result. The alternative
  is a short grace window on the API, in which the token just rotated still
  answers once with the same new pair. That is a SPEC-0001 change, and it
  weakens replay detection by exactly that window. This spec assumes the
  browser-side answer.
- **OQ-37 — SPEC-0001 drift found while writing this spec.** `INVALID_DATA` is
  returned by the API and asserted by its tests, and appears in no spec or
  convention document. The triggered-reset audit row is written as
  `usuario.redefinicao_solicitada`; SPEC-0001 §8 calls it
  `usuario.redefinicao_disparada` and reserves `auth.redefinicao_solicitada` for
  AC-0001-30. Either the spec or the code moves; this spec does not decide which.
- **The 12-character password rule** is SPEC-0001's assumption; these screens
  show whatever the API refuses and hard-code no length.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-25 | First draft. Scope set by what SPEC-0001 serves; style from the Lovable design reference, with its signup, Gov.br, session checkbox and admin gate rejected against SPEC-0001 and ADR-0010. OQ-33 and OQ-34 opened. |
| 0.2 | 2026-09-25 | `/spec-review` of 0.1. C4: `name` is null for every invited account, so three criteria that showed it would have shown blanks. AC-0010-46/47: the API treats a second refresh with one token as a replay and revokes the family, so parallel requests or two tabs would log the user out and write false `auth.refresh_replay` rows. AC-0010-48 (provider returns an error), -49 (`INVALID_DATA`), -50 (`RATE_LIMITED`), -51 (signed-in user at /login). AC-0010-27 made observable. Unauthenticated pages added to §6. OQ-35, -36, -37 opened. |
