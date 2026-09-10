---
id: SPEC-0006
title: Saldo por ATA (visão derivada)
status: Draft
version: 0.3
owner: Isaac Kleimann Graper
satisfies: [RF14, RN10, RN15]
depends_on: [SPEC-0002, SPEC-0004]
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

### 2.2 Quantity, per item

```
quantidade_disponivel(item_ata) =
      item_ata.quantidade                -- contracted, plus aditivos de quantidade
    - Σ ITEM_NOTA_EMPENHO.quantidade     -- where the parent NE is in a reserving
                                         -- or committed state
```

This is the figure the buyer actually decides on: an ATA can hold budget while
the item it covers is exhausted. `RN10` blocks on whichever runs out first
(AC-0004-24).

NEs in `demanda`, `validacao_saldo` and `cancelada` contribute nothing to either.
Reservation begins at `pre_empenho` — the first stage past the saldo guard — and
converts to commitment at `ne_emitida`.

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
`consumo_percentual` is 0.

**AC-0006-02** — The worked example from Tela 5 reproduces exactly: ATA 002/2026
at R$ 2.840.000,00 with one NE in `ne_emitida` whose itens total R$ 78.000,00
yields saldo R$ 2.762.000,00 and consumo 3% (rounded to the nearest whole
percent). A second test splits the same R$ 78.000,00 across four itens and
asserts an identical result — the saldo depends on the sum, not on how the NE is
composed.

**AC-0006-03** — Consumption at or above 80% flags the ATA as
`alto_consumo = true` (RF14); a test at 79.9%, 80.0% and 80.1% pins the boundary.

**AC-0006-04** — Aditivos raise `valor_contratado` and therefore lower
`consumo_percentual` without any NE changing.

**AC-0006-05** — Cancelling an NE in a reserving state releases its value **and
the contracted quantity of every one of its itens** in the same transaction.

**AC-0006-06** — Saldo is computed from the NE ledger on every read; a test
mutates `ITEM_NOTA_EMPENHO` rows directly in the database and asserts the next
read reflects it with no refresh step. This is what distinguishes a derived value
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
