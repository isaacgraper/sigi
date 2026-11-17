---
id: SPEC-0019
title: Implantação contínua na VPS
status: Draft
version: 0.1
owner: Isaac Kleimmann Graper
satisfies: [RNF09]
depends_on: []
milestone: M5
---

# SPEC-0019 — Implantação contínua na VPS

## 1. Purpose

Put every released version on the VPS without anyone logging into it. Today a
release ends when the release PR from `dev` is merged into `main`
(`docs/process/branching-and-releases.md`), and the VPS is then updated by hand
with the commands in `docs/process/deploy-vps.md`. The product owner, on
2026-11-17, asked that the merge into `main` deploy the VPS by itself.

The deploy runs the same steps the manual procedure runs, in the same order, on
the same stack: the production compose file, its environment file, the
migrations as the owner role and the existing database volume. It adds a health
check at the end, so that a run that finished is a run whose application
answers.

## 2. Scope

**In scope**
- A deploy started by every push to `main`, and by nothing else.
- Bringing the VPS checkout to exactly the commit that was pushed.
- Rebuilding and restarting the production stack, then applying migrations.
- Checking that the API answers once the stack is up.
- Removing dangling images after a successful deploy.
- The credentials the run needs, kept as repository secrets, never in the tree.

**Out of scope**
- Running the tests again. `main` only takes a release PR with green checks
  (`branching-and-releases.md`, rule 4); the deploy trusts that gate.
- Automatic rollback. A failed run leaves the stack as the failing step left it
  and the run red; recovery is manual (§4.4).
- Deploying `dev`. The VPS may still be pointed at `dev` by hand for a demo;
  this spec does not automate that (OQ-57).
