# ADR-0016 — The unit price keeps five decimals; every total keeps two

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Isaac Kleimmann Graper (product owner)
- **Related:** SPEC-0003 (AC-0003-20, -21), SPEC-0004, SPEC-0006, ADR-0003, `data-sources.md` §12

## Context

The project rule is that money is `Decimal` and `NUMERIC(15,2)`. The entity's files
break it in one place: unit prices. `data-sources.md` §12 measured `valorUnitario`
`0,00599`, and money written as text with five places, `R$ 4.892,88000`. Stored at
two places, `0,00599` becomes `0,01`, a 67% error, and multiplied over a thousand
units it moves R$ 4,01 that nobody contracted.

`data-model.md` had `ITEM_ATA.valor_unitario NUMERIC(15,4)`, which keeps `4,582` but
still loses `0,00599`. Totals are another matter: an ATA's value, an aditivo, a
reserved or committed amount and saldo are all paid or accounted in centavos.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Two places everywhere | One rule, no exception | Corrupts measured prices: `0,00599` → `0,01` |
| Four places on the unit price | What the model said | Still loses `0,00599` |
| **Five places on the unit price, two on everything else** | Holds every price in the files; totals stay in centavos | One column is the exception, and the rounding of a product has to be stated |
| Five places everywhere | No rounding question | Saldo and NE values in fractions of a centavo nobody pays |

## Decision

- `ITEM_ATA.valor_unitario` is `NUMERIC(15,5)`. A value with more than five places is
  refused, never rounded (AC-0003-20).
- Every other amount stays `NUMERIC(15,2)`: the ATA's value, aditivos, NE values,
  saldo and every figure derived from them.
- An item's value is `quantidade_contratada × valor_unitario`, computed exactly in
  `Decimal` and rounded **once, half up, to the centavo**, on the way out
  (AC-0003-21). It is not stored. A sum over items adds those rounded values.
- An NE copies the unit price with its five places when it opens (SPEC-0004), so a
  later correction to the item never changes an issued NE.

Compliance is checkable: one `NUMERIC(15,5)` column in the schema, and no
`quantize` to two places anywhere but where a product becomes an amount.

## Consequences

**Positive** — every unit price in the files is stored as written. Totals, saldo and
the screens stay in centavos, which is how the entity reads them.

**Negative** — a rounding rule now exists and has to be the same in every place that
turns a price into an amount: the item's value, the NE item's value, the saldo
calculation. A sum of rounded item values can differ by centavos from the rounded
product of the sums; the item's own rounded value is the one that counts. The
frontend shows a unit price with up to five places and every amount with two.

**Follow-up** — `data-model.md` changes `ITEM_ATA.valor_unitario` to `NUMERIC(15,5)`
and `data-sources.md` §12 closes the four-places row; the money rule in `CLAUDE.md`
names this exception; SPEC-0004 copies the price at five places and rounds the NE
item's value by this rule.
