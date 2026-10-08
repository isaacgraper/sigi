<!--
Release PR: dev → main.
This body becomes the GitHub Release notes and is the audit record for the version.
Full process: docs/process/branching-and-releases.md
-->

Releases vX.Y.Z. <!-- One paragraph, in business terms: what this version delivers. -->

**Previous version:** `vX.Y.Z`
**Planned deployment date:**

### Included PRs

<!-- git log --oneline --no-merges vX.Y.Z..dev -->

* **Features**
  * #___ —
* **Fixes**
  * #___ —
* **Infrastructure & Documentation**
  * #___ —

### Specs Delivered

<!-- IDs of the specs whose implementation is complete in this version. -->

* `SPEC-____` —

### Database Migrations

- [ ] This version contains no migrations
- [ ] Contains migrations — listed below

| Alembic revision | Description | Reversible |
| ---------------- | ----------- | ---------- |
|                  |             |            |

**Apply with:**

```bash
docker compose exec backend alembic upgrade head
```

### Deployment Notes

<!-- New environment variables, service start order, required window. -->

### Rollback Plan

<!-- How to go back. If a migration is irreversible, say so explicitly. -->

* Rollback tag: `vX.Y.Z`
* Migrations reverted by:

### Sign-off

<!--
This checklist is deliberate: unlike a regular PR, a release PR is the auditable
record of what was verified before a version reached production.
-->

- [ ] All CI checks green on `dev`
- [ ] `CHANGELOG.md` has a filled and dated `[X.Y.Z]` section
- [ ] `version` updated in `backend/pyproject.toml` and `frontend/package.json`
- [ ] No included spec is still in `Draft`
- [ ] Blocking open questions (`docs/open-questions.md`) resolved
- [ ] Rollback tested in staging
- [ ] Will be merged with a **merge commit**, not a squash
- [ ] Tag `vX.Y.Z` and GitHub Release published immediately after the merge
- [ ] `main` merged back into `dev` after the release