- Database backups before migrating (OQ-58), TLS and a domain (RNF04, the
  Caddyfile's own note), monitoring (RNF02).
- Creating the first gestor, `.env.prod` or the daily `notificar` cron. They are
  one-off steps of `deploy-vps.md` and stay there.

## 3. Domain model touched

None. No entity, table or column changes. The deploy applies whatever
migrations the released commit carries; it creates none.

The invariants it must not weaken:

- **Two database roles** (CLAUDE.md, ADR-0004). Migrations run as the owner
  inside the backend container, through the owner URL already in the production
  compose file. The application keeps connecting as the restricted role.
- **The database volume survives.** No step removes `postgres_data`,
  `caddy_data` or `mail_data`.
- **No secret enters the repository.** The VPS address, user and key live only
  in the repository's secrets; `.env.prod` lives only on the VPS.

## 4. Behaviour

### 4.1 Trigger

**AC-0019-01** — A push to `main` starts a deploy
```gherkin
Given the release PR from dev into main is merged
When  GitHub records the push to main
Then  one run of the deploy workflow starts for that commit
```

**AC-0019-02** — Nothing else starts a deploy
```gherkin
Given a push to dev, to a working branch, or a pull request on any branch
When  GitHub records it
Then  no run of the deploy workflow starts
```

**AC-0019-03** — One deploy at a time
```gherkin
Given a deploy run in progress
When  a second push to main starts another run
Then  the second waits until the first ends
And   the first is not cancelled
```

**AC-0019-04** — Least privilege
```gherkin
Given the deploy workflow
Then  its token may only read the repository's contents
```

### 4.2 Reaching the VPS

**AC-0019-05** — Credentials come from secrets
```gherkin
Given the deploy workflow file in the repository
Then  it holds no host address, no user name, no key and no host fingerprint
And   it reads each of them from a repository secret
```

**AC-0019-06** — The host is verified
```gherkin
Given the VPS's SSH host key fingerprint stored as a secret
When  the run connects and the host presents a different key
Then  the connection is refused
And   no command runs on the VPS
And   the run fails
```

**AC-0019-07** — Missing secret
```gherkin
Given one of the deploy secrets is not set
When  a deploy run starts
Then  the run fails before connecting, naming the missing secret in its log
```

### 4.3 Deploying

Each step below runs only if the one before it succeeded, and any failure ends
the run red.

**AC-0019-08** — The checkout is the pushed commit
```gherkin
Given the VPS checkout on main, with no local changes
When  the run updates it
Then  the checkout's HEAD is the commit that started the run
```

**AC-0019-09** — A checkout that diverged is not overwritten
```gherkin
Given the VPS checkout has local commits or modified tracked files
When  the run updates it
Then  the update is refused without discarding them
And   the stack is not rebuilt
And   the run fails
```

**AC-0019-10** — A VPS left on dev moves to main
```gherkin
Given the VPS checkout on dev, with no local changes
When  the run updates it
Then  the checkout is on main at the commit that started the run
```

**AC-0019-11** — The production stack is rebuilt
```gherkin
Given the checkout at the pushed commit
When  the run rebuilds the stack
Then  it uses the production compose file and the VPS's .env.prod
And   db, backend, frontend and caddy are running
And   the postgres_data volume is the one that existed before the run
```

**AC-0019-12** — Missing .env.prod
```gherkin
Given the VPS has no .env.prod
When  the run rebuilds the stack
Then  the rebuild fails without starting any service with default secrets
And   the run fails
```

**AC-0019-13** — Migrations as the owner
```gherkin
Given the stack is up
When  the run applies migrations
Then  the database is at the released commit's Alembic head
And   they ran through the owner connection, not the application role
```

**AC-0019-14** — A failed migration stops the run
```gherkin
Given a migration of the released commit fails
When  the run applies migrations
Then  the run fails at that step
And   no later step runs
```

**AC-0019-15** — The application answers
```gherkin
Given migrations applied
When  the run checks the API's health route from inside the stack
Then  it answers 200 with status "ok" within 60 seconds
```

**AC-0019-16** — The application does not answer
```gherkin
Given migrations applied
When  the API's health route does not answer 200 within 60 seconds
Then  the run fails
And   its log holds the last lines of the backend's own log
```

**AC-0019-17** — Images are pruned after success
```gherkin
Given the health check passed
When  the run finishes
Then  dangling images are removed
And   no volume, container or network in use is removed
```

**AC-0019-18** — The run names what it deployed
```gherkin
Given a finished run, green or red
Then  its log shows the commit deployed and, if the commit is tagged, the tag
```

### 4.4 Recovery (manual, not automated)

A red run is the alarm; GitHub notifies the person who merged. Recovery stays
the documented manual procedure: on the VPS, check out the previous tag and
rebuild (`deploy-vps.md`, "To pin a version"). A migration is never reverted
by the deploy: `alembic downgrade` is denied by design, and a release whose
migration cannot be undone is a `MAJOR` (`branching-and-releases.md`).

## 5. Errors and edge cases

The deploy has no HTTP surface and no pt-BR copy. Its failures are a red run
with the reason in the log.

| Condition | Step that fails | AC |
| --- | --- | --- |
| A secret is missing | Before connecting | AC-0019-07 |
| The host key does not match | Connecting | AC-0019-06 |
| The VPS checkout diverged | Updating the checkout | AC-0019-09 |
| `.env.prod` missing or incomplete | Rebuilding | AC-0019-12 |
| A migration fails | Migrating | AC-0019-14 |
| The API does not answer in 60 s | Health check | AC-0019-16 |
| A second push to `main` mid-deploy | Waits, does not fail | AC-0019-03 |

## 6. Permissions

The application's perfis (gestor, servidor, auditor) take no part. Who may
deploy is who may merge into `main`, which branch protection already decides.

| Action | Who |
| --- | --- |
| Start a deploy | Anyone whose merge into `main` branch protection allows |
| Set or rotate the deploy secrets | A repository administrator |
| Log into the VPS as the deploy user | The holder of the deploy key: the workflow only |

## 7. API surface

None. The health route the check calls already exists (RNF09).

## 8. Audit events

None in `HISTORICO_MOVIMENTACAO`: the deploy mutates no application data. The
record of who deployed what and when is the GitHub Actions run, linked to the
push and the release PR, which `branching-and-releases.md` already treats as
the audit record of a version.

## 9. Open questions

- **OQ-57** — Does the VPS keep running `dev` for demos, or only `main` once
  this is in place? Blocks nothing here; AC-0019-10 moves it to `main` on the
  first release.
- **OQ-58** — Must the deploy dump the database before migrating? Blocks
  nothing here; RNF11 covers backups separately.
- **OQ-59** — The checkout path and user on the VPS: `deploy-vps.md` says
  `~/sigi` and its cron says `/root/sigi`. Blocks the plan, not the criteria.
- **OQ-60** — No RF or RNF asks for automated deployment; RNF09 is the nearest.
  The product owner's request of 2026-11-17 is the source.

## 10. Implementation plan

_Filled by `/plan`. Empty until the spec is Approved._

- Migration:
- Modules:
- Tests:

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-17 | Initial draft, on the product owner's request of 2026-11-17 to deploy the VPS on every merge into `main` |
