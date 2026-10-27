# Changelog

All notable changes to this project are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versioning follows [Semantic Versioning](https://semver.org/).

Every Pull Request adds its entry under `[Unreleased]`. In the release PR, those
entries are moved into a new dated version section — see
[`docs/process/branching-and-releases.md`](docs/process/branching-and-releases.md).

## [Unreleased]

### Added

- `python -m app.cli seed-demo`: a fictitious sample for a development install, loaded
  through the services with its audit rows, once, and refused outside development.
- The API documentation on GitHub Pages: the `api-docs` workflow exports the OpenAPI schema
  from `create_app()` on every push to `dev` and publishes it with Swagger UI, read-only, on
  the `gh-pages` branch.
- The insumo screens (SPEC-0014): "Insumos" in the sidebar, the catalogue searched and
  filtered, registration and correction, the insumo page with its ATAs and the gestor's SKU
  change, discontinuation, substitution and reactivation, and the grupo tree.
- Both CSV imports on screen: choosing the file checks it with a dry run at once, the lines are
  shown as the API read them with what happens to each, and one confirmation imports them. A
  file over 5 MB or not .csv is refused before it is sent; a cell with a control character or
  starting with =, + or @ refuses the file (SPEC-0003 v1.3, AC-0003-33, -34).
- A SKU, descrição, unidade or grupo name made of digits only is refused, by hand and by file,
  and the default SKU pattern asks for a letter (SPEC-0003 v1.4, AC-0003-35).
- The items section of the ATA page: the unit price at up to five decimals, the contracted
  quantity with its aditivos, the items' sum beside the ATA's value, and the gestor's add,
  correct, remove and aditivo de quantidade.
- A gestor sets a servidor's grupos de materiais from Membros, over the new
  `GET /api/v1/usuarios/{id}/grupos-materiais` (SPEC-0003 v1.2, AC-0003-32).
- The insumo catalogue (SPEC-0003): `/api/v1/insumos` registers, corrects, searches,
  discontinues, substitutes and reactivates insumos by SKU, and changes a SKU with a
  justification; `/api/v1/grupos-materiais` holds the three levels of the DOMS hierarchy.
- The items of an ATA under `/api/v1/atas/{id}/itens`: added, corrected and removed one by
  one, with the unit price at five decimals and the item's value rounded once to the centavo
  (ADR-0016), an optional fornecedor per item, and their sum beside the ATA's valor_total. The
  aditivo de quantidade raises one item, at most 25% of its quantity.
- CSV import for the catalogue and for an ATA's items: all or nothing, a dry run, pt-BR
  numbers in a `;` file, UTF-8 or Windows-1252, and the hazards measured in the source files.
  The two import routes take a body up to 5 MB (SPEC-0001 v1.10).
- RN07 on the grupo axis: a gestor sets a servidor's grupos, and the servidor sees only the
  insumos and items in them. Migration `0005_insumos`.

- The dashboard is the stakeholders' `RELATÓRIO GERAL CAME` report (SPEC-0012): four tabs,
  Atendimento por unidade, Consumo, Processos licitatórios and Itens em falta, with every
  filter, card, table and chart the report shows. Each block reads "Sem dados" until SIGI
  holds its data.
- `GET /api/v1/painel/{section}` serves the dashboard's blocks for all three perfis. The page
  shows a skeleton while it waits and "Sem dados" for a block that comes back empty, which
  today is every block (SPEC-0012 v1.1).
- ATA screens (SPEC-0013): `/atas` with what falls due ("Vencimentos e reajustes", one list
  ordered by urgency) and the list filtered by status and situação; `/atas/nova` and
  `/atas/{id}/editar` to register and edit, in sections; `/atas/{id}` with the ATA, its
  aditivos and reajuste requests, the lifecycle moves, "Registrar aditivo" and
  "Registrar pedido de reajuste". Every perfil reads; only a gestor sees the writes. No
  backend change: the screens use SPEC-0002's endpoints.
- `docs/product/user-map.md`: every screen, its sidebar slot and what each perfil may do there.
- `docs/product/user-flows/atas.md`: every path through the ATA screens, each field's rules and
  the API's refusal for it, with 27 screenshots of the running application.

### Changed

- SPEC-0003 v1.5 and SPEC-0014 v1.4 are `Implemented`, accepted by the product owner after
  testing the insumo screens. AC-0003-25 is carried by SPEC-0004; RN07's unidade axis waits for
  `UNIDADE`.
- SPEC-0002 v1.3 and SPEC-0013 v1.8 are `Implemented`, accepted by the product owner. The three
  SPEC-0002 criteria that need NEs move to SPEC-0004 v0.5 (AC-0004-17, -25, -26).
- SPEC-0003 v0.4 specifies the insumo catalogue and the items of an ATA for approval: grupos in
  the three levels of the DOMS hierarchy, substitution and discontinuation, a catalogue file and
  an items file per ATA with a dry run, the pt-BR number rules and the hazards measured in the
  source files, one item at a time on the ATA, the aditivo de quantidade with its 25% ceiling,
  and RN07 on the grupo axis. ADR-0016 keeps the unit price at five decimals and every total
  at two.
- Registering an ATA ends in a review, "Confira os dados antes de cadastrar", and saves only on
  "Confirmar cadastro". The ATA is vigente from that moment: there is no rascunho and no
  "Ativar" (SPEC-0002 v1.2, SPEC-0013 v1.7). Migration `0004_ata_sem_rascunho` moves any
  rascunho to vigente.
- "Editar" corrects every field of a vigente or suspensa ATA, the figures included, with the
  previous values in the audit trail; an encerrada or cancelada ATA is not edited
  (AC-0002-24). Once NEs exist, an NE emitida locks the figures (AC-0002-26, SPEC-0004).
- No success banner after a write on the ATA screens: the result is the confirmation, and
  assistive technology still hears it (DESIGN.md §4 Notice).
- Every field of the ATA form and dialogs explains itself behind an "i" (AC-0013-19, DESIGN.md
  §4 Field help).
- Navigating between pages no longer flashes a skeleton: the routes under the shell have no
  `loading.tsx`, a skeleton appears only once a wait passes 300 ms, a page already read in the
  tab draws its last data at once while the API answers, and resting on an ATA's link fetches it
  before the click (SPEC-0011 v1.4 AC-0011-18, DESIGN.md §6). The answers live in the tab's
  memory only and are cleared on login, logout and any write.
- The M2 specs reviewed for approval: SPEC-0004 v0.6 types the NE número in at emission, as
  the financial system issues it, and copies each item's price from the ATA; SPEC-0006 v0.5
  and SPEC-0007 v0.2 are in Given/When/Then with their read endpoints, permissions and errors.
  SPEC-0005 moves to M2, so NFs can be launched in the same milestone.

- Status reads as text, never as a pill badge (DESIGN.md §4): the word in the body colour, a
  small dot only when it needs attention, and finished states in grey. An ATA's status and
  situação become one line ("Vigente · a vencer"); member status follows the same rule.
- Frontend constants and types live in `lib/constants.ts`, `lib/types.ts` and
  `lib/<feature>/` (`atas`, `members`, `dashboard`), per `docs/process/coding-standards.md`.
  An ESLint rule fails the lint on an `UPPER_CASE` constant anywhere else. No behaviour
  change: the Vitest and Playwright suites pass unchanged.
- Backend constants live in `app/constants/` by domain (`auth`, `members`, `atas`,
  `painel`), per `docs/process/coding-standards.md` §7. `scripts/check_constants.py`
  refuses one declared anywhere else, at commit and in `backend-ci`. No behaviour change:
  the 320 backend tests pass unchanged.
- The dashboard no longer shows module tiles; the sidebar lists the modules (SPEC-0011 v1.2
  withdraws AC-0011-13 and -14). Who is signed in moves to the page header.

### Removed

- `docs/rfc-sigi-v1.7.md`, superseded since PR #4, by the product owner's decision (OQ-28).
  `RF05` and `RN11` keep one definition each, so tests may be named after them.

### Fixed

- A write's transaction was committed after its response had left, so a read made at once
  could miss the row it had just been told about: a new ATA's page opened on "ATA não
  encontrada" now and then. The session dependency now commits before the response is sent.
- The alphanumeric CNPJ the Receita Federal issues since July 2026 (IN RFB nº 2.229/2024) was
  refused; it is accepted and stored uppercased (AC-0002-25).

- The ORM model of `sessao` listed `lockout` where migration 0001 created `bloqueio` in
  `ck_sessao_motivo_valor`. The database was right and the code only ever wrote
  `bloqueio`; the model now says so too. `alembic check` does not compare `CHECK` text,
  which is why the drift went unnoticed.

## [0.1.0] - 2026-10-08

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
- A pending member's row offers "Gerar novo convite": a new activation link, shown once,
  that switches off the previous one (SPEC-0001 AC-0001-46, SPEC-0010 AC-0010-61).
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

- SPEC-0001 (v1.9), SPEC-0010 (v1.7) and SPEC-0011 (v1.1) are `Implemented`, accepted by the
  product owner. Their traceability rows name the tests that prove each criterion.
  AC-0001-30 stays blocked until a mail transport exists (OQ-31).
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

### Fixed

- `docker-compose.yml` no longer defaults `SUPPORT_CONTACT_EMAIL` to a personal
  address. Unset, the error pages say "Procure o gestor da sua unidade.", as
  AC-0010-57 specifies; deploy sets the gestores' mailbox.

[Unreleased]: https://github.com/isaacgraper/sigi/compare/v0.1.0...dev
[0.1.0]: https://github.com/isaacgraper/sigi/releases/tag/v0.1.0
