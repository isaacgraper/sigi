---
id: SPEC-0016
title: Telas de notas fiscais
status: Implemented
version: 1.1
owner: Isaac Kleimmann Graper
satisfies: [RF05, RF11, RF17, RN02, RN05, RN12]
depends_on: [SPEC-0005, SPEC-0011, SPEC-0015]
milestone: M2
---

# SPEC-0016 — Telas de notas fiscais

## 1. Purpose

The screens of SPEC-0005, so the stakeholders can launch an NF against an issued
NE, walk it through the conference and see on the NE what arrived, what is held
and what is still missing. Every rule is the API's; the screens show it and land
its refusals on the field they name (DESIGN.md §4).

## 2. Scope

**In scope:** "Notas fiscais" in the sidebar; the list with its filters;
registering an NF from an issued NE; the NF page with its itens and the moves;
correcting an NF before conference; on the NE page, what each item received,
holds and misses, its NFs and "Registrar NF".

**Out of scope:** importing NFs from a file; the coverage view (SPEC-0012).

## 3. Behaviour

**AC-0016-01** — The list
```gherkin
Given a signed-in member of any perfil
When  they open /notas-fiscais
Then  they see the NFs newest first, each with its número, NE, data de emissão, valor and status
And   an NF in quarantine says so
```

**AC-0016-02** — The filters
```gherkin
Given the list
When  a status or "Em quarentena" is chosen
Then  only the NFs that match are listed, and the URL keeps the choice
```

**AC-0016-03** — Registering an NF
```gherkin
Given a gestor or a servidor on an NE in NE emitida
When  they press "Registrar NF", type the número, data de emissão, valor, CNPJ
And   the quantity of at least one item, and press "Registrar NF"
Then  the NF is registered in Aguardando and its page shows
```
Each item shows what the NE still waits for. The CNPJ starts as the fornecedor's.

**AC-0016-04** — A refusal lands on its field
```gherkin
Given the registration form
When  the API refuses the número, the data, the valor, the CNPJ or an item
Then  the message shows under that field, and nothing is registered
```

**AC-0016-05** — A data before the empenho is confirmed
```gherkin
Given a data de emissão earlier than the NE's issuance
When  the form is sent
Then  the API's message shows with "Confirmar data"
And   confirming sends it again, and the NF is registered
```

**AC-0016-06** — The NF page
```gherkin
Given an NF
When  its page opens
Then  its número, NE, data de emissão, valor, status and itens show
And   a returned NF shows its justificativa, and one in quarantine its motivo
```

**AC-0016-07** — The conference
```gherkin
Given an NF in Aguardando and a gestor
When  they send it to conference and approve it
Then  the NF reads Aprovada
When  an NF in conference is returned with a justificativa
Then  it reads Devolvida and shows the justificativa
```

**AC-0016-08** — The quarantine
```gherkin
Given an NF in conference
When  a gestor or a servidor holds it with a motivo
Then  it reads "Em quarentena" with the motivo, and "Aprovar" is not offered
When  a gestor releases it
Then  "Aprovar" is offered again
```

**AC-0016-09** — Correcting
```gherkin
Given an NF in Aguardando or Devolvida
When  a gestor or a servidor presses "Corrigir", changes it and saves
Then  the page shows the new values
```

**AC-0016-10** — The buttons follow the perfil
```gherkin
Given an NF in conference
Then  a servidor sees "Quarentena" and neither "Aprovar", "Devolver" nor "Liberar"
And   an auditor sees no move at all, and no "Registrar NF"
```

**AC-0016-11** — The NE shows what arrived
```gherkin
Given an NE of 100 units of an item with an NF of 60 and one of 10 in quarantine
When  its page opens
Then  that item reads recebida 60, em quarentena 10 and faltante 40
And   its NFs are listed, each opening its page
```
An NF counts from the moment it is registered, and one in quarantine is not
faltante (AC-0005-12, -13).

## 4. Permissions

As SPEC-0005 §6. Hiding a button is cosmetic; the API refuses what a perfil may
not do (invariant 8).

## 5. API surface

SPEC-0005 §7. No new endpoint.

## 6. Implementation plan

`app/(app)/notas-fiscais/` (list, `nova`, `[id]`, `[id]/corrigir`), `components/notas-fiscais/`
(the form, the moves, the status), the NFs and the received figures on the NE
page, `lib/notas-fiscais/` (types and constants), and "Notas fiscais" in
`NAV_MODULES` after Notas de empenho. E2e in `frontend/e2e/notas-fiscais.spec.ts`,
a test per AC named `AC-0016-NN`. No new dependency.

## 7. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-04 | Written and approved at the product owner's request to build the NF screens with the backend, in the same PR, for the stakeholders' PoC |
| 1.1 | 2026-11-09 | Implemented, accepted by the product owner after testing the screens. Every criterion has a test in `frontend/e2e/notas-fiscais.spec.ts`; no criterion changed |
