---
id: SPEC-0002
title: ATAs de Registro de Preços
status: Draft
version: 0.3
owner: Isaac Kleimmann Graper
satisfies: [RF04, RF08, RF11, RF16, RF19, RN04, RN11, RN13, RN15]
depends_on: [SPEC-0001]
milestone: M2
---

# SPEC-0002 — ATAs de Registro de Preços

## 1. Purpose

The ATA is the root of every supply cycle. Without it there is no item, no
saldo and no NE. This spec covers its lifecycle, its registration, the reajuste that falls
due a year after the budget date, and the renewal alert that gives Mariana
warning before an ATA lapses.

## 2. Lifecycle vs. vigência

The RFC conflates two orthogonal concepts: the ENUM `(em_andamento, concluida,
cancelada)` in the data model, and the badges `Vigente / A vencer / Vencida /
Encerrada / Suspensa` in Tela 4. These are separated here.

- **`status`** (stored, explicit lifecycle): `rascunho → vigente → encerrada`,
  with `suspensa` and `cancelada` reachable from `vigente`.
- **`situacao_vigencia`** (derived, never stored): `vigente` |
  `a_vencer` (≤ 90 days remaining) | `vencida`, computed from
  `vigencia_fim` against the current date.

Storing a derived date state guarantees it goes stale the moment nobody runs the
job that refreshes it.

## 3. Behaviour

**AC-0002-01** — A gestor registers an ATA with número, objeto, fornecedor,
órgão, vigência início/fim, valor total and data de orçamento planilhado.

**AC-0002-02** — `numero` is unique; a duplicate returns 409 `ATA_DUPLICADA`.

**AC-0002-03** — `vigencia_fim` must be after `vigencia_inicio`; otherwise 422.

**AC-0002-04** — `valor_total` must be greater than zero, `NUMERIC(15,2)`; a
value with more than two decimals is rejected rather than silently rounded.

**AC-0002-05** — Only a gestor may create, edit or close an ATA (RN04); servidor
and auditor receive 403.

**AC-0002-06** — *Withdrawn in v0.3.* It specified a CSV upload of ATAs exported
from e-Publica. No such export exists, and the stakeholder confirmed that ATAs
are informed through SEI and recorded in a spreadsheet (question 1; OQ-02,
OQ-19), so a gestor registers each one (AC-0002-01). The items of an ATA are
imported by CSV under SPEC-0003 (AC-0003-06). The number is kept, because no AC
is ever renumbered.

**AC-0002-07** — *Withdrawn in v0.3.* Atomic import per file remains a rule, but
for the items: SPEC-0003 AC-0003-07 owns it.

**AC-0002-08** — A `processo_sei`-style e-Publica process number is validated by
format only; no HTTP request is made to e-Publica (RF08, ADR-0002).

**AC-0002-09** — An ATA within 90 days of `vigencia_fim` with no aditivo appears
in the renewal alert (RF19), ordered by days remaining ascending.

**AC-0002-10** — Closing an ATA sets `status = encerrada` and records the actor
and timestamp.

**AC-0002-11** — Closing is refused with 409 `ATA_COM_NE_PENDENTE` while any NE
against it is in a non-terminal state (RN13); the message names the blocking NEs.

**AC-0002-12** — A suspended ATA accepts no new NEs but retains its history.

**AC-0002-13** — An aditivo increases `quantidade` and/or `valor_total`, is
recorded as its own entity with its own justification, and immediately raises
`saldo_disponivel` (RF15).

**AC-0002-14** — An aditivo exceeding 25% of the original quantity is rejected
with 422 `ADITIVO_ACIMA_DO_LIMITE` (RN15).

**AC-0002-15** — `situacao_vigencia` is computed at read time; a test freezes the
clock at three dates and asserts all three values without any write occurring.

**AC-0002-16** — Every ATA mutation writes a `HISTORICO_MOVIMENTACAO` row with
`dados_anteriores` containing the full prior state.

**AC-0002-17** — Deleting an ATA is not possible through any route; only
cancellation, which preserves history.

**AC-0002-18** — The reajuste date is derived (OQ-08)
```gherkin
Given an ATA with data_orcamento_planilhado 10/03/2026
When  its reajuste date is read
Then  it is 10/03/2027, one calendar year after the data do orçamento
And   no column stores it
```
A date that follows another date is never stored, for the reason `situacao_vigencia`
is not (§2). An orçamento dated 29/02 falls due on 28/02.

