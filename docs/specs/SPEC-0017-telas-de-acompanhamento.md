---
id: SPEC-0017
title: Telas de acompanhamento, rastreio e histórico
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF06, RF10, RN06, RN07]
depends_on: [SPEC-0007, SPEC-0011, SPEC-0013, SPEC-0014, SPEC-0015, SPEC-0016]
milestone: M2
---

# SPEC-0017 — Telas de acompanhamento, rastreio e histórico

## 1. Purpose

The screens of SPEC-0007, so a person reads what happened to an ATA, an NE, an
NF or an insumo in words, not in rows of JSON. The product owner, on 2026-11-10:
"o historico ainda nao entendi, tipo o aditivo, o que mudou? acompanhamento
inteiro? e bem legal, uma parte como rastreio ou historico mesmo". Every event
is the API's, with its label, its changes and its details (AC-0007-10); the
screens only write them out.

## 2. Scope

**In scope:**
- an "Acompanhamento" tab on the ATA, NE and NF pages;
- the rastreio of an insumo on its page;
- "Histórico" in the sidebar, for the gestor and the auditor.

**Out of scope:** exporting the history. Every export carries its provenance and
writes its own history row (SPEC-0009 AC-0009-02, -04), so it comes from the API.
The "Exportar" of the Histórico arrives with SPEC-0009 v1.2's shared export, with
the list exports.

## 3. Behaviour

**AC-0017-01** — The Acompanhamento of an ATA
```gherkin
Given a gestor or an auditor on an ATA whose vigência_fim an aditivo moved
When  they open its "Acompanhamento" tab
Then  its events show newest first, each with its label, when and who
And   the aditivo reads "Fim da vigência" with the date before and the date after
```
A date reads `dd/MM/yyyy`, money `R$`, a quantity in pt-BR, a status by its name.
A detail the event recorded that is not a change, such as a motivo, shows under
it with its label.

**AC-0017-02** — The same on an NE and on an NF
```gherkin
Given an NE that advanced and an NF held in quarantine
When  a gestor or an auditor opens the "Acompanhamento" tab of each
Then  the NE's advance reads its etapa before and after
And   the NF's reads "Em quarentena" and the motivo it was held with
```

**AC-0017-03** — Creation and removal
```gherkin
Given an event that created an entity
Then  it reads "Criado com" and the values it was created with
Given an event that removed an ATA item
Then  it reads "Removido" and the values it had
```

**AC-0017-04** — The servidor has no Acompanhamento
```gherkin
Given a servidor on an ATA, an NE or an NF
Then  the page has no "Acompanhamento" tab
```
The API refuses the history to a servidor (AC-0007-09); a servidor follows an
insumo through its rastreio.

**AC-0017-05** — The rastreio of an insumo
```gherkin
Given an insumo that is an item of an ATA, with one NE in Pré-empenho and another
      issued with an NF
When  any perfil opens the insumo's page
Then  its rastreio reads, top to bottom, the ATA, the item, each NE and the NF
And   each NE shows its five etapas, the current one marked and the ones still missing listed
And   the ATA, the NE and the NF each link to their page
```
A servidor sees only the insumos of its grupos (RN07): outside them the page is
not found (AC-0014-12).

**AC-0017-06** — Each step of the rastreio tells what happened
```gherkin
Given the rastreio of an insumo
When  "Ver acompanhamento" is pressed on a step
Then  that step's events show, with their changes, oldest first
```

**AC-0017-07** — An insumo with no ATA
```gherkin
Given an insumo that is no item of any ATA
Then  its rastreio says it has not started
```

**AC-0017-08** — The Histórico
```gherkin
Given a gestor or an auditor
When  they open "Histórico" in the sidebar, before "Membros"
Then  every event shows newest first, 25 to a page, each with when, the label,
      the entity and who
And   the entity links to its page when it has one
And   the URL keeps the page and the filters
```

**AC-0017-09** — Filtering the Histórico
```gherkin
Given the Histórico
When  an entity type, a member or a period is chosen
Then  only the events that match show
When  the period starts after it ends
Then  the API's message shows under "De" and the list is kept
```

**AC-0017-10** — An event opens to its changes
```gherkin
Given a row of the Histórico
When  it is opened
Then  its changes show, before and after, and its details with their labels
```

**AC-0017-11** — Only values, only statuses
```gherkin
Given a page of the Histórico
When  "Só mudanças de valor" is chosen
Then  only the events that changed money or a quantity on that page show
When  "Só mudanças de status" is chosen
Then  only the events that changed a status or an etapa on that page show
And   the URL keeps the choice
```
The filter narrows the page the API served, and says so; the next page is still
the API's next page.

**AC-0017-12** — The servidor has no Histórico
```gherkin
Given a servidor
Then  "Histórico" is not in the sidebar
And   opening /historico says the perfil cannot see it
```

## 4. Permissions

As SPEC-0007 §2.1: the history to the gestor and the auditor, the cycle of an
insumo to every perfil inside RN07. A member's name comes from `/api/v1/usuarios`,
which the servidor does not read, so the rastreio names no one to a servidor.
Hiding is cosmetic; the API refuses what a perfil may not read (invariant 8).

## 5. API surface

SPEC-0007 §2.1, with the fields of AC-0007-10. The rastreio also reads each NE
and NF it names (SPEC-0004, SPEC-0005) for its número and its current status. No
new endpoint.

## 6. Implementation plan

1. `lib/historico/` (types, constants: the labels of entidade types, the routes
   of each, the tipos counted as value or status; `format.ts`, a change's value
   by its tipo).
2. `components/historico/`: `event-list.tsx` (an event, its changes and
   details), `record-tabs.tsx` ("Dados" and "Acompanhamento", the tab in the
   URL as `?aba=acompanhamento`), `rastreio.tsx` (the timeline).
3. The tabs on `atas/[id]`, `notas-empenho/[id]` and `notas-fiscais/[id]`; the
   rastreio on `insumos/[id]`.
4. `app/(app)/historico/` and "Histórico" in `NAV_MODULES` before Membros,
   visible to the gestor and the auditor; its row in `user-map.md`.
5. Vitest for `format.ts` in `tests/historico.test.ts`; e2e in
   `e2e/historico.spec.ts`, a test per AC named `AC-0017-NN`.

No new dependency: the tabs are a `role="tablist"` of buttons.

## 7. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-11 | Written as Approved, by the product owner's approval on 2026-11-10 of the plan: an Acompanhamento tab on the ATA, NE and NF pages, the rastreio of an insumo for every perfil, and a Histórico for the gestor and the auditor with filters, rows that open and "só mudanças de valor" and "de status". Two defaults accepted then: a servidor sees only the rastreio, and a creation reads "criado com" and its first values. The export moves to SPEC-0009 v1.2, which serves every export with its provenance |
