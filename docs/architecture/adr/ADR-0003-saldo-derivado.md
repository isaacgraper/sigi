# ADR-0003 — Saldo is derived, never stored

- **Status:** Accepted
- **Date:** 2026-05-22
- **Related:** RF14, RN10, SPEC-0006, ADR-0007

## Context

Saldo per ATA is the most-consulted figure in the product and the one an auditor
is most likely to challenge. The obvious implementation — a `saldo` column
decremented on each NE — is faster to read and simpler to write.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Stored mutable `saldo` column | Trivial reads | Any missed decrement, failed transaction, manual fix or new code path desynchronises it permanently. Reconciliation becomes a recurring operational task. Two sources of truth. |
| Derived from the NE ledger | Cannot desynchronise; the ledger is the audit trail | Aggregate cost on every read; needs care to meet RNF01 |
| Derived + materialised view refreshed in the write transaction | Fast reads, single source of truth | Slightly more complex writes |

## Decision

Saldo is a pure function of the NE ledger:
`valor_contratado − valor_reservado − valor_empenhado`. No mutable saldo column
exists. If reads outgrow the aggregate, a materialised view refreshed **inside
the same transaction as the NE state change** is permitted; an asynchronous
refresh job is not.

A three-state model (contratado / reservado / empenhado) is introduced because
the RFC validates saldo at `validacao_saldo` but deducts at `ne_emitida`,
leaving a window in which two concurrent NEs can each pass validation and
jointly exceed the ATA.

## Consequences

**Positive** — "The saldo is wrong" becomes structurally impossible; it can only
be "the NE ledger is wrong", which is visible, auditable and correctable. The
post-MVP runway projection (RF21) becomes a read-model addition with no schema
change.

**Negative** — Every saldo read is an aggregation, so indexes and the p95 budget
(AC-0006-07) need active attention. Developers accustomed to a stock-balance
column will repeatedly propose adding one; CLAUDE.md names this explicitly so the
proposal is caught in review rather than in a migration.

**Follow-up** — AC-0006-06 asserts derivation by mutating NE rows directly and
reading saldo with no refresh step. If that test is ever weakened, this decision
has been silently reversed.

## Empirical support (added 2026-09-02)

The stakeholders' own workbook contains the experiment this ADR describes in the
abstract. `Controle CAME 2026 › Controle de ITENS` keeps two columns side by
side: `SALDO`, maintained by hand, and `SALDO CALCULADO`, derived.

| Rows carrying both | Divergent | Share |
| --- | --- | --- |
| 951 | **309** | **32,5%** |

A third of the stored balances disagree with the derived ones, in the very
spreadsheet SIGI is meant to replace. The "Negative" consequence above — that
developers will repeatedly propose a stored balance column — now has a number
attached to what that costs. Reproduce with `scripts/analise-planilhas.py`.

Note also that the operation tracks saldo **per item, in quantity**
(`TOTAL DA ATA` / `COMPRADO` / `SALDO`), while this ADR defines it **per ATA, in
value**. Both are real and only one is modelled; see OQ-20 and
`docs/architecture/data-sources.md` §10.

Aggregation moves down one level as a result of ADR-0007: saldo is computed over
`ITEM_NOTA_EMPENHO`, not `NOTA_EMPENHO`. The decision itself is unchanged.

