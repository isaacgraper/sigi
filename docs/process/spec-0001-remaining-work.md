# SPEC-0001 — remaining work, branch by branch

Handoff note. `dev` is at the merge of #21. SPEC-0001 is v0.6, `Approved`.

## What is already done

AC-0001-01 to 09, 24 and 27: local login, refresh rotation, logout, `/me`,
per-address lockout, the audit writer, RS256 sessions. Plus the DB-level
guarantees for 10, 12, 14, 25 and 29, which live in `0001_baseline` triggers and
are covered by `test_migration_baseline.py`.

## What is left

| Order | Branch | ACs | Prior work to cherry pick |
| --- | --- | --- | --- |
| 0 | `add/english-internal-names` | none | — |
| 1 | `add/permission-matrix` | 15, 16, 17, 18, 23 | `aeb74d3` |
| 2 | `add/member-invitations` | 10, 11, 13, 26, 28 | `e7e15e3` + `91f8ca4` |
| 3 | `add/institutional-oidc` | 19, 20, 21, 22 | `bb3e8b7` |
| 4 | `add/password-reset` | 30, 31, 32 | nothing written |
| 5 | `add/rate-limiting` | 33 | nothing written |

Prior commits live on `origin/add/authentication-spec-0001`. They predate the
English rename and the API rename, so expect to translate as you port. Ignore
`d873629` on that branch, it is a superseded translation pass.

**Each branch is cut fresh from the current `origin/dev`, never stacked.** The
five branches with these names that already exist locally are 8+ commits behind;
delete and recreate them.

### Why this order

Matrix first because invitations are gestor-only routes that need it. Rate
limiting last because AC-0001-33 wraps every auth route, so it conflicts with
anything still in flight.

Branch 0 is optional but cheaper now than later: it renames `usuario_id` to
`user_id` (57 sites in `app/`) and the last Portuguese Python names. Every
feature branch after it inherits correct names instead of adding more to fix.

## Conventions

- Commit and PR title: `feat: include the permission matrix [SPEC-0001]`. No
  module scope, no dashes in prose.
- English: code, folders, filenames, comments, docstrings, JSON fields, error
  codes, route paths, branches, commits. Portuguese: the database schema and
  glossary nouns. pt-BR: every string a servidor reads. See ADR-0013.
- A name built on a glossary noun stays whole Portuguese (`USUARIO_INATIVO`,
  `/usuarios/{id}/bloquear`); one without becomes English (`INVITE_EXPIRED`).
- 200 to 600 lines per branch. Split if larger.
- Change the spec first, then the code, in the same commit.
- Every test names the AC it verifies.
- **Never merge.** Open the PR, request `PauloVomScheidt` and `theisgui`, stop.

## Commands

```bash
su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/sigi-dev \
  -o '-p 55432' -l /tmp/pg-sigi.log -w start"

cd backend
poetry run ruff check . && poetry run ruff format --check .
poetry run mypy app migrations tests
TEST_DATABASE_URL_ADMIN="host=127.0.0.1 port=55432 user=sigi dbname=postgres" \
  poetry run pytest -q
```

Export `TEST_DATABASE_URL_ADMIN` on `git push` too, or the pre-push hook falls
back to testcontainers and fails with no Docker. Push with
`git push -u origin HEAD`; `--force` and pushing to `dev`/`main` are denied.

## Traps

- `test_migration_baseline.py` and `test_audit_immutability.py` hold raw SQL in
  plain psycopg strings, not `text(...)`, so nothing syntactic marks them as
  SQL. Never run a pattern rename across `backend/tests/`.
- Renaming an ORM attribute renames its column unless you pass the name
  explicitly: `mapped_column("usuario_id", ...)`. Precedent at
  `app/models/user.py:39`.
- `alembic check` runs inside the suite. If it fails, a model drifted from the
  schema; fix the model, do not autogenerate a migration.
- Error codes for branches 2 to 5 are already renamed in SPEC-0001 §5
  (`INVITE_*`, `RESET_*`, `WEAK_PASSWORD`, `RATE_LIMITED`,
  `EMAIL_ALREADY_REGISTERED`, `NON_INSTITUTIONAL_DOMAIN`, `INVALID_STATE`).
  Use those spellings; do not invent Portuguese ones.
- `e7e15e3` carries a spec bump it calls v0.6. That number is taken. The
  invitations branch bumps to v0.7 and keeps the substance of that change
  (the gestor delivers the invitation, not the system).
- Services raise typed domain exceptions; only `api/` maps them to HTTP. Never
  raise `HTTPException` from a service.
- Every write endpoint writes its `historico_movimentacao` row in the caller's
  transaction. A failed audit write fails the request.

## Two open questions to settle in branch 2

Neither is in `docs/open-questions.md` yet; add them as OQ-30 and OQ-31.

1. SPEC-0001 puts the invitation and reset tokens in the URL path
   (`/convites/{token}/ativar`). Paths land in access logs, proxies and browser
   history. Moving them to the request body costs nothing now and cannot be
   undone later. Recommend the body.
2. `historico_movimentacao` has seven yearly partitions, to 2032. Nothing
   creates the eighth. Decide who runs `criar_particao_historico` and when.
