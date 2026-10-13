---
id: SPEC-0013
title: Telas de ATAs
status: Approved
version: 1.5
owner: Isaac Kleimmann Graper
satisfies: [RF04, RF08, RF11, RF15, RF16, RF19]
depends_on: [SPEC-0002, SPEC-0011]
milestone: M2
---

# SPEC-0013 — Telas de ATAs

## 1. Purpose

SPEC-0002 gave the ATA its backend: registration, the lifecycle, aditivos,
reajuste requests and the two alerts, under `/api/v1/atas`. Nobody can use any of
it without a client. This spec gives the gestor the screens to register and
run an ATA, and every perfil the screens to read ATAs and see what needs
attention: the ATAs about to lapse (RF19) and the reajustes due (RF16).

The screens add no rule. Every decision is SPEC-0002's and the API's; the
screens ask, show the answer, and show the API's refusal in its own words.

## 2. Scope

**In scope**
- `/atas`: the upcoming vencimentos and reajustes in one list, the ATA list with
  its filters and pages, and "Cadastrar ATA".
- `/atas/nova` and `/atas/{id}/editar`: registering and editing an ATA, each on
  its own page.
- `/atas/{id}`: the ATA, its aditivos and reajuste requests, and the gestor's
  actions on it: edit, the lifecycle moves, "Registrar aditivo" and
  "Registrar pedido de reajuste".
- "ATAs" in the sidebar for every perfil.
- The loading, empty and error states of every page.

**Out of scope**
- Valor empenhado, saldo and the share consumed. They come from the NE ledger
  (SPEC-0004, SPEC-0006), which does not exist yet.
- The items of an ATA and their CSV import (SPEC-0003).
- Changing the ATA's responsável. The API accepts it (AC-0002-24), but choosing
  a member needs a list of members that only a gestor may read today.
- The ATA's audit history on screen (SPEC-0007).
- Deleting an ATA. No control exists, because the API refuses it (AC-0002-17).

## 3. Domain model touched

None. The screens call the endpoints of SPEC-0002 §3 and nothing else. No
endpoint, column or migration is added.

## 4. Behaviour

### 4.1 Navigation

**AC-0013-01** — Every perfil finds ATAs in the sidebar
```gherkin
Given a signed-in usuario of any perfil
When  any page of the shell is shown
Then  the sidebar lists "ATAs" after "Painel" and before "Membros"
And   choosing it opens /atas, whose page header reads "ATAs"
```
This is the entry AC-0010-27 and AC-0011-01 leave room for: a module whose spec
is Approved takes its place between "Painel" and "Membros".

### 4.2 The ATA list

**AC-0013-02** — What falls due comes first, in one list
```gherkin
Given a signed-in usuario of any perfil
When  /atas is shown
Then  a block "Vencimentos e reajustes" lists the rows of GET /api/v1/atas/alertas/renovacao
      and GET /api/v1/atas/alertas/reajuste together, ordered by days remaining ascending
And   each row shows its kind ("Vencimento" or "Reajuste"), the ATA's número and objeto,
      the date it falls due and the days remaining
And   each row opens that ATA
And   a row whose date has passed is marked in the danger colour, with a bar on its
      left edge, a faint tint, its days in red and "em atraso" after its kind
And   a row due within 30 days is marked in the attention colour, with a bar on its
      left edge and its days in amber
And   a row due later carries no colour
And   the block's title is followed by how many are "em atraso" and how many fall due
      "em até 30 dias"
When  there are more than 5 rows
Then  the 5 most urgent show, and "Mostrar todos (N)" shows the rest
When  neither alert has rows
Then  the block is a single line: "Nenhum vencimento ou reajuste próximo."
```
A row's date is the ATA's `vigencia_fim` for a Vencimento and its `data_reajuste`
for a Reajuste. Days remaining read "45 dias", "1 dia" or "hoje", and once the
date has passed, "há 3 dias" in the danger colour. A negative count is the API's
(AC-0002-09, AC-0002-20); the screen does not decide which ATA belongs in an
alert, and an ATA in both appears twice, once per kind.

