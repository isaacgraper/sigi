---
id: SPEC-0012
title: Painel
status: Approved
version: 1.2
owner: Isaac Kleimmann Graper
satisfies: [RF20]
depends_on: [SPEC-0011]
milestone: M2
---

# SPEC-0012 — Painel

## 1. Purpose

`/dashboard` becomes the screen the entity already works from: the four pages of
its `RELATÓRIO GERAL CAME` report (Looker Studio), which the stakeholders sent as
the design of SIGI's home screen. It is the coverage view RF20 names and ADR-0008
puts in scope: what was requested and delivered per unidade, how consumption
moves, where each processo licitatório stands, and which items are running out.

Every block is on screen from the first release and reads "Sem dados" until SIGI
holds what feeds it. The layout is the stakeholders' and does not change as
modules land; each block only starts showing figures.

## 2. Scope

**In scope**
- The four sections of the report, as four tabs, with every filter, card, table
  and chart the report shows, in its order and with its labels.
- The empty, loading and error states of each block.
- Who is signed in, moved from the dashboard body to its header (AC-0010-28).

**Out of scope**
- Filling any block. Each block's data arrives with the spec that owns its
  source (§3), and that spec adds the criterion for its figures.
- The report's colours and fonts. `DESIGN.md` governs style (ADR-0014); the
  report governs content and order.
- Module tiles. The sidebar already lists every module, so AC-0011-13 and
  AC-0011-14 are withdrawn by SPEC-0011 v1.2.

## 3. Domain model touched

None. The dashboard reads; it never writes. Where each block's data will come
from, per `docs/architecture/data-sources.md`:

| Section | Source, when it exists |
| --- | --- |
| Atendimento por unidade | DOMS `TRANSFERENCIA CONSOLIDADO (CSV)` (§3) and `UNIDADE` |
| Consumo | DOMS `REQUISIÇÃO ENTRE UNIDADES (CSV)` (§4) and the estoque snapshot (ADR-0008) |
| Processos licitatórios | `PROCESSO_LICITATORIO`, `ETAPA_PROCESSO`, `ITEM_PROCESSO` (no spec yet) |
| Itens em falta | DOMS `COBERTURA DE ESTOQUE (CSV)` (§2), `ITEM_ATA`, saldo (SPEC-0006) |

**Invariant 5 holds on this screen.** Saldo and Estoque are separate columns and
cards, never summed, never one figure. An estoque figure, once shown, carries the
snapshot's `data_referencia`.

## 4. Behaviour

### 4.1 The page

**AC-0012-01** — The dashboard opens on the report's four sections
```gherkin
Given a signed-in usuario of any perfil
When  /dashboard is shown
Then  the page header reads "Painel"
And   a tab list offers, in this order, "Atendimento por unidade", "Consumo",
      "Processos licitatórios" and "Itens em falta"
And   "Atendimento por unidade" is selected
```

**AC-0012-02** — The tabs follow the keyboard pattern for tabs
```gherkin
Given /dashboard with "Atendimento por unidade" selected
When  the selected tab has focus and ArrowRight is pressed
Then  "Consumo" is selected and its panel is shown
And   ArrowLeft, Home and End move the selection the same way
And   each panel is labelled by its tab
```

**AC-0012-03** — The selected tab survives a reload
```gherkin
Given /dashboard with "Itens em falta" selected
When  the page is reloaded
Then  "Itens em falta" is still selected
```
The tab lives in the URL (`?aba=itens-em-falta`), so a link to a section can be sent.

**AC-0012-04** — A block with no data says so
```gherkin
Given a section whose answer from GET /api/v1/painel/{section} has no rows for a block
When  the answer arrives
Then  the block keeps its title and reads "Sem dados"
And   the section's filters are shown disabled
```
Today every block's answer is empty, because none of the sources in §3 exists
yet. "Sem dados" is what the backend said, not what the screen assumed.

**AC-0012-05** — A section whose request fails does not pass for empty
```gherkin
Given a section whose request to GET /api/v1/painel/{section} fails
When  the failure arrives
Then  the error notice of DESIGN.md §6 shows in place of the blocks, with the gestor contact (AC-0010-57)
And   no block reads "Sem dados"
```

**AC-0012-11** — A skeleton covers the section until its answer arrives
```gherkin
Given a section whose request is still pending
When  it is shown
Then  every block shows a skeleton of its own shape, in the report's layout
And   the wait is announced once as "Carregando..."
And   the route's first paint (loading.tsx) shows the same skeleton
```
The skeleton has the blocks' shape so nothing moves when the answer lands
(DESIGN.md §6, "Loading a page").

