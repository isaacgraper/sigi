# ADR-0015 — Saldo is consumed on delivery, not on emission

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Isaac Kleimmann Graper, on the stakeholder's answer
- **Amends:** ADR-0003 (the formula's third term; the decision that saldo is derived stands)
- **Related:** ADR-0007, ADR-0008, ADR-0009, OQ-03, OQ-40, RN10, RN12, RF14, SPEC-0004, SPEC-0005, SPEC-0006

## Context

ADR-0003 fixed saldo as `valor_contratado − valor_reservado − valor_empenhado`
and OQ-03 proposed that an NE reserves from `pre_empenho` and is committed at
`ne_emitida`. That proposal was `Assumed`, not stated by anyone at the entity.

The validation questionnaire asked about it (question 6). The answer confirmed
the reservation and moved the rest: *"Esta correta a afirmação da reserva a
partir do pré-empenho, porém o consumo deve ser considerado apenas depois desta
entrega ser realizada e este volume entrar em estoque."* A direct stakeholder
statement outranks this repository's ADRs (ADR-0009), so the proposal gives way.

Two facts make the answer harder to apply than to read:

- SIGI does not record stock entries and never infers stock (ADR-0008), so "the
  volume enters stock" has to be seen through something SIGI does hold.
- The NF carries a total value and no item lines (SPEC-0005, RN05).

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| A. Keep consumption at `ne_emitida` | No change | Counts as consumed what has not arrived, which the stakeholder said is wrong |
| **B. Consume when an NF bound to the NE is `aprovada`, in value** | Uses what SIGI holds (NF, RN02, RN12); an NE delivered in several NFs consumes in several steps | The quantity of each item cannot be split between reserved and consumed, because the NF has no item lines |
| C. Consume when the stock snapshot rises | Matches "enters stock" literally | The snapshot is monthly and carries no link to an NE; ADR-0008 forbids SIGI inferring stock |
| D. B, plus item lines on the NF | Exact quantity | A new entity, without evidence that the entity registers NFs by item. Deferred |

## Decision

Option B.

1. **Saldo is still derived, never stored** (ADR-0003 stands). Its formula
   becomes `saldo_disponivel = valor_contratado − valor_reservado − valor_consumido`.
2. `valor_comprometido` is the value of the NEs in `pre_empenho`,
   `envio_fornecedor` and `ne_emitida`. `valor_consumido` is the value of the NFs
   in `aprovada` bound to those NEs. `valor_reservado` is the difference.
3. **Reserved and consumed together are exactly what is committed**, so
   `saldo_disponivel = valor_contratado − valor_comprometido`. Approving an NF
   moves value from one subtraction to the other and never changes what a new NE
   may claim. The guard of RN10 behaves as before.
4. **Emission changes nothing in saldo.** `valor_empenhado`, the value of the NEs
   in `ne_emitida`, stays as a derived reporting figure for the budget-execution
   report and the runway projection. It is subtracted from nothing.
5. **An approved NF is the delivery event.** It is the receipt the entity's
   staff confirm, and the only delivery evidence SIGI holds. Whether it is also
   the moment the volume enters stock is OQ-40, `Assumed`.
6. **Quantity per item stays committed as a whole**, reserved-or-consumed, until
   NFs carry item lines (option D). `quantidade_disponivel` is unaffected.
7. RF14's 80% flag measures the **committed** share, not the delivered one: the
   buyer needs to know how little is left to promise, and that does not wait for
   deliveries.

## Consequences

**Positive** — the saldo a new NE can claim is the same as before, so nothing
that decides a purchase moves. What changes is what the figures mean, and they
now match how the entity talks: *reservado* is what is on its way, *consumido* is
what has arrived. AC-0005-10's old guarantee, that approval never deducts twice,
survives intact. The ledger stays the only source (ADR-0003).

**Negative** — an NE that is issued and never delivered keeps its value
reserved, and `ne_emitida` is terminal (AC-0004-11), so there is no way to
release it. That was already true when issuance committed the value; it becomes
visible now that "reserved" reads as "still owed". Releasing an undelivered NE
needs its own instrument and is not specified. SPEC-0006 now reads one more
table, so AC-0006-07's p95 budget has to be re-measured.

**Follow-up**

- Invariant 5 in `CLAUDE.md` is reworded to the new formula; RN17 states the rule.
- SPEC-0004 v0.4, SPEC-0005 v0.3 and SPEC-0006 v0.4 carry the criteria.
- Confirm with the stakeholder that the approved NF is when the volume enters
  stock, and whether NFs should list their items (OQ-40).
