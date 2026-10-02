---
id: SPEC-0003
title: Catálogo de insumos
status: Draft
version: 0.3
owner: Isaac Kleimmann Graper
satisfies: [RF03, RF07, RF11, RN14]
depends_on: [SPEC-0001, SPEC-0002]
milestone: M2
---

# SPEC-0003 — Catálogo de insumos

## 1. Purpose

The insumo catalogue is where nomenclature consistency with DOMS is won or lost.
A.V.'s reported pain — "integração entre plataformas dificulta a nomenclatura e
especificidade dos itens, causando retrabalho" — is addressed here or not at all.

## 2. A resolved contradiction

RF03 says the insumo carries "ATA vinculada". The data model uses `ITEM_ATA` as
an N:N join. Both cannot be true: an insumo owned by one ATA cannot be reused,
and the same paper appearing in three ATAs would be three catalogue entries with
three codes, destroying DOMS correspondence.

**Resolution:** the insumo is a global catalogue entry with a unique `sku`. Its relationship to ATAs is exclusively through `ITEM_ATA`, which
carries quantity and unit price. Tela 3's "ATA" column shows the ATAs an insumo
participates in, not an ownership field. (OQ-01)

## 3. Behaviour

**AC-0003-01** — A servidor registers an insumo with `sku`, `descricao`,
`categoria` and `unidade`; `quantidade_referencia` is optional. `codigo_doms` and
`codigo_externo` are optional and exist only to join with the DOMS exports.

**AC-0003-02** — `sku` matches the SKU pattern (configurable, default
`^[A-Z0-9]+$`, which fits the two examples in the CAME sheet, `CLORDEG21` and
`SER5D`); a mismatch returns 422 `INVALID_SKU` with a message showing the
expected format and an example (RF07). `codigo_doms`, when given, is digits only
(`26829`); a value such as `2888.0`, which is how the source files spell some
codes, is rejected rather than trimmed, with 422 `INVALID_DOMS_CODE`.

**AC-0003-03** — `sku` is globally unique, and so is `codigo_doms` when present; a
duplicate returns 409 naming the existing insumo, so the operator reuses it
rather than inventing a variant.

**AC-0003-04** — `sku` is immutable once referenced by any `ITEM_ATA`
(RN14); an edit attempt returns 409 `SKU_IMMUTABLE`.

**AC-0003-05** — `quantidade_referencia` is a process-alert threshold only. No
endpoint, report or calculation treats it as stock on hand. A test asserts that
saldo computation is unaffected by any value of this field.

**AC-0003-06** — Importing a CSV with columns `sku, codigo_doms, nome, categoria,
unidade, estoque, minimo, ata` maps `minimo → quantidade_referencia`, does not
write `estoque` onto the insumo, and links `ata` by creating `ITEM_ATA` rows.
The import report states that `estoque` is handled by the coverage importer
(§4, ADR-0008), not that it was discarded. **A row with no `sku` is refused, by
line number**: the DOMS export carries only its own code, which is not the
item's identity, so the operator joins it to the SKU sheet before importing
(OQ-43).

**AC-0003-07** — Import is atomic per file, with a per-row failure report
(same rule as AC-0002-07).

**AC-0003-08** — Import is idempotent: re-uploading the same file updates
existing insumos by `sku` rather than creating duplicates, and the report
distinguishes created from updated rows.

**AC-0003-09** — `categoria` comes from a controlled list (Expediente, TI, Saúde,
Limpeza, Mobiliário), extensible by a gestor. Free-text categories reintroduce
exactly the nomenclature drift this module exists to prevent.

**AC-0003-10** — An insumo referenced by an `ITEM_ATA` cannot be deleted, only
deactivated.

## 4. Note on the `estoque` column

*(Revised 2026-09-02 — ADR-0008.)* v0.1 said SIGI discarded the DOMS stock
figure outright, on the grounds that importing it would create a second source
of truth. That reasoning held while the boundary forbade all stock data; ADR-0008
narrowed it to forbid stock SIGI **computes or mutates**.

The figure is now ingested, but **not by this spec and not into `INSUMO`**. It
lands in `POSICAO_ESTOQUE_SNAPSHOT` — import-only, keyed by `data_referencia`,
with no write path — under the coverage spec that ADR-0008 requires and that does
not exist yet.

