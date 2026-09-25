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

[Conventional Commits](https://www.conventionalcommits.org/) without a module
scope, with the spec referenced:

```
feat: include local login [SPEC-0001]
fix: correct orphaned NF binding [SPEC-0005]
chore: add frontend lint workflow
docs: record CSV import decision
```

Accepted types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`.

**Atomic commits.** One logical change per commit, never a squash of several.
A spec fix, a new spec, new open questions and the traceability rows that follow
are four commits, not one.

**Short messages.** The subject says what the commit does. A body, when needed,
says why in a few lines. No dashes used as punctuation.

## Pull request descriptions

A PR description is read twice: by the reviewer now, and by whoever audits how a
change reached production later. Write it for the second reader.

Three parts, and nothing else:

**1. Description — one or two sentences, no heading.** What the PR does.

**2. `## Key Changes`** — one line per change. No sub-grouping, no prose.

**3. `## Technical Details`** — what a reviewer cannot read off the diff: why an
approach was chosen over the alternative, what was measured, what broke during
implementation and how. Short bullets.

Keep it dry. No summaries of the summary, no restating the diff in prose, no
closing paragraph that repeats the opening one.

- **No questions, and nothing addressed to the reader.** The description states
  what was done. An open decision goes in `docs/open-questions.md`, and the PR
  only references its ID.
- **No signature.** No generated-by footer, no session link.

### Worked example

```markdown
Replaces uv with Poetry and adds pre-commit hooks.

## Key Changes

- Backend dependency management moves from uv to Poetry
- Ruff gains the `W` and `D` rules; the 24 resulting violations are fixed
- `gitleaks` added as a CI job

## Technical Details

- `package-mode = false` replaces `[build-system]`: no wheel is ever built.
- Hooks are `repo: local`, so ruff and mypy come from `poetry.lock`.
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
