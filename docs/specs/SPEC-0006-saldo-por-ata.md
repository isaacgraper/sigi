---
id: SPEC-0006
title: Saldo por ATA (visão derivada)
status: Draft
version: 0.4
owner: Isaac Kleimmann Graper
satisfies: [RF14, RN10, RN15]
depends_on: [SPEC-0002, SPEC-0004, SPEC-0005]
milestone: M2
---

# SPEC-0006 — Saldo por ATA

## 1. Purpose

Saldo is the number every stakeholder in the RFC's research asked for, and it is
the number most likely to be wrong. This spec defines it as a pure function of
the NE cycle, so that "wrong saldo" becomes impossible by construction rather
than something a reconciliation job fixes after the fact.

## 2. Definition

Saldo exists in **two units**, because the operation uses both (OQ-20).

### 2.1 Value, per ATA

```
saldo_disponivel(ata) =
      valor_contratado(ata)          -- ATA total + approved aditivos
    - valor_reservado(ata)           -- Σ itens of NEs in pre_empenho, envio_fornecedor
    - valor_empenhado(ata)           -- Σ itens of NEs in ne_emitida
```

Since ADR-0007 an NE carries many insumos, so both sums aggregate over
`ITEM_NOTA_EMPENHO`, filtered by the **parent NE's** status. The status lives on
the header; the quantities live on the lines.

Reserved and committed both subtract, so **issuing the NE does not change
`saldo_disponivel`**. What changes is how it is shown: while an NE is reserved
the saldo reads `700 (300)`, the reserved part in parentheses, and once it is
issued it reads `700`. This is the stakeholder's own example (ADR-0015, OQ-03).

`comprometimento_percentual` is `(valor_reservado + valor_empenhado) /
valor_contratado`. RF14 and Tela 5 call it "consumo"; the stakeholder uses
*consumo* for delivery (§2.3), so the API says what it is.

### 2.2 Quantity, per item

```
quantidade_disponivel(item_ata) =
      item_ata.quantidade                -- contracted, plus aditivos de quantidade
    - Σ ITEM_NOTA_EMPENHO.quantidade     -- where the parent NE is in pre_empenho,
                                         -- envio_fornecedor or ne_emitida
```

This is the figure the buyer actually decides on: an ATA can hold budget while
the item it covers is exhausted. `RN10` blocks on whichever runs out first
(AC-0004-24).

NEs in `demanda`, `validacao_saldo` and `cancelada` contribute nothing to either.
Reservation begins at `pre_empenho` — the first stage past the saldo guard — and
converts to commitment at `ne_emitida`. The quantity splits the same way, into
`quantidade_reservada` and `quantidade_empenhada`.

### 2.3 Delivery, per NE item

```
quantidade_recebida(item_nota_empenho) =
      Σ ITEM_NOTA_FISCAL.quantidade     -- NFs bound to the NE, launched, not in
                                        -- quarantine and not "devolvida"
quantidade_faltante(item_nota_empenho) = item_nota_empenho.quantidade - quantidade_recebida
```

What an NE still waits for. It **never enters `saldo_disponivel`**: the ATA's saldo
was settled when the NE was reserved and committed. An NF counts when it is
**launched**, not when it is approved. An NF with a problem in the note or the
material is in quarantine: it does not count, and the NE shows that the item
arrived and is held (ADR-0015, OQ-46).

**There is no `saldo` column, in either unit.** No endpoint writes one. The only
way to change a saldo is to change an ATA's contracted value or move an NE
through its state machine. This is the single most important architectural
constraint in the system; see ADR-0003 — and the entity's own spreadsheet, which
keeps `SALDO` beside `SALDO CALCULADO` and disagrees with itself in 32,5% of
rows.

**Saldo is not estoque.** Saldo is budget and contracted quantity remaining on
an ATA, derived here. `estoque` is physical stock, imported from DOMS as a dated
snapshot (ADR-0008). They are never summed and never shown as one number.

## 3. Behaviour

**AC-0006-01** — With no NEs, `saldo_disponivel` equals `valor_contratado` and
`comprometimento_percentual` is 0.

