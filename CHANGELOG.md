# Changelog

All notable changes to this project are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versioning follows [Semantic Versioning](https://semver.org/).

Every Pull Request adds its entry under `[Unreleased]`. In the release PR, those
entries are moved into a new dated version section — see
[`docs/process/branching-and-releases.md`](docs/process/branching-and-releases.md).

## [Unreleased]

### Added

- **Quality gates that run before the commit, not only in CI.** `pre-commit`
  enforces `ruff`, `ruff format` and `mypy`; `pytest` with the 70% coverage
  floor runs at push. Every hook is `repo: local` with `language: system`, so
  there is one pinned version of each tool — the one in `poetry.lock` — and
  installing the hooks needs no network.
- `scripts/check_commit_msg.py` — enforces the Conventional Commits convention
  and the `[SPEC-XXXX]` reference, which `CONTRIBUTING.md` has required and
  nothing has checked.
- `scripts/check_personal_data.py` — refuses to commit CPF, SIAPE numbers, JWTs
  or an institutional address belonging to a real person. A generic scanner does
  not know what a CPF is, and this table of rules is where that knowledge lives.
- `gitleaks` as a CI job, closing the gap `docs/security/threat-model.md` has
  named in three separate paragraphs and `roadmap.md` places in M1.
- `docs/process/sop-qualidade.md` — which rule is enforced by which machine,
  and, deliberately in the same table, the four that nothing enforces.
- `## Bootstrap` in `CONTRIBUTING.md`.
- Initial project structure: FastAPI backend, Next.js frontend, Docker Compose
  and specification documentation.
- Branching and release process (`dev` → `main` via a release PR), Pull Request
  templates, CODEOWNERS and CI workflows.
- `docs/architecture/data-sources.md` — field-level mapping from the entity's
  eight real CSV exports to the model, with cadence, format hazards and an LGPD
  section.
- `ADR-0007` — the Nota de Empenho carries multiple insumos.
- `ADR-0008` — ingesting stock signals from DOMS without becoming an inventory
  system, as an import-only dated snapshot.
- `ADR-0009` — **operational data supersedes the RFC as the source of truth.**
  Authority runs: operational data › stakeholder statements › repo specs ›
  RFC v1.6 (historical context).
- `scripts/analise-planilhas.py` — reproduces every figure cited in the
  documents from the stakeholders' workbooks.
- `ADR-0015` — saldo is reserved from pré-empenho and committed at emission, as
  the stakeholder's own example shows; delivery is tracked on the NE as
  `quantidade_faltante` and never enters saldo. New rule `RN17`. NFs gain item
  lines and a quarantine flag (SPEC-0005).
- SPEC-0001 v1.7: a gestor unblocks an account (AC-0001-44) and the invitation
  asks for the full name and the registration (AC-0001-45); SPEC-0010 v1.5 has the
  matching screens.
- SPEC-0002 v0.3: the reajuste date, its request by SEI process and its alert
  (AC-0002-18 to -21).
- A gestor can unblock a member (`POST /api/v1/usuarios/{id}/desbloquear`, with a
  justification), and an invitation carries the full name and the registration
  (`registro_funcional`, migration `0002`), as SPEC-0001 v1.7 specifies.
- The members page shows the registration, the invite dialog asks for the full name and
  the registration, and a blocked member offers "Desbloquear" with a justification
  (SPEC-0010 v1.5, AC-0010-59 and -60).
- ATAs (`/api/v1/atas`): registration, the lifecycle, aditivos, reajuste requests and the
  renewal and reajuste alerts, with migration `0003_atas`, as SPEC-0002 v1.1 specifies.
- SPEC-0002 v0.4: an MVP slice with every criterion in Given/When/Then, the ATA lifecycle,
  reading for all profiles, permissions, errors and audit events. Criteria that need
  SPEC-0003, SPEC-0004 or SPEC-0006 are marked deferred. OQ-45 records the assumptions.
- OQ-40 to OQ-44 and OQ-46, recording what the stakeholder's answers settled, left assumed or open.

### Changed

- The SKU is the item's identity (SPEC-0003 v0.3), unique and changeable by a
  gestor with a justification; the DOMS code moves to its own field. ATA import is withdrawn from SPEC-0002, because ATAs are entered by
  hand. SPEC-0004, SPEC-0005 and SPEC-0006 follow ADR-0015.
- `docs/requirements/traceability.md` maps the revised and new criteria; RF16 is no
  longer unmapped.
- **The backend is managed with Poetry instead of uv.** `pyproject.toml` keeps
  its PEP 621 and PEP 735 tables unchanged and gains `package-mode = false`,
  which is what the application always was; `backend/poetry.toml` fixes the
  environment at `backend/.venv`; `uv.lock` is replaced by `poetry.lock`. CI,
  the Dockerfile, `CLAUDE.md` and `.claude/settings.json` follow.
- Ruff now selects `W` and `D` (docstrings, `google` convention) alongside
  `E`, `F`, `I`, `UP`, `B` and `SIM`. `mypy` joins the dev dependencies, which
  `definition-of-done.md` had required since before there was a pipeline to run
  it in.
- `NOTA_EMPENHO` becomes a header with a new `ITEM_NOTA_EMPENHO` child; `INSUMO`
  gains `sku`, `codigo_externo`, `grupo_id`, `substituido_por_id`; new
  `GRUPO_MATERIAL`. `DB2` and `DB6` revised, `DB7` added (ADR-0007).
- SPEC-0001 through SPEC-0006 and SPEC-0008 revised to v0.2 against the
  operational data and the 17/08 stakeholder meeting.
- SPEC-0004 and SPEC-0006 to **v0.3**: acceptance criteria rewritten for the
  header/item split. AC-0004-01/02/12/13/14/16 and AC-0006-02/05/06/07 revised;
  AC-0004-19..24 and AC-0006-10..12 added. No AC renumbered.
- Saldo is now defined in two units — value per ATA and quantity per
  `ITEM_ATA` — because the purchase decision is taken on quantity and the audit
  question is asked of value (OQ-20).
- `OQ-07` and `OQ-27` marked `Assumed`, implemented as AC-0004-16 and
  AC-0004-22.
- `OQ-02`, `OQ-05`, `OQ-06` and `OQ-11` resolved from measured data; `OQ-08`,
  `OQ-09` and `OQ-15` reframed; `OQ-18` to `OQ-27` opened.
- `docs/security/lgpd.md` records health data (`pacienteNome`) present in the
  source exports, which the RFC assumed absent.
- Scope re-anchored to the operation (ADR-0009): `CLAUDE.md`, `vision.md`,
  `glossary.md`, `sdd-workflow.md` and the `sigi-domain` skill no longer treat
  the RFC as the arbiter of scope, and invariant 5 now forbids *computed or
  mutable* stock rather than all stock data.
- Nine entities required by the operation added to the data model: `UNIDADE`,
  `CENTRO_CUSTO`, `SOLICITACAO`, `ITEM_SOLICITACAO`, `CRONOGRAMA`,
  `POSICAO_ESTOQUE_SNAPSHOT`, `PROCESSO_LICITATORIO`, `ETAPA_PROCESSO`,
  `ITEM_PROCESSO`, `ACAO_ITEM`.
- `OQ-04`, `OQ-20`, `OQ-21`, `OQ-25` and `OQ-26` resolved by ADR-0009; RF20/RF21
  leave the deferred list.
- `roadmap.md` states plainly that the 16-week plan no longer covers the scope.
- `docs/rfc-sigi-v1.7.md`, merged in PR #4, marked **Superseded**: it reuses
  requirement identifiers that already mean something else (`RF05`, `RN11`, the
  `RF04`–`RF30` range) and is contradicted by the operational data on five
  points. Its disposition — keep as history or delete — is OQ-28.
- `docs/analise-lacunas-rfc-v1.6.md` repointed to the ADRs that actually carry
  its findings.

[Unreleased]: https://github.com/isaacgraper/sigi/commits/dev
