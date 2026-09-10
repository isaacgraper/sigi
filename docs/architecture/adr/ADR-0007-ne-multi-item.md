# ADR-0007 — A Nota de Empenho carries multiple insumos

- **Status:** Accepted
- **Date:** 2026-09-02
- **Deciders:** Isaac Kleimann Graper, pending confirmation by Anderson Viebranz
- **Related:** SPEC-0004, SPEC-0006, OQ-05, OQ-06, RF13, RN09, ADR-0003

## Context

`OQ-05` asked whether one NE can cover several insumos and recorded the
assumption "MVP: one item per NE", with a warning attached: *"if real NEs are
multi-item, this is a data-model change, and it is far cheaper now than in M4."*

The stakeholders supplied their operational workbook on 2026-09-02. Measured on
`Controle CAME 2026 › EMPENHOS`:

| Distinct empenhos | Covering more than one SKU | Share | Largest |
| --- | --- | --- | --- |
| 482 | 134 | **27,8%** | **37 insumos in one NE** |

Multi-item is not an edge case. `NOTA_EMPENHO` currently holds `item_ata_id`,
`ata_id`, `insumo_id`, `quantidade` and `valor` directly, so it can represent
exactly one item. Roughly a quarter of real empenhos cannot be recorded at all,
and the largest would need 37 rows pretending to be one document.

The cost of deferring is not linear. `SPEC-0004`'s state machine, `SPEC-0006`'s
saldo aggregation and `DB2`'s consistency trigger are all written against the
one-item shape, and each acquires tests as milestones progress.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Keep one item per NE; model a multi-item empenho as N sibling NEs sharing `processo_sei` | No schema change now | The NE número is the document identity; N rows with one número breaks `numero UNIQUE`. Advancing the flow per sibling permits a half-committed empenho, which does not exist administratively. Saldo per document becomes a group-by over a convention rather than a relationship |
| `ITEM_NOTA_EMPENHO` child table | Matches the document; state stays on the NE where the administrative act lives; saldo aggregates over a real FK | Migration touches the core; `SPEC-0004` and `SPEC-0006` need revision; the OQ-06 denormalisation must move or go |
| Defer to post-MVP | Ships M2 sooner | Guarantees the change lands in M4 with tests, fixtures and possibly production data attached — the outcome OQ-05 explicitly warned against |

## Decision

`NOTA_EMPENHO` becomes a header. A new `ITEM_NOTA_EMPENHO` holds one row per
insumo committed by that NE:

```
ITEM_NOTA_EMPENHO
  id UUID PK
  nota_empenho_id  FK → NOTA_EMPENHO
  item_ata_id      FK → ITEM_ATA
  quantidade       NUMERIC
  valor_unitario   NUMERIC(15,4)
  valor            NUMERIC(15,2)     -- quantidade × valor_unitario
  UNIQUE (nota_empenho_id, item_ata_id)
```

Consequences of that shape, each binding:

1. `NOTA_EMPENHO.quantidade`, `.valor`, `.item_ata_id`, `.insumo_id` are
   removed. `NE.valor` becomes `Σ ITEM_NOTA_EMPENHO.valor`, derived — the same
   reasoning as ADR-0003, applied one level down.
2. `NOTA_EMPENHO.ata_id` **stays**. Every item of an NE belongs to the same ATA;
   the FK carries that invariant instead of leaving it to convention. A trigger
   asserts that every `item_ata_id` resolves to `NOTA_EMPENHO.ata_id`. This
   replaces `DB2` and narrows OQ-06, which asked about a redundancy that no
   longer exists in the same form.
3. **Status stays on the header.** The five-stage flow describes the
   administrative document, not the line. There is no per-item status, no
   partially advanced NE. `ADR-0005` is unaffected.
4. Saldo reservation and commitment (`ADR-0003`) aggregate over
   `ITEM_NOTA_EMPENHO`, not `NOTA_EMPENHO`. `SPEC-0006`'s three quantities keep
   their definitions; only the aggregation path changes.
5. `RN09` — an NE must carry Processo SEI, ATA, insumo, quantity and estimated
   value before it is opened — is read as: at least one `ITEM_NOTA_EMPENHO`,
   each with quantity and value. An NE with zero items cannot leave `demanda`.

## Consequences

**Positive** — The model can represent the documents the entity actually issues,
including the 37-item one. Saldo is computed from the level at which quantity
exists. `NF → NE` (`RN02`) is untouched, since NFs bind to the document.

**Negative** — This is a core change made before any code exists, which is the
cheapest moment, but it is still a change to the spine of the product. Every
`AC-0004-*` that names quantity or value on the NE needs rewriting, and
`SPEC-0006`'s aggregation ACs change shape. A multi-item NE also raises a
question the entity has not been asked: whether an item can be removed from an
NE after `pre_empenho`, when saldo is already reserved. Recorded as OQ-27 rather
than answered here.

**Follow-up**

- `docs/architecture/data-model.md` — add the entity, remove the moved columns,
  replace `DB2`.
- `SPEC-0004` — revise the ACs that assume one item; add ACs for an empty NE and
  for duplicate `item_ata_id`.
- `SPEC-0006` — re-express the aggregation over `ITEM_NOTA_EMPENHO`.
- `OQ-05` → `Resolved`; `OQ-06` → narrowed; `OQ-27` opened.
- Confirm with Anderson Viebranz that a 37-item empenho is ordinary and not a
  spreadsheet artefact. The decision does not depend on the answer — one
  multi-item empenho is enough to require the table — but the answer shapes the
  UI.