**AC-0006-02** — The worked example from Tela 5 reproduces, with its figures named
as the stakeholder's answer requires: ATA 002/2026 at R$ 2.840.000,00 with one NE
in `ne_emitida` whose itens total R$ 78.000,00 yields `saldo_disponivel`
R$ 2.762.000,00, `valor_reservado` R$ 0,00, `valor_empenhado` R$ 78.000,00 and
`comprometimento_percentual` 3% (rounded to the nearest whole percent). Tela 5
called that 3% "consumo"; it is the committed share. A second test splits the same R$ 78.000,00 across four itens and
asserts an identical result — the saldo depends on the sum, not on how the NE is
composed.

**AC-0006-03** — Commitment at or above 80% flags the ATA as
`alto_consumo = true` (RF14); a test at 79.9%, 80.0% and 80.1% pins the boundary.
The flag measures `comprometimento_percentual`, reserved plus committed: the buyer
needs to know how little is left to promise, and that does not wait for deliveries.

**AC-0006-04** — Aditivos raise `valor_contratado` and therefore lower
`comprometimento_percentual` without any NE changing.

**AC-0006-05** — Cancelling an NE in a reserving state releases its value **and
the contracted quantity of every one of its itens** in the same transaction.

**AC-0006-06** — Saldo is computed from the NE ledger on every read; a test
mutates `ITEM_NOTA_EMPENHO` rows, and separately `ITEM_NOTA_FISCAL` rows, directly in
the database and asserts the next read reflects it with no refresh step. This is what distinguishes a derived value
from a cached one. **If this criterion is ever weakened, ADR-0003 has been
silently reversed** — the failure mode it prevents is measurable in the source
spreadsheet at 32,5%.

**AC-0006-07** — The saldo endpoint for 500 ATAs and 10.000 NEs **averaging three
itens each** responds under 300 ms p95 (RNF01), using an indexed aggregate or a
materialised view refreshed in the same transaction as the NE write — never a
stale asynchronous job. The aggregation now crosses one more join than in v0.2,
so this budget is measured against the real shape rather than assumed.

**AC-0006-08** — Money arithmetic uses `Decimal` throughout; a test summing 1.000
NEs of R$ 0,01 asserts exactly R$ 10,00 (RNF15).

**AC-0006-09** — A saldo response states the instant it was computed, so an
exported report can be reproduced and defended in an audit.

**AC-0006-10** — Quantity saldo per item (OQ-20)
```gherkin
Given an ITEM_ATA for "Monitor 24 polegadas" with contracted quantidade 20
And   an NE in "ne_emitida" carrying 5 units of that monitor
And   a second NE in "pre_empenho" carrying 3 units of it
When  the item's saldo is read
Then  quantidade_disponivel is 12
And   the ATA's value saldo is unaffected by how that quantity is distributed
```

**AC-0006-11** — Quantity and value can disagree about exhaustion
```gherkin
Given an ATA with saldo disponível of R$ 500.000,00
And   an ITEM_ATA whose quantidade_disponivel is 0
When  the ATA's saldo view is read
Then  it reports the ATA as having budget available
And   it flags that item as esgotado
```
A single "saldo" number would hide this. The buyer needs to see that the money
is there and the item is not.

**AC-0006-12** — Aditivo de quantidade raises the item ceiling (RN15)
```gherkin
Given an ITEM_ATA with contracted quantidade 100 and 100 already committed
When  a gestor registers an aditivo de quantidade of 25%
Then  quantidade_disponivel becomes 25
And   an aditivo above 25% is rejected with error code "ADITIVO_ACIMA_DO_LIMITE"
```

**AC-0006-13** — Reserved reads in parentheses until the empenho is issued (OQ-03, ADR-0015)
```gherkin
Given an item of an ATA with quantidade 1.000
When  an NE of 300 units of it is in "pre_empenho"
Then  quantidade_disponivel is 700 and quantidade_reservada is 300
And   a screen shows "700 (300)"
When  that NE is issued, "ne_emitida"
Then  quantidade_disponivel is 700, quantidade_reservada is 0 and quantidade_empenhada is 300
And   a screen shows "700"
```
The same holds in value: `saldo_disponivel` is the same before and after emission.