So the catalogue importer still ignores `estoque`, and AC-0003-06 stands as
written. What changes is the reason: not "SIGI does not hold stock", but "stock
does not belong on the catalogue entry". The import report should say the column
is handled elsewhere rather than discarded, so an operator does not conclude the
data was lost.

## Revision 2026-09-02 — validated against operational data

**Item identity is plural.** This spec and RN14 assume one `codigo`, globally
unique and immutable. The data carries four identifiers for the same item: the
CAME `SKU` (`CLORDEG21`), the DOMS client code (`26829`), the DOMS surrogate
`mercadoriaId` (`3678`), and `Nº ITEM` (a position within a pregão, not an
identity). `INSUMO` gains `sku` and `codigo_externo` so imports can join on
whichever the source provides; `codigo` remains the DOMS client code. See OQ-29.
*(Superseded 2026-10-02: the stakeholder chose the SKU as the identity. See the
revision below.)*

**Categories are a three-level hierarchy.** `categoria` is a flat string; the
source has `Grupo mercadoria` → `SubGrupo Mercadoria` →
`Classificao SubGrupo Mercadoria`, measured at 15 groups and 44 group/subgroup
pairs. Replaced by `GRUPO_MATERIAL`, self-referencing. The 17/08 meeting made
the same point — *"só odontologia tem mais de 400 referências"*.

**Items are substituted and discontinued.** `Controle de ITENS` carries
`ITEM SUBSTITUIDO POR ITEM 43204` and `ITEM DESCONTINUADO`; the CAME dashboard
surfaces it as `SUGESTÕES DE TROCA`. RN14 forbids changing the item's code once
referenced — correctly — but says nothing about substitution, which is the
operation's actual mechanism. Modelled as `substituido_por_id` and
`descontinuado_em`: a link, never a rewrite, so historical NEs stay correct.
Confirmed by the stakeholder on 2026-10-02 (OQ-23), and RN14 now says so.

**Import validation has concrete hazards now.** `data-sources.md` §12 lists what
the real files contain — codes typed as floats (`2888.0` will not join to
`2888`), the item code embedded in the description (`26829 - CLOREXIDINA 2% -
1 L`), leading whitespace on supplier names, and unit prices at five decimal
places (`0,00599`) that `NUMERIC(15,2)` would round to `0,01`. These belong in
this spec's validation ACs.

## Revision 2026-10-02 — the stakeholder chose the SKU

The validation questionnaire asked which of the four codes never changes and
should identify the item. The answer was **"Devemos utilizar o SKU"** (question
3), which reverses the proposal in OQ-29, where `codigo` was the DOMS client code.

- `INSUMO.sku` is the identity: `NOT NULL`, globally unique, immutable once
  referenced (RN14). Every `codigo` in ACs 01 to 04, 06 and 08 became `sku`, and
  the error codes `CODIGO_DOMS_INVALIDO` and `CODIGO_IMUTAVEL` became
  `INVALID_SKU` and `SKU_IMMUTABLE`, in English as ADR-0013 asks of a code with
  no glossary noun in it.
- The DOMS client code gets its own column, `codigo_doms`, optional and unique,
  for joining DOMS exports. `mercadoriaId` stays in `codigo_externo`. The column
  `codigo` no longer exists.
- The SKU is the CAME's own mnemonic, kept in a sheet that maps it to the DOMS
  code. The DOMS exports do not carry it, so a catalogue import needs the SKU
  joined in first. That a SKU exists for every item and is never reused is not
  known: OQ-43.
- The group hierarchy, substitution and the import hazards above are untouched.

## 5. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF03/RF07, Tela 3, mockup 9.2.2.2, §9.5 CAME mapping |
| 0.2 | 2026-09-02 | Four item identifiers recorded (OQ-29); three-level hierarchy replaces flat `categoria`; substitution/discontinuation modelled (OQ-23); concrete import hazards from real files |
| 0.3 | 2026-10-02 | The SKU is the item's identity, by the stakeholder's answer (OQ-29 resolved, reversing the DOMS-code proposal): ACs 01 to 04, 06 and 08 now key on `sku`, the DOMS code moves to `codigo_doms`, and a catalogue import refuses a row with no SKU. Substitution confirmed (OQ-23). OQ-43 opened for SKU coverage |