### 4.2 The sections

Each section lists its blocks in the report's order. Column and card names are
the report's, in its words.

**AC-0012-06** — Atendimento por unidade
```gherkin
Given the "Atendimento por unidade" tab
When  it is shown
Then  it has the filters "Unidade", "ESF", "ESB", "Pesquisa de mercadorias" and "Data"
And   a table "Mercadorias" with the columns Mercadorias, Autorizado, Atendido, V.T atendido
And   a table "Unidades" with the columns Unidade, ESF, ESB, EMULTI, EMAP, EAPP,
      EMAD Multi Prof I, População, Atendido
And   a chart "Atendido e valor total atendido por unidade"
```

**AC-0012-07** — Consumo
```gherkin
Given the "Consumo" tab
When  it is shown
Then  it has the filters "Mercadorias" and "Unidade"
And   a card "Estoque"
And   a chart "Solicitado, autorizado, atendido e média atual por mês"
```

**AC-0012-08** — Processos licitatórios
```gherkin
Given the "Processos licitatórios" tab
When  it is shown
Then  it has the filters "Ano processo", "Objeto" and "SKU"
And   the cards Abertura, Novo processo, Previsão, Status, Nova data projetada,
      Progresso, Vigente, Vencimento and Previsão de tempo sem processo vigente
And   a chart "Etapas: planejado e real" with the stages Comunicado, ACP, SAP-ARC,
      PGM, LCT construção de edital, Publicação do edital, Pregão,
      Propostas / amostras and Homologação
And   a table "Itens do processo" with the columns Ano processo, Nº item, Item,
      Objeto, Acompanhamento
```

**AC-0012-09** — Itens em falta
```gherkin
Given the "Itens em falta" tab
When  it is shown
Then  it has the filters "Impacto", "Grupo", "Aquisição", "Grupo de compras",
      "Movimento", "SKU", "Pregão", "Comprador" and "Material"
And   the cards SKU, Estoque and Consumo mês
And   the blocks "Informações extras" and "Sugestões de troca"
And   a table "Processos por grupo" with the columns Grupo, Ano, Processo,
      Data projetada, Dias sem processo
And   the charts "Curva ABC" and "Disponibilidade" (Disponível, Em falta, Baixo estoque)
And   a table "Materiais" with the columns Material, Emp. abertos, Dias estoque,
      Status item, Pregão, SEI, Validade, Saldo, Status do pregão, Status da ATA,
      Classif., Estoque ideal
```

### 4.3 Who is signed in

AC-0010-28 still holds, from the page header: its description shows the
usuario's name when the API returns one, their e-mail and their perfil
("Maria Souza · maria@sc.gov.br · Gestor").

### 4.4 The data

**AC-0012-12** — The dashboard's data answers every perfil, block by block
```gherkin
Given a signed-in usuario of any perfil
When  GET /api/v1/painel/{section} is called for each of the four sections
Then  the response is 200 with the section's id and one entry per block of that section
And   each entry holds "rows", empty while the block's source does not exist
When  it is called without a session
Then  the response is 401
When  it is called for a section that does not exist
Then  the response is 404 with error code "NOT_FOUND"
```

### 4.5 Demonstration data

The stakeholders see the screen before SIGI holds their data. A development
installation can answer with fictional figures in the report's shape, the same
way it can seed `admin/admin` (SPEC-0001 AC-0001-39): never in production, and
never unlabelled.

**AC-0012-13** — In development, the dashboard can show demonstration data
```gherkin
Given APP_ENV is "development" and DASHBOARD_DEMO is true
When  GET /api/v1/painel/{section} is called for each section
Then  every block answers with rows, and the answer carries "demo": true
And   the filters say "Filtros indisponíveis na demonstração."
And   the charts draw their figures, and the Estoque tile names the date of its position
```
The figures are invented, in the ranges of the CAME report. No name, code or
CNPJ of the entity's is used. Saldo and Estoque stay separate figures (invariant 5).

**AC-0012-14** — Demonstration data never reaches another environment
```gherkin
Given DASHBOARD_DEMO is true and APP_ENV is anything but "development"
When  the backend starts
Then  it refuses to start, naming the setting
When  DASHBOARD_DEMO is not set
Then  every answer carries "demo": false and the rows SIGI really holds
```