*(v1.4)* By the product owner's request that a vencimento really close, or past,
be recognised at a glance. Past is unambiguous; 30 days as "close" is assumed
(OQ-47). The colour only says how loudly to show a row the API already put in
an alert; it decides nothing.

*(v1.2)* The two alerts were two identical cards, which halved the width of each,
cut the objeto short and said "Nenhuma ATA neste alerta." twice when there was
nothing to do. One list answers the question both asked, what needs attention
first, by the product owner's decision.

**AC-0013-03** — The list shows every ATA, a page at a time
```gherkin
Given ATAs registered
When  /atas is shown
Then  a table lists them with the columns Número, Objeto, Fornecedor, Vigência,
      Valor contratado, Status and Reajuste em
And   Vigência reads "01/01/2026 a 31/12/2026", Valor contratado reads "R$ 1.234.567,89"
And   Status reads as one line of text (DESIGN.md §4): the status word, followed by
      the situação when the ATA is vigente or suspensa and not plainly vigente
And   each row opens that ATA
When  there are more than 25
Then  the list shows 25 and a control to move between pages, with the total
```
Status words: Rascunho, Vigente, Suspensa, Encerrada, Cancelada. Situação words:
vigente, a vencer, vencida. Both come from the API (`status`,
`situacao_vigencia`, AC-0002-15); the screen never derives them, only chooses
which to show:

| Status | Situação | Reads | Mark |
| --- | --- | --- | --- |
| vigente | vigente | Vigente | none |
| vigente | a_vencer | Vigente · a vencer | amber dot |
| vigente | vencida | Vigente · vencida | red dot |
| suspensa | vigente | Suspensa | amber dot |
| suspensa | a_vencer, vencida | Suspensa · a vencer, Suspensa · vencida | amber, red dot |
| rascunho, encerrada, cancelada | any | Rascunho, Encerrada, Cancelada | muted text |

The situação of an ATA not running says nothing a person acts on, so it is not
shown; the Situação filter still applies to every ATA.

**AC-0013-04** — The list filters by status and situação
```gherkin
Given /atas
When  a status and a situação are chosen
Then  the list holds only the ATAs the API returns for those filters
And   the filters and the page live in the URL (?status=vigente&situacao=a_vencer&pagina=2)
And   reloading the page keeps them
When  the filters are cleared
Then  the full list returns, from its first page
```

**AC-0013-05** — An empty list says why
```gherkin
Given no ATA registered
When  /atas is shown
Then  the list reads "Nenhuma ATA cadastrada."
And   a gestor is offered "Cadastrar ATA"
Given filters that match no ATA
When  the list is shown
Then  it reads "Nenhuma ATA com esses filtros." with a control to clear them
```

**AC-0013-06** — Loading and failure
```gherkin
Given a request of /atas or /atas/{id} still pending
When  the page is shown
Then  each block shows a skeleton of its own shape, announced once as "Carregando..."
Given a request that fails
When  the failure arrives
Then  the error notice of DESIGN.md §6 shows in place of that block, with the gestor contact (AC-0010-57)
And   no block reads as empty
```

### 4.3 Registering an ATA

**AC-0013-07** — A gestor registers an ATA on its own page
```gherkin
Given a gestor on /atas
When  "Cadastrar ATA" is chosen
Then  /atas/nova opens with the page header "Nova ATA" and the fields in four sections:
      Identificação (Número, Objeto, Órgão), Fornecedor (CNPJ do fornecedor, Razão social),
      Vigência (Início da vigência, Fim da vigência, Data de emissão (opcional)) and
      Valores (Valor total, Data do orçamento planilhado)
And   "Cadastrar" and "Voltar" stay in view at the foot of the page
When  it is submitted with valid values
Then  POST /api/v1/atas is called once
And   the new ATA's page opens, saying "ATA cadastrada como rascunho."
When  "Voltar" is chosen
Then  /atas returns and nothing is sent
Given a servidor or an auditor on /atas
Then  "Cadastrar ATA" is not offered
And   /atas/nova, opened by its address, says "Seu perfil não permite esta ação." with a link back
```
Hiding the control is cosmetic; the API refuses the write (AC-0002-05).

