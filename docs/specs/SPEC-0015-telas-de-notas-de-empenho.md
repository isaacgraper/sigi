---
id: SPEC-0015
title: Telas de notas de empenho
status: Approved
version: 1.1
owner: Isaac Kleimmann Graper
satisfies: [RF13, RF14, RN03, RN08, RN10, RN17]
depends_on: [SPEC-0004, SPEC-0006, SPEC-0011, SPEC-0013]
milestone: M2
---

# SPEC-0015 — Telas de notas de empenho

## 1. Purpose

The screens of SPEC-0004 and of SPEC-0006's saldo, so the stakeholders can walk
an NE from demanda to NE emitida and see the ATA's saldo move: `700 (300)` while
reserved, `700` once issued. Every rule is the API's; the screens show it and
land its refusals on the field they name (DESIGN.md §4).

## 2. Scope

**In scope:** "Notas de empenho" in the sidebar; the list with its counters and
the filter by etapa; opening an NE; the NE page with its stages, its itens and
the moves; the saldo block of the ATA page.

**Out of scope:** replacing the itens of an NE on screen (the API has it,
AC-0004-19); the NFs (SPEC-0005).

## 3. Behaviour

**AC-0015-01** — The list
```gherkin
Given a signed-in member of any perfil
When  they open /notas-empenho
Then  they see Emitidas, Em andamento and Total from /notas-empenho/indicadores
And   the NEs newest first, each with its Processo SEI, ATA, etapa, valor and both números
And   a gestor sees "Abrir NE"
```

**AC-0015-02** — The filter by etapa
```gherkin
Given the list
When  an etapa is chosen
Then  only NEs in it are listed, and the URL keeps the choice
```

**AC-0015-03** — Opening an NE
```gherkin
Given a gestor on /notas-empenho/nova
When  they choose a vigente ATA, type the Processo SEI and the quantity of at least one item
And   press "Abrir NE"
Then  the NE is opened in Demanda and its page shows
```
Each item shows its unit price and what is still available; the price is the
ATA's and is not typed.

**AC-0015-04** — A refusal lands on its field
```gherkin
Given the opening form
When  the API refuses the Processo SEI, the ATA or an item
Then  the message shows under that field, and nothing is opened
```

**AC-0015-05** — The NE page
```gherkin
Given an NE
When  its page opens
Then  the five stages show, the ones passed checked and the current one marked
And   its ATA, Processo SEI, valor, nota de pré-empenho, número and itens show
```
A cancelled NE says it was cancelled in place of the stages.

**AC-0015-06** — Advancing
```gherkin
Given an NE that is not terminal, and a gestor or a servidor
When  they press "Avançar para {etapa}" and confirm
Then  the NE moves one stage and the page shows it
```

**AC-0015-07** — The números are asked for where they arrive
```gherkin
When  the next stage is Pré-empenho
Then  the dialog asks for the número of the nota de pré-empenho
When  the next stage is NE emitida
Then  the dialog asks for the número of the NE
And   a número already used is refused under the field
```

**AC-0015-08** — A refused advance is read in the dialog
```gherkin
Given an NE whose saldo or quantity does not cover it
When  it is advanced to Pré-empenho
Then  the API's message, with the figures, shows in the dialog, and the NE stays
```

**AC-0015-09** — Reverting and cancelling
```gherkin
Given a gestor on an NE that is not terminal
When  they revert one stage or cancel, with a justification
Then  the NE moves and the page shows it
And   neither button is offered to a servidor or an auditor, and nothing at all to an auditor
```

**AC-0015-10** — The saldo of an ATA
```gherkin
Given an ATA with an NE of 300 of 1.000 units of an item in Pré-empenho
When  its page opens
Then  the saldo block shows the value disponível with the reserved part in parentheses
And   that item reads "700 (300)"
When  the NE is issued
Then  the item reads "700"
```
The block states when the figures were summed (AC-0006-09) and offers a gestor
"Abrir NE" on a vigente ATA.

## 4. Permissions

As SPEC-0004 §6. Hiding a button is cosmetic; the API refuses what a perfil may
not do (invariant 8).

## 5. API surface

SPEC-0004 §7 and SPEC-0006 §3.1. No new endpoint.

## 6. Implementation plan

`app/(app)/notas-empenho/` (list, `nova`, `[id]`), `components/notas-empenho/`
(the form, the moves, the stage), `components/atas/saldo.tsx` on the ATA page,
`lib/notas-empenho/` (types and constants), and "Notas de empenho" in
`NAV_MODULES` after Insumos. E2e in `frontend/e2e/notas-empenho.spec.ts`, a test per
AC named `AC-0015-NN`. No new dependency.

## 7. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-10-27 | Written and approved at the product owner's request to build the NE screens with the backend, for the stakeholders' PoC |
| 1.1 | 2026-10-27 | Built. Every criterion has a test in `frontend/e2e/notas-empenho.spec.ts`. No criterion changed |
