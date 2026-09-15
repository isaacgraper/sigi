# Branching and Releases

> How code leaves the editor and reaches production. This document is normative.

SIGI serves a state government entity. A change in production must be auditable:
who wrote it, who reviewed it, when it landed, and in which version. The model
below exists to guarantee that.

Domain vocabulary stays in Portuguese — `ATA`, `NE`, `NF`, `empenho`, `saldo`.

## Branch model

```
add/*  fix/*  chore/*
        \    |    /
         \   |   /          PR + CI  (continuous review)
          v  v  v
            dev             integration — always green, always deployable
             |
             |              release PR  (deliberate event)
             v
            main            release only — every commit is a tagged version
             |
             v
          tag vX.Y.Z + GitHub Release
```

### `main`

- Contains released code only. Every commit on `main` corresponds to a version.
- Protected: requires a PR, requires green checks, rejects force-push and deletion.
- Advances **exclusively** through a release PR from `dev` (or a `hotfix/*`, see
  below). Never through a direct commit, never through an isolated feature merge.

### `dev`

- Integration branch. The default target of every Pull Request.
- Must stay green and deployable to staging at all times.
- Protected: requires a PR and green checks.

### Working branches

Created from `dev`, named by type:

- `add/<short-description>` — new functionality. Never a person's or a
  tool's name: not `claude/…`, not `isaac/…`. See `CONTRIBUTING.md`.
- `fix/<short-description>` — bug fix
- `chore/<short-description>` — tooling, CI, dependencies, documentation

Keep them short-lived: the smaller the PR, the more effective the review. A
working branch that survives for weeks accumulates conflict and stops being
reviewable.

## Versioning

[Semantic Versioning 2.0.0](https://semver.org/): `vMAJOR.MINOR.PATCH`.

| Increment | When                                                            |
| --------- | --------------------------------------------------------------- |
| `MAJOR`   | API contract break, or an irreversible data migration.           |
| `MINOR`   | New functionality, backwards compatible.                         |
| `PATCH`   | Bug fix, no contract change.                                     |

Before the first production delivery the project stays on `0.x.y`, where `MINOR`
absorbs contract breaks.

## The release PR

When `dev` has accumulated a set of changes ready to ship:

### 1. Open the release PR

From `dev` to `main`, titled `Release vX.Y.Z`, using the release template:

```
https://github.com/isaacgraper/sigi/compare/main...dev?template=release.md
```

The body lists **every** PR included since the last release. It is the audit
record for that version — worth the effort of filling in properly.

To gather what landed since the last tag:

```bash
git log --oneline --no-merges v0.1.0..dev
```

### 2. Prepare the version

On a `chore/release-vX.Y.Z` branch created from `dev`, merged into `dev` before
the release PR:

- Move the `[Unreleased]` entries in `CHANGELOG.md` into a `[X.Y.Z] - YYYY-MM-DD`
  section.
- Update `version` in `backend/pyproject.toml` and `frontend/package.json`.

### 3. Review and merge

- All CI checks green.
- Migration notes and rollback plan filled in on the PR.
- Merge with a **merge commit** (never squash): the release PR must preserve the
  individual history of the PRs it aggregates.

### 4. Tag and publish

Immediately after the merge, on `main`:

```bash
git checkout main
git pull origin main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

Then publish the GitHub Release pointing at the tag, reusing the release PR body
as the version notes.

### 5. Synchronise

`main` and `dev` must be identical right after a release. If the merge produced a
commit only on `main`, bring it back:

```bash
git checkout dev
git merge --no-ff main
git push origin dev
```

## Hotfix

An urgent fix that cannot wait for the normal cycle:

1. `hotfix/<description>` created from `main`.
2. PR to `main` — same review and CI requirements as any other PR.
3. After the merge, immediately tag a new `PATCH` version (`v0.2.1`).
4. Merge `main` back into `dev`, so the fix is not lost in the next release.

A hotfix is an exception. If it is becoming routine, the problem is in test
coverage or release size, not in the process.

## Inviolable rules

1. Nobody pushes directly to `main` or `dev`.
2. `main` only ever receives a merge from a release PR or a `hotfix/*`.
3. Every commit on `main` carries a tag and has a GitHub Release.
4. No PR is merged with red CI.
5. No tag is rewritten or moved. A published version is immutable.
