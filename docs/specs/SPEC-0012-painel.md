---
id: SPEC-0012
title: Painel
status: Approved
version: 1.0
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
Given a block whose source returns no rows, or has no source yet
When  its section is shown
Then  the block keeps its title and reads "Sem dados"
And   its filters are shown disabled
```

**AC-0012-05** — A block whose source fails does not pass for empty
```gherkin
Given a block whose source request fails
When  its section is shown
Then  the block shows the error notice of DESIGN.md §6 with the gestor contact (AC-0010-57)
And   it does not read "Sem dados"
```
Not reachable while every source is `null`; it binds the first block that gets one.

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

### 4.4 Layout

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
| No source yet, or zero rows | Title and "Sem dados" (AC-0012-04) |
| Source request fails | Error notice with the gestor contact (AC-0012-05) |
| Session expired while loading | SPEC-0010's session handling, as on every page |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| View the dashboard | ✓ | ✓ | ✓ |

When a block gets data, the endpoint behind it enforces its own permission (invariant 8).

## 7. API surface

None in this version. Each block's endpoint is specified with its source.

## 8. Audit events

None. The dashboard only reads.

## 9. Open questions

None block this version. Every block's figures wait on specs that do not exist
yet, which the table in §3 names.

## 10. Implementation plan

- Migration: none.
- Modules: `frontend/lib/dashboard.ts` declares each section and block (title,
  kind, columns, filters, source, `null` today). `frontend/components/dashboard/`
  holds the tabs, the block frame with its empty and error states, and the
  empty table, chart, card and filter shells. `app/(app)/dashboard/dashboard.tsx`
  renders the registry. No chart library until the first chart has data, when
  its spec names one.
- Tests: `frontend/e2e/dashboard.spec.ts`, one test per AC; the AC-0010-28 test
  moves to the header; the AC-0011-13/-14 tests are removed with those criteria.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-09 | Initial draft from the stakeholders' `RELATÓRIO GERAL CAME` report (four pages), sent as the design of the home screen. Every block is laid out and reads "Sem dados" until its source exists. |
| 1.0 | 2026-10-09 | Approved by the product owner, to be refined while it is built; the screen must match the report or improve on it. §4.3 keeps the e-mail in the header, as AC-0010-28 requires. |
