# ADR-0008 — Ingesting stock signals from DOMS without becoming an inventory system

- **Status:** Accepted (by ADR-0009, 2026-09-02)
- **Date:** 2026-09-02
- **Deciders:** Isaac Kleimann Graper (product owner), 2026-09-02
- **Related:** ADR-0002, ADR-0003, ADR-0009, RF20, RF21, OQ-25, `docs/architecture/data-sources.md`

## Context

`vision.md` states the boundary in load-bearing terms: *"Physical inventory
control. The saldo view is a consequence of the empenho cycle, not an independent
stock module… it is why there is no 'entrada de estoque' operation anywhere in
the system."* `CLAUDE.md` invariant 5 and the `sigi-domain` skill repeat it, and
name "adding a `saldo` or `estoque` column" as a recurring mistake.

Two things now sit against that boundary.

**The 17/08 meeting.** The stakeholders described their operating loop as
coverage-driven: coverage equals stock divided by consumption; below three
months triggers a purchase, conditioned on whether the ATA is current and has
saldo. The CAME dashboard is organised around that loop.

**The export contract.** `ESTOQUE CONSOLIDADO (CSV)` already carries
`curvaAbc`, `curvaXyz`, `estoqueMinimo`, `pontoPedido`, `estoqueMaximo`,
`diasEstoque` and `demandaDiaria`. `COBERTURA DE ESTOQUE (CSV)` carries
`estoqueAtual`, `demandaMensal` and `diasEstoque`, refreshed monthly.

So the question is not whether SIGI should *build* inventory management. DOMS
has already built it. The question is whether SIGI may *read* the result.

`RF20` (coverage-profile alerts) was deferred post-MVP with the justification
*"requires consumption-rate history that will not exist at launch."* That premise
is now false: `MÉDIA DE CONSUMO POR ITENS` holds 15.721 rows and
`COBERTURA DE ESTOQUE` 5.290.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Hold the line: ingest nothing | Boundary stays trivially clear; no new failure modes | The product cannot answer the question its users actually ask. The CAME spreadsheet survives alongside SIGI, and the fragmentation the project exists to end continues |
| Ingest the signals read-only, as a dated snapshot | Answers the coverage question; no stock arithmetic in SIGI; the boundary stays enforceable because there is no write path | A stale snapshot can mislead; "SIGI says we have stock" becomes a sentence people say. Requires visible dating |
| Own stock: entries, exits, balances | One system, always current | Reverses ADR-0003 and invariant 5; makes SIGI the system of record for something DOMS already owns; two sources of truth for physical stock — the exact failure ADR-0003 was written to avoid |

## Decision

SIGI ingests stock signals **as an observation, never as a state it maintains**.
Concretely:

1. A `POSICAO_ESTOQUE_SNAPSHOT` table holds imported rows keyed by
   `(insumo_id, unidade_id, data_referencia)`, carrying `estoque_atual`,
   `demanda_mensal`, `dias_estoque`, `curva_abc`, `estoque_minimo`,
   `ponto_pedido` — values copied verbatim from the export.
2. **No write path.** No endpoint, service or UI action changes a snapshot
   value. The only writer is the importer. There is no `entrada de estoque`,
   no adjustment, no recount. Invariant 5 is preserved in the sense that
   matters: SIGI never computes or mutates a stock balance.
3. Every surface displaying a snapshot value shows its `data_referencia`. A
   figure whose provenance is not visible is indistinguishable from one SIGI
   computed, and that confusion is what erodes the boundary.
4. `saldo` (ATA/empenho, `ADR-0003`) and `estoque` (physical, imported) are
   distinct concepts with distinct names, never summed, never shown as one
   number. The glossary must separate them explicitly.
5. Scope stays negative where it was: no reorder-point arithmetic of SIGI's own,
   no forecasting, no ML. SIGI reads `pontoPedido`; it does not compute one.

## Consequences

**Positive** — `RF20` and `RF21` become implementable from real data instead of
deferred on a premise that no longer holds. The coverage question the
stakeholders actually ask gets an answer inside the product, which is the
condition for retiring the spreadsheet.

**Negative** — A monthly snapshot is stale for up to a month, and users will
read it as current unless the dating is prominent. It adds an import path, its
validation surface — the strict-import rules in `data-sources.md` §12 — and
its failure modes. It also softens a boundary
that was previously absolute and therefore easy to police in review: "no stock
data in SIGI" becomes "no stock data SIGI computes or mutates", which is a
subtler rule that reviewers must actually understand. `CLAUDE.md` invariant 5
and the `sigi-domain` skill must be reworded, or they will read as forbidding
this.

**Follow-up**

- Reword `CLAUDE.md` invariant 5 and `sigi-domain`'s "recurring mistakes" so
  they forbid *computed or mutable* stock, not *imported and dated* stock.
- Amend `vision.md`'s "What SIGI is not" with the same distinction.
- New spec for the import; `RF20`/`RF21` leave the deferred list in
  `traceability.md`.
- Settle the cadence question (OQ-25): monthly is what the entity runs today.

**Resolution (2026-09-02)** — This ADR was raised as `Proposed` because
`CLAUDE.md` requires stopping and asking when a task appears to break an
invariant. The product owner has since ruled that the shared operational sources
govern (ADR-0009). Under that hierarchy the question answers itself: the
entity's loop is coverage-driven, so SIGI must represent it. The reading offered
above — that invariant 5 forbids *computed or mutable* stock, not *imported and
dated* stock — is adopted, and the safeguards in the decision are what keep it
honest. `ADR-0003` is untouched: `saldo` remains derived from the NE ledger and
is never conflated with imported `estoque`.
