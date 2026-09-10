---
name: sigi-domain
description: Domain rules for the SIGI supply-cycle traceability system (ATA, Nota de Empenho, Nota Fiscal, saldo, audit trail). Use whenever writing or reviewing code, specs, tests, UI copy or database changes that touch these concepts, or when a request mentions empenho, saldo, ATA, insumo, fornecedor, DOMS or e-Publica.
---

# SIGI Domain Rules

SIGI tracks the administrative supply cycle of a Brazilian state entity:
`ATA → NE → NF → conclusão`, and surfaces the **coverage** figure that drives
the purchase decision. It is **not** the system of record for physical stock,
and **not** accounting.

Scope is governed by the operational data, not by the RFC — see ADR-0009 and
`docs/architecture/data-sources.md`.

## Vocabulary — never translate

`ATA` (price-registration agreement) · `Nota de Empenho / NE` (budget
commitment) · `Nota Fiscal / NF` (supplier invoice) · `saldo` (available balance)
· `insumo` (supply item) · `fornecedor` · `vigência` · `aditivo` · `reajuste` ·
`Processo SEI`. These appear in Portuguese in code, database, API paths and UI.
Full list: `docs/product/glossary.md`.

## The five invariants

1. **NF binds to NE, never to ATA.** The ATA link is inherited through the NE.
   No route, schema or column may offer a direct NF→ATA link.
2. **The NE flow is sequential:** `demanda → validacao_saldo → pre_empenho →
   envio_fornecedor → ne_emitida`. No skipping. Reversal is one step, gestor
   only, justification mandatory and recorded. `ne_emitida` is terminal.
   **An NE carries many insumos** (`ITEM_NOTA_EMPENHO`) — 27,8% of real ones do,
   up to 37. Status lives on the header: there is no per-item status and no
   partially advanced NE (ADR-0007).
3. **Saldo is derived:** `valor_contratado − valor_reservado − valor_empenhado`,
   aggregated over `ITEM_NOTA_EMPENHO` (ADR-0007). There is no `saldo` column
   and no operation that writes one. Reservation begins at `pre_empenho`;
   commitment at `ne_emitida`.
   **Estoque is imported, not derived and not computed.** A dated snapshot from
   DOMS, written only by the importer, always displayed with its
   `data_referencia` (ADR-0008). `saldo` ≠ `estoque`: different sources,
   different meanings, never summed.
4. **The audit trail is append-only**, enforced by PostgreSQL privileges and a
   trigger. Every mutation writes a history row in the same transaction as the
   mutation. If the history write fails, the mutation fails.
5. **No API calls to DOMS or e-Publica.** Consistency comes from format
   validation and CSV import. Do not write an HTTP client for them.

## Roles

| | gestor | servidor | auditor |
| --- | --- | --- | --- |
| ATAs, NEs, members | full CRUD | — | read |
| Advance an NE stage | ✅ | ✅ | ❌ |
| Reverse / cancel | ✅ with justification | ❌ | ❌ |
| Insumos, NFs | ✅ | ✅ | read |
| Reports and exports | ✅ | read | ✅ |

Enforced server-side on every endpoint. Frontend checks are cosmetic.

## Recurring mistakes to avoid

- Adding a mutable `saldo` column "for performance". This reverses ADR-0003 —
  and the entity's own spreadsheet shows why: it keeps `SALDO` beside
  `SALDO CALCULADO`, and 32,5% of rows disagree.
- Writing to a stock snapshot from anywhere but the importer, or showing a
  snapshot figure without its `data_referencia`. This reverses ADR-0008.
- Treating imported `estoque` as SIGI's own state, or summing it with `saldo`.
- Treating `quantidade_referencia` as stock on hand. It is a process alert only.
- Modelling an NE as single-item. See ADR-0007.
- Binding an NF to an ATA because the UI shows an ATA column. It is inherited.
- Checking saldo and writing status in separate transactions. Use
  `SELECT ... FOR UPDATE`.
- `float` for money. Use `Decimal` / `NUMERIC(15,2)`.
- Generic error messages. Every validation failure names its field, in pt-BR,
  and says what to do — this is the mitigation for the transcription errors that
  motivated the project.
- Calling CSV import "integração". It is not; the word sets a false expectation
  with stakeholders.
