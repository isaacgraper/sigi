---
id: SPEC-0013
title: Telas de ATAs
status: Approved
version: 1.1
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
- `/atas`: the two alerts, the list with its filters and pages, and "Cadastrar ATA".
- `/atas/{id}`: the ATA, its aditivos and reajuste requests, and the gestor's
  actions on it: edit, the lifecycle moves, "Registrar aditivo" and
  "Registrar pedido de reajuste".
- "ATAs" in the sidebar for every perfil.
- The loading, empty and error states of both pages.

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

**AC-0013-02** — The two alerts come first
```gherkin
Given a signed-in usuario of any perfil
When  /atas is shown
Then  a block "ATAs a renovar" lists the rows of GET /api/v1/atas/alertas/renovacao
And   a block "Reajuste a solicitar" lists the rows of GET /api/v1/atas/alertas/reajuste
And   each row shows the ATA's número and objeto and the days remaining, in the API's order
And   each row opens that ATA
When  an alert has no rows
Then  its block reads "Nenhuma ATA neste alerta."
```
Days remaining are written out: "Vence em 12 dias", "Venceu há 3 dias", "Vence
hoje" for renewal, and "Reajuste em 20 dias", "Reajuste vencido há 5 dias",
"Reajuste hoje" for reajuste. A negative count is the API's (AC-0002-09,
AC-0002-20); the screen does not decide which ATA belongs in an alert.

**AC-0013-03** — The list shows every ATA, a page at a time
```gherkin
Given ATAs registered
When  /atas is shown
Then  a table lists them with the columns Número, Objeto, Fornecedor, Vigência,
      Valor contratado, Status, Situação and Reajuste em
And   Vigência reads "01/01/2026 a 31/12/2026", Valor contratado reads "R$ 1.234.567,89"
And   Status and Situação are badges with the API's values in words
And   each row opens that ATA
When  there are more than 25
Then  the list shows 25 and a control to move between pages, with the total
```
Status words: Rascunho, Vigente, Suspensa, Encerrada, Cancelada. Situação words:
Vigente, A vencer, Vencida. Both come from the API (`status`,
`situacao_vigencia`, AC-0002-15); the screen never derives them.

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

**AC-0013-07** — A gestor registers an ATA
```gherkin
Given a gestor on /atas
When  "Cadastrar ATA" is chosen
Then  a dialog asks for Número, Objeto, Órgão, CNPJ do fornecedor, Razão social,
      Data de emissão (opcional), Início da vigência, Fim da vigência,
      Valor total and Data do orçamento planilhado
When  it is submitted with valid values
Then  POST /api/v1/atas is called once
And   the new ATA's page opens, saying "ATA cadastrada como rascunho."
Given a servidor or an auditor on /atas
Then  "Cadastrar ATA" is not offered
```
Hiding the control is cosmetic; the API refuses the write (AC-0002-05).

**AC-0013-08** — The API's refusal lands on the field it names
```gherkin
Given the "Cadastrar ATA" dialog
When  the API answers 422 "INVALID_DATA" with `fields`
Then  each named field shows its message below it and is marked invalid
And   focus moves to the first of them
And   every value typed is kept
When  the API answers 409 "ATA_DUPLICADA"
Then  Número shows "Já existe uma ATA com este número. Confira o número ou abra a existente."
```
The dialog checks only that a required field is not empty before sending. The
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
Then  the page header reads "ATA {número}" with its Status and Situação badges
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

**AC-0013-14** — A gestor edits what may still change
```gherkin
Given a gestor on a "Rascunho" ATA
When  "Editar" is chosen
Then  the registration fields are shown filled and editable
Given a gestor on an ATA past "Rascunho"
When  "Editar" is chosen
Then  only Objeto and Órgão are editable
And   the others are shown read-only with "Depois de ativada, valores e prazos só mudam por aditivo."
When  the edit is saved
Then  PATCH /api/v1/atas/{id} carries only the fields that changed
And   a refusal lands on its field as in AC-0013-08
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

**AC-0013-18** — Both pages hold at every width
```gherkin
Given /atas and /atas/{id}, with their dialogs open and closed
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
| `TRANSICAO_INVALIDA`, `ATA_NAO_EDITAVEL`, `ATA_NAO_VIGENTE` | The API's message in the open dialog, and the ATA reloaded (AC-0013-12, -14) |
| `NOT_FOUND` on /atas/{id} | "ATA não encontrada." with a link back (AC-0013-10) |
| `PERFIL_NAO_AUTORIZADO` | The API's message; reachable only if the perfil changed while the page was open |
| Session expired | SPEC-0010's session handling, as on every page |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| See /atas, /atas/{id} and both alerts | ✓ | ✓ | ✓ |
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
  - `frontend/lib/modules.ts` gains "ATAs".
  - `frontend/lib/atas.ts` holds the types, the words for each status and
    situação, the moves per status (AC-0013-12) and the days-remaining text.
  - `frontend/lib/format.ts` gains a calendar-date formatter, BRL formatting,
    pt-BR money parsing to a decimal string, and CNPJ formatting.
  - `frontend/app/(app)/atas/` holds the list page, and `[id]/` the ATA page,
    each with its `loading.tsx`.
  - `frontend/components/atas/` holds the badges, the alerts, the ATA form
    (register and edit), the move confirmation, and the aditivo and reajuste dialogs.
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