**AC-0002-19** — A gestor records a reajuste request
```gherkin
Given a vigente ATA
When  a gestor records a reajuste request with a processo_sei and the date it was filed
Then  the request is stored against the ATA
And   an audit row records it with the gestor as actor
When  the processo_sei is malformed
Then  the response is 422 with error code "PROCESSO_SEI_INVALIDO", as in SPEC-0004 AC-0004-03
When  a servidor or an auditor tries to record one
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
The request is opened in SEI, outside SIGI; SIGI records that it was filed and
under which process (RF08, ADR-0002).

**AC-0002-20** — The reajuste alert
```gherkin
Given a vigente ATA whose reajuste date is within the alert window, or already past
And   no reajuste request is recorded for it
When  the reajuste alert is read
Then  the ATA appears, ordered by days remaining ascending, negative once the date has passed
When  a reajuste request is recorded for it
Then  it no longer appears
```
The window is 90 days and configurable (OQ-42, `Assumed`). A test freezes the
clock at three dates, as AC-0002-15 does.

**AC-0002-21** — Recording a request changes no price
```gherkin
Given an ITEM_ATA at valor_unitario R$ 7.800,00
When  a reajuste request is recorded for its ATA
Then  the ITEM_ATA still reads R$ 7.800,00
```
Applying a new price needs the index and who approves it, which nobody has said
(OQ-08). SPEC-0004 AC-0004-23 already guarantees that a later price change never
reaches an issued NE.

## 4. Open questions

OQ-02 (resolved: ATAs are entered by hand, confirmed by the stakeholder on
2026-10-02), OQ-08 (reajuste: window, request and alert specified, index and
approver still unknown), OQ-11 (does the entity ever run an ATA with multiple
fornecedores? The model assumes one), OQ-19 (the Cincatarina channel), OQ-42
(the reajuste alert's lead time).

## Revision 2026-09-02 — validated against operational data

Three assumptions in this spec were checked against the stakeholders' workbooks
(`docs/architecture/data-sources.md`) and two did not survive.

**There is no ATA import.** OQ-02 asked whether e-Publica import is a lookup or
a CSV upload. It is neither: the entity's export contract contains **no ATA
report at all**. ATAs are maintained by hand in a spreadsheet, and some arrive
through **Cincatarina**, a shared-purchase channel producing ATAs the entity did
not run itself. AC-0002-* covering import must be re-scoped to: manual ATA
registration, plus CSV import of the ATA's *items*. See OQ-19. *(Done 2026-10-02:
AC-0002-06 and -07 are withdrawn.)*

**`fornecedor_id` is not always singular.** 29 of 456 ATAs (6,4%) carry more
than one fornecedor, up to three. §2's model of one supplier per ATA is wrong
for those. The likely fix is to move fornecedor to `ITEM_ATA`, which also
matches how the source records it. Not applied here — it changes AC-0002-01 and
the data model, and belongs in a revision that can be reviewed on its own.

**A third status axis exists.** §2 separates stored `status` from derived
`situacao_vigencia`. The source's `STATUS DA ATA` holds 17 values, and 12 of
them describe neither: they describe the **acquisition process** — `SAP`,
`FRACASSADO`, `CONSTRUÇÃO EDITAL`, `EM LICITAÇÃO`, `PGM`, `DESERTO`,
`TERMO DE REFERÊNCIA`. A `VENCIDA` ATA whose replacement pregão is `DESERTO` is
operationally different from one `EM LICITAÇÃO`, and neither axis in this spec
can express the difference. See OQ-21.

**Reajuste, partially answered.** `Controle de ITENS` carries
`DATA LIMITE REAJUSTE` per item, so the window is per-item and already tracked.
Index and approver remain unknown, so RF16 stays unspecified (OQ-08). *(Specified
in part on 2026-10-02: see below.)*

## Revision 2026-10-02 — how ATAs arrive, and the reajuste

**ATAs arrive through SEI and live in a spreadsheet.** The validation
questionnaire asked how an ATA reaches the team. The answer (question 1) was that
they are *"informadas via SEI"* and *"cadastradas em uma planilha do drive"*, each
with a limit fixed beforehand in the licitatório and one year of validity. That
confirms there is no ATA import, so AC-0002-06 and -07, which still described an
e-Publica CSV upload and which the 2026-09-02 revision had marked for re-scoping,
are withdrawn. What stays open is the Cincatarina channel (OQ-19).

**The reajuste is specified, in part.** RF16 was unmapped for lack of the entity's
policy. Question 2 supplied what the first version needs: the reajuste falls due
*"um ano após a data do orçamento"*, is requested through a SEI process, and the
system must alert about it. AC-0002-18 to -21 specify the date, the request and
the alert. Still unknown are the index and who approves (OQ-08), so nothing here
changes a price, and the alert's lead time and whether the right lapses after the
date (OQ-42, `Assumed`).

## 5. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF04/RF08, Tela 4, mockup 9.2.2.1 |
| 0.2 | 2026-09-02 | Validated against operational data: no ATA export exists (OQ-02 resolved); multi-fornecedor ATAs confirmed (OQ-11); third status axis recorded (OQ-21) |
| 0.3 | 2026-10-02 | Stakeholder answers (questions 1 and 2): ATAs are informed through SEI and entered by hand, so AC-0002-06 and -07 (ATA import) are withdrawn; the reajuste is specified in part, AC-0002-18 to -21 (date one year after the orçamento, request by SEI process, alert), and RF16 is mapped. Index and approver still unknown (OQ-08); alert lead time assumed (OQ-42) |
