# Contributing to SIGI

SIGI is a government system. The repository history is part of the project's
accountability record: every change that reaches production must be traceable to
a reviewed Pull Request. The workflow below is not optional.

Domain vocabulary stays in Portuguese everywhere — `ATA`, `Nota de Empenho` (NE),
`Nota Fiscal` (NF), `empenho`, `saldo`, `insumo`, `fornecedor`, `vigência`,
`aditivo`, `reajuste`, `Processo SEI`. See `docs/product/glossary.md`.

## Branches

| Branch      | Role                                                            |
| ----------- | --------------------------------------------------------------- |
| `main`      | Release only. Protected. Advances exclusively via a release PR.  |
| `dev`       | Integration branch. All work merges here first.                  |
| `add/*`     | New functionality. Branched from `dev`.                          |
| `fix/*`     | Bug fix. Branched from `dev`.                                    |
| `chore/*`   | Tooling, docs, CI, dependencies. Branched from `dev`.            |
| `hotfix/*`  | Urgent production fix. Branched from `main`.                     |

Name the branch after **the work**, and reference the spec when there is one:
`add/authentication-spec-0001`, `fix/nf-orfa-spec-0005`, `chore/poetry-pre-commit-sop`.

**A branch never carries the name of a person or of a tool.** Not `claude/…`,
not `isaac/…`. A branch is a unit of work, and whoever picks it up next should
be able to tell what it does from its name — a repository where branches are
named after who happened to open them stops being readable the moment two people
work on the same area, and it reads as authorship in an accountability record
where the authorship that counts is the commit trailer and the PR.

**Never push directly to `main` or `dev`.** Both are protected and require a PR.

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

The hooks are not optional and not a convenience: they are where `ruff`, `mypy`,
the commit convention and the ban on committing personal data are actually
enforced. Skipping the install means finding all four in CI instead, on somebody
else's time.

Run `poetry run pre-commit run --all-files` to check the whole tree at once.
`docs/process/sop-qualidade.md` says which gate fires when, and what to do when
one refuses.

## Workflow

```bash
# 1. Always start from an up-to-date dev
git checkout dev
git pull origin dev

# 2. Create your branch
git checkout -b add/cadastro-de-ata-spec-0002

# 3. Work and commit
git commit -m "feat(ata): add registration endpoint [SPEC-0002]"

# 4. Publish and open the PR
git push -u origin add/cadastro-de-ata-spec-0002
```

The Pull Request **always** targets `dev` — never `main`.

## Before writing code

This repository follows spec-driven development. No production code is written
without a spec that has a stable ID. Read
[`docs/process/sdd-workflow.md`](docs/process/sdd-workflow.md) before your first
PR, and check the [definition of done](docs/process/definition-of-done.md).

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/), with the spec
referenced:

```
feat(ne): validate saldo before pré-empenho [SPEC-0004]
fix(nf): correct orphaned NF binding [SPEC-0005]
chore(ci): add frontend lint workflow
docs(adr): record CSV import decision
```

Accepted types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`.

## Pull request descriptions

A PR description is read twice: once by the reviewer, and again months later by
whoever is auditing how a change reached production. Write it for the second
reader.

The template in `.github/pull_request_template.md` is applied automatically.
It has four parts:

**1. Summary — prose, no heading.** Open with what the PR establishes, in
present tense. Two or three sentences, in business terms, not a restatement of
the diff.

**2. `### Changes`** — grouped by area, with the area in bold and its changes as
nested bullets. Bullets start with a past-tense verb: *Scaffolded*, *Configured*,
*Integrated*, *Added*, *Removed*.

**3. `### Why / Motivation`** — why this change, and why now. Reference the spec
when there is one. This is the section the auditor reads.

**4. `### How to Test`** — numbered steps a reviewer can actually follow, each
naming the area in bold and stating the observable result that means it passed.
"Run the tests" is not a step; "hit `/health` and verify a `200 OK`" is.

### Worked example

```markdown
Establishes the foundational architecture and configuration for the project
repository. It scaffolds a Next.js frontend with modern testing tools, sets up a
FastAPI backend with database migration and containerization support, and
incorporates initial documentation and development tooling configurations.

### Changes
* **Backend Setup**
  * Scaffolded FastAPI application structure including an initial health check endpoint
  * Configured Alembic for database schema migrations and Docker for containerized deployment
* **Frontend Setup**
  * Scaffolded Next.js client-side architecture
  * Integrated Vitest for unit testing and Playwright for end-to-end test execution

### Why / Motivation
To lay down the project's boilerplate structure, developer environment
configuration, and testing foundation before initiating core feature development.

### How to Test
1. **Backend:** Spin up the backend via Docker or local python environment, run
   Alembic migrations, and hit the `/health` endpoint to verify a `200 OK` response.
2. **Frontend:** Run the Next.js development server to verify the template builds
   correctly, and run Vitest/Playwright test suites to confirm the testing pipeline works.
```

### What a PR is expected to satisfy

Not a checklist to paste — these are the conditions a reviewer will hold the PR
to, and they are enforced by review and CI rather than by ticking boxes:

- The branch came from `dev` and the PR targets `dev`.
- The referenced spec is approved, not `Draft`.
- Every acceptance criterion the change touches has a corresponding test.
- Backend coverage stays at 70% or above (RNF10).
- Writes record a `HISTORICO_MOVIMENTACAO` row in the same transaction (RN06).
- `CHANGELOG.md` has an entry under `[Unreleased]`.
- No real CPF, SIAPE number, e-mail or token is committed.
- CI is green.

## Releases

Releases are a deliberate event: a single `dev` → `main` PR aggregating every PR
merged since the previous version. The full process is in
[`docs/process/branching-and-releases.md`](docs/process/branching-and-releases.md).
