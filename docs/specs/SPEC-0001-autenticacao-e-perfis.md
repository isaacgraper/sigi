---
id: SPEC-0001
title: Autenticação, perfis e gestão de membros
status: Draft
version: 0.2
owner: Isaac Kleimann Graper
satisfies: [RF01, RF02, RF18, RN01, RN04, RN07]
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

**In scope** — institutional login, JWT issuance and refresh, session
invalidation, three profiles, member management (invite, activate, block,
deactivate), server-side authorisation dependency.
**Out of scope** — Gov.br OAuth (M4, see §9), SSO with the entity's directory,
password self-service reset beyond a token e-mail.

## 3. Behaviour

**AC-0001-01** — Login with valid institutional credentials returns an access
token expiring in 15 minutes and sets a refresh token as an httpOnly, Secure,
SameSite=Lax cookie valid 7 days (RNF03).

**AC-0001-02** — Login with a wrong password returns 401 with a message that does
not reveal whether the e-mail exists.

**AC-0001-03** — After 5 failed attempts for one account within 15 minutes,
further attempts return 429 for 15 minutes, and the lockout is audited.

**AC-0001-04** — Only e-mails on the configured institutional domain allowlist
(e.g. `*.gov.br`) may authenticate; others return 401.

**AC-0001-05** — Passwords are stored with bcrypt cost 12; the hash never appears
in any API response, log line or error.

**AC-0001-06** — An expired access token returns 401 with code `TOKEN_EXPIRADO`;
the refresh endpoint issues a new pair without re-authentication.

**AC-0001-07** — Logout invalidates the refresh token server-side; a replayed
refresh token returns 401 and is audited as a possible token-theft signal.

**AC-0001-08** — A user whose `ativo` is false cannot authenticate **and** cannot
use an already-issued, unexpired access token (RN01). The active check runs on
every request, not only at login. Deactivation that only takes effect in 15
minutes is not deactivation.

**AC-0001-09** — JWTs are signed RS256; a token signed with a different key, or
with `alg: none`, is rejected.

**AC-0001-10** — A gestor invites a member by e-mail and profile; the account is
created with status `pendente` and no password.

**AC-0001-11** — An invited user activating via a single-use token valid 72 hours
sets a password and becomes `ativo`.

**AC-0001-12** — A gestor blocks an account; the user is immediately unable to
authenticate or use existing tokens, and the block is audited with the actor.

**AC-0001-13** — A servidor or auditor attempting any member-management operation
receives 403.

**AC-0001-14** — Deactivating a user anonymises `nome`, `email` and `cpf` while
preserving every `HISTORICO_MOVIMENTACAO` row referencing their `usuario_id`
(RN16, LGPD art. 16, I). Audit rows show a stable pseudonym, never a dangling FK.

**AC-0001-15..17** — For each of the three profiles, every write endpoint in the
system is exercised and returns 403 where the permission matrix says it should.
This is a generated test that enumerates the route table; adding an endpoint
without a permission entry fails the build.

**AC-0001-18** — A 403 is recorded in the audit trail with the attempted route,
the actor and the timestamp (RFC §3.2).

## 4. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Invite / activate / block / deactivate members | ✅ | ❌ | ❌ |
| Change own password | ✅ | ✅ | ✅ |
| View member list | ✅ | ❌ | ✅ read-only |

## 5. API surface

`POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`,
`GET /auth/me`, `GET|POST /api/v1/usuarios`,
`POST /api/v1/usuarios/{id}/bloquear`, `POST /api/v1/usuarios/{id}/desativar`,
`POST /api/v1/convites/{token}/ativar`.

## 6. Open questions

- **OQ-04 — RN07 is not implementable.** "Servidores só podem visualizar insumos
  da sua área de competência" requires an area/setor attribute that exists on
  neither `USUARIO` nor `INSUMO`. Until the entity defines what a "área de
  competência" is, this spec implements profile-based RBAC only, and RN07 stays
  unenforced. This must be resolved before any claim of least-privilege access.
- **OQ-09 — Gov.br OAuth** requires entity-level registration with the federal
  portal, a process outside the team's control. Login by institutional
  credentials is the MVP path; Gov.br is additive in M4 and must not block M2.
- The mockup shows CPF and SIAPE on the profile screen; neither is in the data
  model, and CPF is personal data under LGPD requiring a legal basis entry. See OQ-10.

## Revision 2026-09-02 — the authentication question was the wrong one

OQ-09 asked *when* the entity would register with Gov.br. The 17/08 meeting
shows the premise is wrong: **Gov.br was never mentioned**. Servidores already
hold credentials provisioned by the entity's own TI, and the discussion was
about **Microsoft Entra ID** — *"É uma Entra, né?"*, answered *"Dá pra colocar.
É possível."*

This matters beyond a vendor name. Gov.br is citizen-to-state federation; SIGI's
users are internal servidores who already have an institutional identity. Keeping
Gov.br in the spec promises an integration nobody asked for while omitting the
one actually discussed, and its M4 lead-time risk is imaginary.

Proposal, pending confirmation with the entity's TI: **OIDC against Entra ID as
the primary mechanism**, local credentials retained only as contingency, Gov.br
dropped from scope. RF01's text ("institutional credentials or Gov.br") is
frozen RFC wording and is not edited; the divergence is recorded in
`functional.md`'s notes column and in OQ-09.

Note also that RN07's "área de competência" (OQ-04, still open) now has a
candidate shape from the data: every stock and fulfilment row is keyed by
`unidadeId`, and compradores are organised by **grupo de materiais**. Those are
the two axes the operation actually uses. See OQ-26.

## 7. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF01–RF02, §6.2, mockup 9.2.3 |
| 0.2 | 2026-09-02 | OQ-09 reframed from the 17/08 meeting: Entra ID, not Gov.br. Candidate axes for RN07 scoping recorded from the data (unidade, grupo de materiais) |