*(v1.2)* Ten fields with validation are a document, not a quick task, and a
dialog that scrolls hid half of them; the sections follow the ATA page's own
grouping, so the form looks like the page it produces, by the product owner's
decision.

**AC-0013-08** — The API's refusal lands on the field it names
```gherkin
Given the registration or the edit page
When  the API answers 422 "INVALID_DATA" with `fields`
Then  each named field shows its message below it and is marked invalid
And   focus moves to the first of them
And   every value typed is kept
When  the API answers 409 "ATA_DUPLICADA"
Then  Número shows "Já existe uma ATA com este número. Confira o número ou abra a existente."
```
The page checks only that a required field is not empty before sending. The
rest (CNPJ check digits, the vigência's order, the valor's precision) is the API's
(AC-0002-03, -04, -25).

**AC-0013-09** — Money is typed in pt-BR and sent exactly
```gherkin
Given a money field
When  "1.234.567,89" is typed
Then  the API receives "1234567.89"
When  "10,005" is typed
Then  the API receives "10.005" and refuses it, and nothing is rounded (AC-0002-04)
```
The value goes from text to text and never through a floating-point number. The
CNPJ is shown as 00.000.000/0000-00 while it is typed and sent as typed; the API
keeps its 14 digits.

### 4.4 The ATA page

**AC-0013-10** — The ATA page shows the ATA as the API holds it
```gherkin
Given an ATA
When  /atas/{id} is shown
Then  the page header reads "ATA {número}" with its status line of AC-0013-03 and its objeto
And   it shows Objeto, Órgão, Fornecedor (razão social and CNPJ), Data de emissão,
      Vigência, Valor total, Valor contratado, Data do orçamento planilhado and
      Data de reajuste
And   a calendar date reads as typed, dd/MM/yyyy, on any browser time zone
When  the id does not exist
Then  the page reads "ATA não encontrada." with a link back to /atas
```
Valor contratado and Data de reajuste are the API's (AC-0002-13, AC-0002-18). A
date such as `vigencia_fim` is a calendar date, not an instant, so it is never
shifted by a time zone.

**AC-0013-11** — Aditivos and reajuste requests are listed
```gherkin
Given an ATA
When  /atas/{id} is shown
Then  a table "Aditivos" has the columns Tipo, Acréscimo ou novo fim, Justificativa, Registrado em
And   a table "Pedidos de reajuste" has the columns Processo SEI, Data do pedido, Registrado em
When  either is empty
Then  it reads "Nenhum aditivo registrado." or "Nenhum pedido de reajuste registrado."
```

### 4.5 The gestor's actions

**AC-0013-12** — The lifecycle moves offered follow the status
```gherkin
Given a gestor on an ATA's page
Then  a "Rascunho" ATA offers "Ativar" and "Cancelar"
And   a "Vigente" ATA offers "Suspender", "Encerrar" and "Cancelar"
And   a "Suspensa" ATA offers "Retomar", "Encerrar" and "Cancelar"
And   an "Encerrada" or "Cancelada" ATA offers no move
When  a move is chosen
Then  a confirmation names the ATA and what the move does
When  it is confirmed
Then  the page shows the status the API returned, and the change is announced
When  the API refuses it
Then  the confirmation shows the API's message and the page reloads the ATA
```
The list mirrors AC-0002-22 so that a gestor is not offered a dead button; the
API stays the authority, and a refusal it sends is shown, not hidden.

**AC-0013-13** — Cancelling asks why
```gherkin
Given a gestor confirming "Cancelar"
Then  the confirmation asks for a Justificativa, up to 500 characters
When  it is left empty
Then  "Cancelar ATA" stays disabled
When  it is confirmed with a justification
Then  POST /api/v1/atas/{id}/cancelar carries it
```