### 4.6 Layout

**AC-0012-10** — The dashboard holds at every width
```gherkin
Given each of the four tabs
When  it is shown at 360, 768 and 1440 px
Then  the page does not scroll sideways, and a wide table scrolls inside its own frame
And   it passes the accessibility check of AC-0010-44
```

## 5. Errors and edge cases

| Condition | What the block shows |
| --- | --- |
| Request pending | Skeleton of the block's shape (AC-0012-11) |
| No source yet, or zero rows | Title and "Sem dados" (AC-0012-04) |
| Request fails | Error notice with the gestor contact, in place of the blocks (AC-0012-05) |
| Unknown section | 404 `NOT_FOUND` (AC-0012-12); the page itself falls back to the first tab |
| Session expired while loading | SPEC-0010's session handling, as on every page |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| View the dashboard, `GET /api/v1/painel/{section}` | ✓ | ✓ | ✓ |

The endpoint enforces it on the server (invariant 8). A block whose source
later needs a narrower permission gets its own criterion in that source's spec.

## 7. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| GET | `/api/v1/painel/{section}` | Every block of one section: `atendimento`, `consumo`, `processos` or `itens-em-falta` | 04, 05, 11, 12, 13 |

```json
{ "section": "consumo", "demo": false, "blocks": { "estoque": { "rows": [] }, "grafico": { "rows": [] } } }
```

`rows` is a list of rows, each a list of the block's values as text, in its
column order. The block ids are the keys of `frontend/lib/dashboard.ts`. Each
source's spec fills its blocks in the service behind this route; the contract
does not change.

- **Table:** one row per line, display text in pt-BR (`R$ 1.234,56`, `dd/MM/yyyy`).
- **Tile:** one row, the value as display text and, optionally, a caption
  (`["32.693", "Posição de 01/10/2026"]`).
- **Chart:** one row per point, the label first and then one raw number per
  series, as text with a dot for decimals (`["Jan/26", "2119281", "2207565"]`).
  The stages chart sends one row per stage: name, planned days, real days.

`demo` is true only for AC-0012-13's answer.

## 8. Audit events

None. The dashboard only reads.

## 9. Open questions

None block this version. Every block's figures wait on specs that do not exist
yet, which the table in §3 names.

## 10. Implementation plan

- Migration: none.
- Modules: `backend/app/api/painel.py`, `services/painel.py` and
  `schemas/painel.py` serve §7. `frontend/lib/dashboard.ts` declares each
  section and block (title, kind, columns, filters). `frontend/components/dashboard/`
  holds the tabs, the block frame with its empty and error states, and the
  empty table, chart, card and filter shells. `app/(app)/dashboard/dashboard.tsx`
  renders the registry.
- **New dependency (v1.2): `recharts`.** The first charts with data are the
  demonstration's (AC-0012-13), and the stages, line, bar and pie shapes of
  the report need a chart library. Recharts is React-native SVG, needs no
  canvas, and its output can be labelled for assistive technology.
- Settings: `DASHBOARD_DEMO` (default false), refused outside development.
- Tests: `backend/tests/test_painel.py` for AC-0012-12; `frontend/e2e/dashboard.spec.ts`, one test per AC; the AC-0010-28 test
  moves to the header; the AC-0011-13/-14 tests are removed with those criteria.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-09 | Initial draft from the stakeholders' `RELATÓRIO GERAL CAME` report (four pages), sent as the design of the home screen. Every block is laid out and reads "Sem dados" until its source exists. |
| 1.0 | 2026-10-09 | Approved by the product owner, to be refined while it is built; the screen must match the report or improve on it. §4.3 keeps the e-mail in the header, as AC-0010-28 requires. |
| 1.1 | 2026-10-09 | The dashboard asks the backend for its data, by the product owner's request: GET /api/v1/painel/{section} (§7, AC-0012-12), a skeleton while it waits (AC-0012-11), and "Sem dados" only when the answer is empty (AC-0012-04). AC-0012-05 becomes testable. |
| 1.2 | 2026-10-09 | AC-0012-13/-14: development-only demonstration data, by the product owner's request, so the stakeholders see the screen filled before SIGI holds their data. `demo` added to §7, with the row formats per block kind. `recharts` added to the plan. |
| 1.2-demo | 2026-10-09 | Demo branch only, never merged: the notice above the dashboard is removed for the recording; the filter note still marks the demonstration. |
