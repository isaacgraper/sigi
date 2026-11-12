---
id: SPEC-0018
title: Tela de relatórios
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF12]
depends_on: [SPEC-0009, SPEC-0011]
milestone: M4
---

# SPEC-0018 — Tela de relatórios

## 1. Purpose

The screen of SPEC-0009's four reports, which today exist only in the API. RF12:
"Auditor consults exportable reports (PDF/CSV)". The product owner, on
2026-11-11, chose this screen next. Every figure, every rule and every refusal
is the API's; the screen names the reports and asks for the file.

## 2. Scope

**In scope:** "Relatórios" in the sidebar for the gestor and the auditor; the four
reports, each with what it holds and "Exportar" through the dialog of SPEC-0009
AC-0009-13, with the ATA it may be restricted to.

**Out of scope:** reading a report on screen; the list exports, which live on
their lists (SPEC-0009 AC-0009-10).

## 3. Behaviour

**AC-0018-01** — The reports in the sidebar
```gherkin
Given a gestor or an auditor
When  they open "Relatórios" in the sidebar, after "Histórico" and before "Membros"
Then  the four reports show, each with its name and one line on what it holds:
      execução orçamentária por ATA, posição de saldo consolidada, notas fiscais
      em conferência and indicadores de fornecedores
```

**AC-0018-02** — Exporting a report
```gherkin
Given the Relatórios screen
When  "Exportar" is pressed on a report
Then  the dialog of AC-0009-13 offers CSV or PDF, the report's columns, the data
      de referência and the start of the period
And   "Exportar" in it downloads the report
```

**AC-0018-03** — One ATA
```gherkin
Given the dialog of a report
When  an ATA is chosen in it
Then  the file holds only that ATA, and names it among its filters (AC-0009-02)
```

**AC-0018-04** — The saldo has no period
```gherkin
Given the dialog of the posição de saldo
Then  it offers no start of the period
```
The saldo of part of the NEs would read as the saldo of the ATA (AC-0009-09).

**AC-0018-05** — The servidor has no Relatórios
```gherkin
Given a servidor
Then  "Relatórios" is not in the sidebar
And   opening /relatorios says the perfil cannot see them
```
The API refuses the reports to a servidor (AC-0009-05).

## 4. Permissions

As SPEC-0009 §2.3. Hiding is cosmetic; the API refuses what a perfil may not do
(invariant 8).

## 5. API surface

SPEC-0009 §2.3; the ATAs to choose from come from `GET /api/v1/atas`. No new
endpoint.

## 6. Implementation plan

1. `lib/relatorios/constants.ts`: the four reports, their names, descriptions and
   columns, and which take a period.
2. `components/relatorios/export-dialog.tsx`: the ATA to restrict to and the
   period made optional per report.
3. `app/(app)/relatorios/` and "Relatórios" in `NAV_MODULES` after Histórico,
   visible to the gestor and the auditor; its row in `user-map.md`.
4. E2e in `frontend/e2e/relatorios.spec.ts`, a test per AC named `AC-0018-NN`.

No new dependency.

## 7. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-11 | Written as Approved at the product owner's request on 2026-11-11 for the screen of SPEC-0009's four reports, after the list exports. The dialog is SPEC-0009's |
