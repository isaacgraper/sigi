# Changelog

All notable changes to this project are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versioning follows [Semantic Versioning](https://semver.org/).

Every Pull Request adds its entry under `[Unreleased]`. In the release PR, those
entries are moved into a new dated version section — see
[`docs/process/branching-and-releases.md`](docs/process/branching-and-releases.md).

## [Unreleased]

### Added

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

### Changed

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
