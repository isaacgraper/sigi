---
id: SPEC-0005
title: Notas Fiscais e conferência
status: Draft
version: 0.3
owner: Isaac Kleimmann Graper
satisfies: [RF05, RF11, RF17, RN02, RN05, RN12]
depends_on: [SPEC-0004]
milestone: M4
---

# SPEC-0005 — Notas Fiscais e conferência

## 1. Purpose

The NF closes the cycle: it is the evidence that what was committed was
delivered. Carlos registers it, and Carlos mistypes, so validation quality here
determines whether the −70% error-reduction KPI is achievable.

## 2. Behaviour

**AC-0005-01** — A servidor registers an NF with número, data de emissão, valor,
fornecedor and the NE it belongs to (RN05); any missing field returns 422 naming
it individually.

**AC-0005-02** — The NF binds to `nota_empenho_id` only. There is no route,
schema field or column allowing a direct ATA link (RF05, RN02). The ATA is read
through the NE.

**AC-0005-03** — Binding to an NE whose status is not `ne_emitida` returns 409
`NE_NAO_EMITIDA`, with a test for each of the four non-terminal statuses.

**AC-0005-04** — `data_emissao` may not be in the future; 422 if it is.

**AC-0005-05** — `data_emissao` earlier than the NE's issuance date produces a
warning, not a rejection: the operator confirms explicitly, and the confirmation
is audited. This is a data-quality signal, and blocking it would make legitimate
back-dated documents impossible to register.

**AC-0005-06** — The supplier on the NF must match the supplier on the NE's ATA;
a mismatch returns 409 `FORNECEDOR_DIVERGENTE` naming both.

**AC-0005-07** — The sum of NF values bound to one NE may not exceed the NE
value; exceeding returns 409 `VALOR_ACIMA_DO_EMPENHO` stating both figures (RN12).

**AC-0005-08** — An NF moves through conference statuses `aguardando →
em_conferencia → aprovada | devolvida` (RF17); `devolvida` requires a
justification and permits re-submission.

**AC-0005-09** — A gestor may approve or return an NF; a servidor may register
and submit but not approve their own registration.

**AC-0005-10** — Launching an NF reduces what the NE still waits for, and leaves the
ATA's saldo alone (OQ-03, ADR-0015). A test asserts that `saldo_disponivel` and
`valor_empenhado` are byte-identical before and after the launch, that
`quantidade_faltante` of each item falls by exactly that item's quantity on the NF,
and that an NF in quarantine, or in `devolvida`, moves nothing.

**AC-0005-12** — An NF lists what arrived
```gherkin
Given an issued NE with an item of 300 units
When  a servidor launches an NF with a line for that item of 100 units
Then  the NF is stored with that line and quantidade_faltante of the item is 200
When  a line names an item that is not on the NE, or has a quantity of zero or less
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming the line
When  the lines of the NFs bound to the NE would exceed an item's quantity
Then  the response is 409 with error code "QUANTIDADE_ACIMA_DO_EMPENHO" stating both figures
And   nothing is stored
```
The NF's `valor` is still entered and RN12 still applies to it (AC-0005-07). An NF
counts from the moment it is launched, not when it is approved. A line above what
the NE still waits for is refused the way a value above the NE is (OQ-46).

**AC-0005-13** — An NF with a problem is held in quarantine
```gherkin
Given an NF launched against an issued NE
When  a servidor or a gestor puts it in quarantine with a reason
Then  the NF is flagged and the NE shows that its items arrived and are in quarantine
And   quantidade_faltante does not count its lines
And   an audit row "nf.quarentena_iniciada" records the reason
When  a gestor releases it
Then  quantidade_faltante counts its lines and an audit row "nf.quarentena_liberada" records it
When  the reason is missing
Then  the response is 422 with error code "INVALID_DATA"
When  an NF in quarantine is approved
Then  the response is 409 with error code "NF_EM_QUARENTENA"
```
Quarantine is a flag with a reason, not a fifth status: the four statuses were
confirmed (OQ-12). It is `Assumed` (OQ-46); the stakeholder asked only for *"uma
maneira de destacar que o item chegou porém está em quarentena"*.

## Revision 2026-10-06 — what the NE still waits for

The stakeholder confirmed the four statuses (question 9, OQ-12) and that the
atesto deadline can wait for a later version (OQ-22), so the atesto SLA stays out
of the MVP.

Their example of delivery (question 6 and its follow-up) fixes how an NF matters:
an NE of 300 units with an NF of 100 launched *"só marca a quantidade faltante de
200"*, counted **at the launch** of the note, in units, and never changing the
ATA's saldo (ADR-0015). So the NF gains item lines (AC-0005-12), and a note with a
problem in the note or the material is held in quarantine instead of counted
(AC-0005-13). An earlier text of this revision counted an NF from its approval, in
value; that was a misreading and was removed before review.

## 4. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF05, §2.5 RN02/RN05, Tela 7 |
| 0.2 | 2026-09-02 | RN02 confirmed from real data; RN12 now aggregates over ITEM_NOTA_EMPENHO (ADR-0007); atesto SLA recorded as unmodelled (OQ-22); ENTRADAS NFS excluded on privacy and data-quality grounds (OQ-24) |
| 0.3 | 2026-10-06 | The stakeholder's delivery example (ADR-0015): AC-0005-10 now says launching an NF reduces `quantidade_faltante` and leaves the ATA's saldo alone. AC-0005-12: the NF lists what arrived, per NE item. AC-0005-13: quarantine for an NF with a problem. Four statuses confirmed (OQ-12), atesto deadline deferred (OQ-22). OQ-46 opened |