**AC-0013-14** — A gestor edits what may still change, on its own page
```gherkin
Given a gestor on a "Rascunho" ATA
When  "Editar" is chosen
Then  /atas/{id}/editar opens with the page header "Editar ATA {número}" and the
      sections of AC-0013-07, filled and editable
Given a gestor on an ATA past "Rascunho"
When  "Editar" is chosen
Then  only Objeto and Órgão are editable
And   the others are shown read-only with "Depois de ativada, valores e prazos só mudam por aditivo."
When  the edit is saved
Then  PATCH /api/v1/atas/{id} carries only the fields that changed
And   the ATA's page opens, saying "ATA atualizada."
And   a refusal lands on its field as in AC-0013-08
When  "Voltar" is chosen
Then  the ATA's page returns and nothing is sent
```

**AC-0013-15** — A gestor records an aditivo
```gherkin
Given a gestor on a "Vigente" ATA
When  "Registrar aditivo" is chosen
Then  a dialog asks for Tipo ("Valor" or "Prazo") and a Justificativa
And   "Valor" asks for the Acréscimo, and "Prazo" for the Novo fim da vigência
When  it is submitted
Then  the aditivo appears in "Aditivos" and the page shows the ATA the API returned
When  the API answers 422 "ADITIVO_ACIMA_DO_LIMITE"
Then  Acréscimo shows "O aditivo passa de 25% do valor original da ATA. Reduza o valor."
Given an ATA that is not "Vigente"
Then  "Registrar aditivo" is not offered
```
The screen does not compute the 25% ceiling; the API does (AC-0002-14).

**AC-0013-16** — A gestor records a reajuste request
```gherkin
Given a gestor on a "Vigente" ATA
When  "Registrar pedido de reajuste" is chosen
Then  a dialog asks for the Processo SEI and the Data do pedido
And   the Processo SEI field shows the format NNNNN.NNNNNN/AAAA-DD
When  it is submitted
Then  the request appears in "Pedidos de reajuste"
When  the API answers 422 "PROCESSO_SEI_INVALIDO"
Then  Processo SEI shows "Número de processo SEI inválido. Use o formato NNNNN.NNNNNN/AAAA-DD."
Given an ATA that is not "Vigente"
Then  "Registrar pedido de reajuste" is not offered
```

**AC-0013-17** — Readers read
```gherkin
Given a servidor or an auditor on an ATA's page
Then  the ATA, its aditivos and its reajuste requests are shown
And   no edit, move, aditivo or reajuste control is offered
```

### 4.6 Layout

**AC-0013-18** — Every page holds at every width
```gherkin
Given /atas, /atas/nova, /atas/{id} and /atas/{id}/editar, with their dialogs open and closed
When  they are shown at 360, 768 and 1440 px
Then  the page does not scroll sideways, and a wide table scrolls inside its own frame
And   they pass the accessibility check of AC-0010-44
And   every action can be reached and confirmed with the keyboard
```

## 5. Errors and edge cases

| Condition | What the screen shows |
| --- | --- |
| Request pending | Skeleton of the block's shape (AC-0013-06) |
| Request fails | Error notice with the gestor contact (AC-0013-06) |
| `INVALID_DATA`, `ATA_DUPLICADA`, `ADITIVO_ACIMA_DO_LIMITE`, `PROCESSO_SEI_INVALIDO` | The API's message under the field it names (AC-0013-08, -15, -16) |
| `TRANSICAO_INVALIDA`, `ATA_NAO_VIGENTE` | The API's message in the open dialog, and the ATA reloaded (AC-0013-12) |
| `ATA_NAO_EDITAVEL` | The API's message on the edit page, and the ATA reloaded (AC-0013-14) |
| `NOT_FOUND` on /atas/{id} | "ATA não encontrada." with a link back (AC-0013-10) |
| `PERFIL_NAO_AUTORIZADO` | The API's message; reachable only if the perfil changed while the page was open |
| Session expired | SPEC-0010's session handling, as on every page |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| See /atas, /atas/{id} and the vencimentos and reajustes | ✓ | ✓ | ✓ |
| Cadastrar, editar, mover, registrar aditivo e pedido de reajuste | ✓ | — | — |