**AC-0006-14** — A delivery never changes the ATA's saldo
```gherkin
Given the NE of AC-0006-13, issued
When  an NF of 100 units of that item is launched against it
Then  quantidade_disponivel is still 700 and valor_empenhado is unchanged
```

**AC-0006-15** — The NE shows what is still missing
```gherkin
Given an issued NE of 300 units of an item
When  an NF of 100 units is launched against it
Then  quantidade_faltante is 200
When  a second NF of 200 units is launched
Then  quantidade_faltante is 0
Given an NF of 100 units that is in quarantine, or "devolvida"
Then  it does not reduce quantidade_faltante
And   the NE shows that 100 units arrived and are in quarantine, when it is in quarantine
```
A line above `quantidade_faltante` has no rule yet (OQ-46).

## 4. Runway projection (RF21)

The colleague contribution in the RFC appendix (burn-rate projection: "at this
rate the saldo runs out in ~40 days, but vigência ends in 90") is a pure
read-model addition over the same ledger — `Σ valor_empenhado / elapsed days`
against `vigencia_fim`. It requires no schema change, which is precisely why the
derived-saldo design is worth its cost.

*(2026-09-02)* This left the deferred list. It was postponed for lack of
consumption history; the entity exports that history today
(`MÉDIA DE CONSUMO POR ITENS`, 15.721 rows). It now needs a spec of its own, and
its most-requested form came from the 17/08 meeting — *"olhando o nosso consumo
atual, quanto tempo de estoque essa ata vai durar"*, which is runway measured
against consumption rather than against elapsed spend.

## Revision history

**v0.4 (2026-10-06)** — the stakeholder's example fixes the model. The formula is
ADR-0003's again, `valor_contratado − valor_reservado − valor_empenhado`, and
issuing the NE does not change saldo; only its presentation does (`700 (300)`,
then `700`). Delivery is a separate view per NE item, `quantidade_faltante`,
counted from the NFs launched and never part of saldo (§2.3). AC-0006-02 and
-03 name the committed share `comprometimento_percentual`, AC-0006-01, -04 and
-06 follow, and AC-0006-13 to -15 are new. An earlier text of this version read
"consumo" as a third saldo term, counted from an approved NF; the answer of
2026-10-06 showed that was a misreading, and it was removed before review. No
existing AC was renumbered.

**v0.3 (2026-09-02)** — saldo is now defined in **two units**. §2 splits into
value-per-ATA and quantity-per-item, both derived; AC-0006-02, -05, -06 and -07
are rewritten to aggregate over `ITEM_NOTA_EMPENHO` (ADR-0007); AC-0006-10, -11
and -12 are new, covering quantity saldo, the case where money and quantity
disagree about exhaustion, and the 25% aditivo ceiling (RN15). No existing AC was
renumbered.

**v0.2 (2026-09-02)** — recorded the empirical support for ADR-0003 and the gap
that v0.3 closes.

## 5. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF14, §2.5 RN10, Tela 5 |
| 0.2 | 2026-09-02 | ADR-0003 confirmed empirically (32,5% divergence in the source spreadsheet); aggregation moves to ITEM_NOTA_EMPENHO (ADR-0007); quantity-saldo gap recorded (OQ-20); RF20/RF21 unblocked on data |
| 0.3 | 2026-09-02 | Saldo defined in value and quantity (OQ-20); ACs 02, 05, 06, 07 rewritten over ITEM_NOTA_EMPENHO (ADR-0007); ACs 10–12 added; RF21 leaves the deferred list |
| 0.4 | 2026-10-06 | The stakeholder's example (question 6 and its follow-up): the formula stays `valor_contratado − valor_reservado − valor_empenhado` and emission does not change it, only how it is shown (`700 (300)`, then `700`). Delivery is a separate per-item view, `quantidade_faltante`, counted when an NF is launched and never part of saldo (ADR-0015, OQ-03 resolved, OQ-46 opened). ACs 02 and 03 name `comprometimento_percentual`; ACs 01, 04 and 06 adjusted; ACs 13 to 15 added; depends on SPEC-0005 |
