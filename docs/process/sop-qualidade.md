# Quality Gates — Standard Operating Procedure

> Where every rule in this repository is actually enforced, and by what. This
> document is normative.

A rule with no execution point is documentation, not a gate. This file exists to
say which of ours are which, because for most of this project's life the answer
was "none of them, unless somebody remembered".

It does **not** restate the rules. `definition-of-done.md` is the merge
checklist, `CONTRIBUTING.md` is the contribution contract, and
`CLAUDE.md` is the constitution. A fifth list of the same items would only
give the four existing ones a way to disagree with each other. What follows is
the wiring diagram.

## The map

| Rule | Stated in | Enforced by | Fires at |
| --- | --- | --- | --- |
| `ruff check` clean | definition-of-done | `pre-commit` hook · `backend-ci` | commit · PR |
| `ruff format` clean | definition-of-done | `pre-commit` hook · `backend-ci` | commit · PR |
| `mypy` clean over `app migrations tests` | definition-of-done | `pre-commit` hook · `backend-ci` | commit · PR |
| No CPF, SIAPE, token or real e-mail | CLAUDE.md · `security/lgpd.md` | `scripts/check_personal_data.py` · `gitleaks` | commit · PR |
| Commit message convention | CONTRIBUTING.md | `scripts/check_commit_msg.py` | commit |
| Coverage ≥ 70% (RNF10) | `requirements/non-functional.md` | `pre-push` hook · `backend-ci` | push · PR |
| Frontend lint, tests and build | — | `frontend-ci` | PR |
| **Tests run on real PostgreSQL** | CLAUDE.md | — **no database test exists yet** | never |
| **Models and schema agree (`alembic check`)** | definition-of-done | — **no migration exists yet** | never |
| **Audit trail is append-only (RN06)** | CLAUDE.md · ADR-0004 | — **the table does not exist yet** | never |
| **Every AC has a test that names it** | `requirements/traceability.md` | `/trace` — **run by a person** | never, unasked |
| **Spec is `Approved` before code** | CLAUDE.md | — **a reviewer, reading** | never |
| **A new dependency is justified in the spec's plan** | CLAUDE.md | — **a reviewer, reading** | never |
| **p95 under 300 ms (RNF01)** | `requirements/non-functional.md` | — **the k6 job does not exist yet** | never |

The rows in bold are the reason this document exists. They are real rules that
nothing executes, and writing them next to the ones that do is the only honest
way to describe the state of the project.

They are not all the same kind of nothing:

- **Two should stay human.** A reviewer deciding whether a spec is ready, or
  whether a new dependency is justified, is not automatable and should not be.
- **Two are debt with no excuse.** `/trace` exists and could run in CI; RNF01's
  performance job is named in `traceability.md` against a file nobody has
  written.
- **Three are waiting on code that does not exist yet.** There is no migration,
  no audit table and no database-backed test on this branch, so there is nothing
  for `alembic check`, the append-only trigger or testcontainers to be asserted
  against. They arrive with SPEC-0001, and the commit that brings them moves
  these rows up into the enforced half of the table.

The first draft of this file listed those last three as enforced, because they
are enforced on the branch the author had open. That is exactly the failure this
document is written against, caught by reading the table against the repository
instead of against memory — which is the check the closing section asks for.

## What runs when, and why there

**At commit** — ruff, ruff format, mypy, the personal-data scan, the commit
message. Seconds, no database, no network. These are the checks that must not
be deferred, because a lint error discovered in CI costs a round trip and a
personal-data leak discovered in CI is already in the history of every clone.

**At push** — the test suite with the coverage floor. It needs a real
PostgreSQL and takes around thirty seconds. That is too slow for a commit hook:
a gate people bypass protects nothing, and the bypass for a commit hook
(`--no-verify`) disables the personal-data scan along with it.

**At pull request** — everything above again, on a clean machine, plus
`gitleaks` over the full history and the frontend pipeline. CI is not a
duplicate of the hooks; it is the half that runs on code arriving from
someone else's machine, where no hook was installed.

Every pull request, not only the ones aimed at `dev` and `main`. The workflows
used to filter `pull_request` by branch, and that filter matches the **target**,
so a PR opened against another feature branch — one link of a stacked series —
ran nothing at all and reached its reviewer with no recorded result. The row
above promising `PR` was false for exactly the PRs that most needed it.

## Bootstrap

Once per machine:

```bash
pipx install poetry==2.3.3
```

Once per clone:

```bash
cd backend
poetry env use python3.12      # only if `python3` is not already 3.12
poetry sync --all-groups       # creates backend/.venv, installs main + dev
poetry run pre-commit install --install-hooks \
    --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Two details in that last command are load-bearing.

`poetry run pre-commit`, rather than a globally installed one: `pre-commit
install` writes the absolute path of the interpreter it was run from into each
generated hook. Running it through Poetry burns in `backend/.venv/bin/python`,
so the hooks also fire from editors and GUI git clients, which never source a
shell profile.

The three `--hook-type` flags: without them only `.git/hooks/pre-commit` is
written, and the commit-message and push hooks silently never fire — which is
the worst outcome available, because it looks installed.

Backend tests need a PostgreSQL. Either export `TEST_DATABASE_URL_ADMIN`
pointing at a running server, or leave it unset and let `testcontainers` start
`postgres:16`, which needs Docker. Export it from a **login** profile rather
than `.bashrc`, or the push hook will not see it when git is launched from a
GUI.

## When a gate refuses

Read what it says first. Every one of these hooks prints the rule it applied
and an example of what it wanted.

| Gate | Usual cause | What to do |
| --- | --- | --- |
| `ruff check` | a real finding | fix it; `--fix` already ran and left what it could not decide |
| `ruff format` | formatting drifted | the hook rewrote the files — `git add` them and commit again |
| `mypy` | a type is wrong, or a `Session` is untyped | fix it; do not add `# type: ignore` without a comment saying why |
| personal data | a real value got pasted in | replace it with a synthetic one; if the finding is wrong, put `sigi: dado-pessoal-ok` on that line |
| commit message | missing `[SPEC-XXXX]`, or a type outside the list | fix the message; if the type list is genuinely short, change `CONTRIBUTING.md` first and the script second |
| `pytest` at push | a real failure, or no database | fix it, or start the database — a failure here is a failure in CI ten minutes later |

**Never `git commit --no-verify` and never `git push --no-verify`.** It
disables every hook at once, including the personal-data scan, which is the one
whose damage cannot be undone by a follow-up commit. To skip a single hook, name
it:

```bash
SKIP=pytest git push          # the legitimate escape hatch
```

That is for the case where the suite cannot run at all — no Docker, no
PostgreSQL — and never for the case where it runs and fails. CI will run it
regardless, so skipping it locally buys a few minutes and costs a red pipeline.

## Keeping this document true

The table above is a claim about what executes. It decays the moment a hook is
added and the row is not, which is exactly how the four existing lists came to
disagree. So:

- A change to `.pre-commit-config.yaml` or `.github/workflows/` changes this
  table in the same commit.
- A rule that gains an execution point moves out of the "never" rows, and the
  commit says so.
- A rule that has no execution point stays in the table, in the "never" rows.
  Deleting it because it is unenforced is how a requirement quietly stops
  being one.