The API enforces it (SPEC-0002 §3.7, invariant 8). The screens only hide what a
perfil cannot do.

## 7. API surface

No new endpoint. The screens use SPEC-0002's:

| Method | Path | Used by |
| --- | --- | --- |
| GET | `/api/v1/atas?page=&size=&status=&situacao_vigencia=` | AC-0013-03, -04, -05 |
| GET | `/api/v1/atas/alertas/renovacao`, `/api/v1/atas/alertas/reajuste` | AC-0013-02 |
| POST | `/api/v1/atas` | AC-0013-07, -08, -09 |
| GET, PATCH | `/api/v1/atas/{id}` | AC-0013-10, -11, -14 |
| POST | `/api/v1/atas/{id}/ativar`, `suspender`, `retomar`, `encerrar`, `cancelar` | AC-0013-12, -13 |
| POST | `/api/v1/atas/{id}/aditivos`, `/api/v1/atas/{id}/reajustes` | AC-0013-15, -16 |

## 8. Audit events

None of its own. Every write is SPEC-0002's endpoint, which writes its audit row
in the same transaction (AC-0002-16).

## 9. Open questions

None block this version. Changing the responsável waits on a way for a gestor to
choose a member from this screen (§2).

## 10. Implementation plan

- Migration and backend: none.
- Modules:
  - `NAV_MODULES` in `frontend/lib/constants.ts` gains "ATAs".
  - `frontend/lib/atas/` holds the types (`types.ts`), the words for each
    status and situação and the moves per status (`constants.ts`, AC-0013-12),
    the status line and urgency (`status.ts`) and the days-remaining text
    (`due.ts`).
  - `frontend/lib/format.ts` gains a calendar-date formatter, BRL formatting,
    pt-BR money parsing to a decimal string, and CNPJ formatting.
  - `frontend/app/(app)/atas/` holds the list page, `nova/` the registration,
    `[id]/` the ATA page and `[id]/editar/` the edit, each with its `loading.tsx`.
  - `frontend/components/atas/` holds the status words, the vencimentos and
    reajustes list, the ATA form (register and edit, in sections), the move
    confirmation, and the aditivo and reajuste dialogs.
- New dependencies: none.
- Tests:
  - `frontend/tests/atas.test.ts` (Vitest) covers money parsing, date and
    CNPJ formatting, the moves per status and the days-remaining text.
  - `frontend/e2e/atas.spec.ts` (Playwright, against the real API, in Chromium,
    Firefox and WebKit) has one test per AC.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-13 | Initial draft. The screens for SPEC-0002 v1.1: the list with both alerts, registration, the ATA page, the lifecycle moves, edit, aditivo and reajuste request. No backend change. |
| 1.0 | 2026-10-13 | Approved by the product owner as drafted, including the moves offered per status as a cosmetic mirror of AC-0002-22. |
| 1.1 | 2026-10-13 | AC-0013-01 names the room AC-0010-27 and AC-0011-01 leave for it. No behaviour change. |
| 1.2 | 2026-10-13 | By the product owner's review of the screens: registering and editing move from a dialog to `/atas/nova` and `/atas/{id}/editar`, in the ATA page's sections (AC-0013-07, -14); the two alert cards become one "Vencimentos e reajustes" list ordered by urgency, the 5 most urgent first (AC-0013-02); AC-0013-18 covers the new pages. |
| 1.3 | 2026-10-13 | Status is one line of text, not two badges, by DESIGN.md §4 as revised by the product owner: the Situação column folds into Status, and the situação shows only where it says something (AC-0013-03, -10). |
| 1.4 | 2026-10-13 | AC-0013-02: due rows are coloured by urgency (red once past, amber within 30 days, none beyond) and the block states how many are late and how many close, by the product owner's request. 30 days assumed (OQ-47). |
| 1.5 | 2026-10-13 | §10 names the files `lib/atas.ts` and `lib/modules.ts` became under `docs/process/coding-standards.md`. No criterion or behaviour changed. |
