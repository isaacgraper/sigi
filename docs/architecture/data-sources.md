# Data Sources

Status: Draft · Owner: Isaac Kleimann Graper · Date: 2026-09-02

> **This document is a source of truth, not a report about one.** Under
> `ADR-0009` the entity's operational data outranks the specs and the RFC. Where
> this file and a spec disagree, the spec is wrong.

Field-level correspondence between the data the entity can actually export and
the SIGI model. Written after the stakeholders supplied three workbooks on
2026-09-02, one of which — `CSVs_disponeis_para_SIGI.xlsx` — is an explicit
export contract annotated by Eduardo himself.

**The workbooks are not in this repository.** They carry CNPJ, e-mail, operator
usernames and patient names. Reproduce every figure below with:

```bash
python3 scripts/analise-planilhas.py <directory-with-the-xlsx>
```

## Why this document exists

`ADR-0002` settles that there is no API integration: consistency comes from
format validation and CSV import. That decision left a hole — *which* CSVs, with
*which* columns, at *which* cadence. Specs were written against the RFC's prose
description of DOMS, not against a real export. This document closes that hole,
and in doing so contradicts several assumptions the specs were built on.

---

## 1. The export contract

Nine reports, of which the entity's own annotations (workbook sheet `HUB`) rate
only some as usable. Ignoring those annotations would mean building on data the
stakeholders themselves distrust.

| Source (DOMS export) | Rows | Cols | Eduardo's annotation | Use in SIGI |
| --- | --- | --- | --- | --- |
| `COBERTURA DE ESTOQUE (CSV)` | 5.290 | 16 | *"utilizamos todo mês para atualizar a posição do estoque"* | **Primary** — coverage signal |
| `TRANSFERENCIA CONSOLIDADO (CSV)` | 8.461 | 13 | *"considero o relatório mais importante"* | **Primary** — fulfilment per unidade |
| `TRANFERENCIA DE MERCADORIA (CSV)` | 10.857 | 25 | *"seria um dos mais úteis"*, not yet incorporated | **Primary** — item movement, lote, hierarchy |
| `REQUISIÇÃO ENTRE UNIDADES (CSV)` | 12.658 | 30 | individual orders; emergency vs. scheduled | **Primary** — solicitation + cronograma |
| `ESTOQUE CONSOLIDADO (CSV)` | 1.479 | 23 | — | Secondary — ABC/XYZ, reorder points |
| `FORNECEDORES CADASTRADOS` | 945 | 9 | *"infelizmente apenas XLS"* | Secondary — not a CSV |
| `ENTRADAS NFS (CSV)` | 2.304 | 21 | *"não temos uso real para esse csv no momento"* | **Do not ingest** in MVP |
| `PRODUTOS INDISPONIVEIS (CSV)` | 472 | 12 | *"Não utilizamos… muitos itens cadastrados erroneamente, então o fato de estar zerado não indica a necessidade de compra"* | **Do not ingest** — unreliable |

> **There is no ATA export.** No report in the contract carries ATA data. This
> confirms the 17/08 meeting: the ATA does not come from DOMS. ATAs are tracked
> manually in `Controle CAME 2026 › Controle de ITENS`, and some are acquired
> through **Cincatarina** (22 items with ATA status `COMPR. CINCATARINA`, 49 with
> pregão status `Compra CINCATARINA`). See OQ-02 and OQ-19.

---

## 2. `COBERTURA DE ESTOQUE (CSV)` → coverage signal

The report the entity runs monthly to refresh stock position.

| Column | Type / example | SIGI destination |
| --- | --- | --- |
| `unidadeId` · `unidadeNome` | `289` · `CIAD SES CAME - SECRETARIA DA SAUDE` | **no destination** — no `UNIDADE` entity exists |
| `centroCustoId` · `centroCustoNome` | `657` · `CIAD CAME` | **no destination** |
| `mercadoriaId` | `2498` | `INSUMO` — third identifier, see §8 |
| `mercadoriaCdCliente` | `18954` | `INSUMO.codigo` |
| `mercadoriaNome` | `ABAIXADOR DE LINGUA (PACOTE COM 100…` | `INSUMO.descricao` |
| `demandaDiaria` · `demandaMensal` | `9,29` · `278,71` | **no destination** (ADR-0008) |
| `estoqueAtual` | `1102` | **no destination** (ADR-0008) |
| `diasEstoque` | `119` — **days** | **no destination** (ADR-0008) |
| `ultimaEntradaData` | `27/03/2026` | **no destination** |
| `ultimaEntradaDocumento` | `NF:575057/1` | weak link to `NOTA_FISCAL.numero` |
| `ultimaEntradaQuantidade` | `129` | **no destination** |
| `valorUnitario` · `valorTotal` | `4,582` · `5049,364` | compare with `ITEM_ATA.valor_unitario` |

Eleven of sixteen columns have no destination. That is the measure of the gap
between what the entity can supply and what the model is prepared to receive.

---

## 3. `TRANSFERENCIA CONSOLIDADO (CSV)` → fulfilment

The report Eduardo rates highest. It is the only source of the metric the CAME
dashboard leads with, and the model has no equivalent.

| Column | SIGI destination |
| --- | --- |
| `unidadeSolicitanteId` · `unidadeSolicitanteNome` | **no destination** |
| `mercadoriaId` · `mercadoriaCodigoCliente` · `mercadoria` | `INSUMO` |
| `quantidadeSolicitada` | **no destination** |
| `quantidadeAutorizada` | **no destination** |
| `quantidadeAtendida` | **no destination** |
| `quantidadePendente` | **no destination** |
| `quantidadePedenteSemEstoque` | **no destination** — this is the rupture metric |
| `valorUnitario` · `valorTotal` · `estoqueSolicitante` | **no destination** |

**Five quantities, not two.** A fulfilment rate modelled as
`solicitado ÷ atendido` would be wrong: *authorised* is a distinct decision from
*fulfilled*, and *pending for lack of stock* is the number that distinguishes a
supply failure from an administrative refusal.

---

## 4. `REQUISIÇÃO ENTRE UNIDADES (CSV)` → solicitation and cronograma

Thirty columns describing a three-stage approval workflow the model does not
have: `autorização → aprovação → finalização`, each with its own scheduling
window, actor and timestamp.

| Column group | Content | SIGI destination |
| --- | --- | --- |
| `id` · `tipo` · `urgente` | `63344` · `Manual` · `0` | **no destination** |
| `cronograma_autorizacao_inicio/fim` | scheduling window | **no destination** |
| `data_hora_autorizacao` · `autorizador` | who authorised, when | **no destination** |
| `cronograma_aprovacao_inicio/fim` · `data_hora_aprovacao` · `aprovador` | approval stage | **no destination** |
| `data_hora_finalizado` · `finalizador` | closure | **no destination** |
| `cronograma_entrega_inicio/fim` · `entrega` | delivery window | **no destination** |
| `cronograma` | `CAME 6 2026` | **no destination** — the delivery calendar |
| `centro_custo_solicitante` | `PEDIDO QUINZENAL` | **no destination** |
| `unidade_solicitante` / `_atendente` (+ ids) | `Ubsf Comasa - 2511517` | **no destination** |
| `regiao` | `Centro`, `Norte` | **no destination** |
| `status` | `Autorizado pelo solicitante` | **no destination** |
| `valor_solicitado` | `9240,53` | **no destination** |

**Vocabulary trap.** `tipo` inverts the intuitive reading: per the `HUB`
annotation, **`Manual` means the request follows the cronograma**, and
`Administrativa` means it falls outside it. Any code or UI that guesses from the
word will be backwards.

---

## 5. `TRANFERENCIA DE MERCADORIA (CSV)` → movement, lote, hierarchy

Sole source of the three-level material hierarchy and of lote/validade.

| Column | SIGI destination |
| --- | --- |
| `Grupo mercadoria` | `INSUMO.categoria` — **level 1 of 3** |
| `SubGrupo Mercadoria` | **no destination** — level 2 |
| `Classificao SubGrupo Mercadoria` | **no destination** — level 3 |
| `Lote` · `Validade` | **no destination** — required by the expiry-redistribution flow described in the meeting |
| `Marca` · `Fabricante` | **no destination** |
| `Quantidade Embalagem` · `TipoEmpagalagem` | **no destination** — packaging vs. dispensing unit |
| `Status Item Solicitação` · `Status Solicitação` | **no destination** |
| `Patrimonios` | **no destination** |
| `Id Solicitação` · `Data Hora Atendido/Entrega` | **no destination** |
| `Custo Médio` · `Valor Total` · `Quantidade Atendida` | **no destination** |

Measured: **15 groups, 44 group/subgroup pairs.** `INSUMO.categoria` is a single
flat string and cannot express this. The meeting made the same point from the
other direction — *"além dos grupos, tem subgrupos; só odontologia tem mais de
400 referências"*.

---

## 6. `ESTOQUE CONSOLIDADO (CSV)` → inventory parameters

Relevant because it settles a scope argument rather than because SIGI ingests it
today. Every one of these is **computed by the source system already**:

`curvaAbc` · `curvaXyz` · `participacao` · `participacaoAcumulada` ·
`estoqueMinimo` · `pontoPedido` · `estoqueMaximo` · `diasMinimoEstoque` ·
`diasPontoPedido` · `diasMaximoEstoque` · `diasEstoque` · `demandaDiaria` ·
`quantidadeEstoque` · `quantidadeAutorizada`

SIGI does not need to *build* inventory management to use them — it needs to
*read* them. **ADR-0008** adopts that distinction: these land in
`POSICAO_ESTOQUE_SNAPSHOT`, import-only and dated. Ingestion is therefore
**in scope**, and this report moves from "secondary" to a primary source once
the importer exists.

---

## 7. Sources with no destination by decision

**`ENTRADAS NFS (CSV)`** — not ingested in the MVP, on the entity's own advice.
Worth recording what it contains, because it will be argued for later: it links
`empenho` to `numeroDocumento`, confirming the NE→NF binding of `RN02` from real
data, and it carries an **atesto SLA** (`dataHoraPrazoFinalAtesto`,
`situacaoAtesto` ∈ {`Atestado e recebido no prazo`, `…fora do prazo`,
`Sem atesto`}, `prioridadeAtesto` = `Normal 48H`) that `SPEC-0005`'s NF status
model does not represent. See OQ-22.

**`PRODUTOS INDISPONIVEIS (CSV)`** — not ingested. The entity states that a
zeroed item does not imply a purchase need, because many items are registered in
error. A shortage panel built on this column would inherit that error rate. It
does, however, expose `quantidadeReservada`, `quantidadeQuarentena` and
`quantidadeBloqueioLote` — reservation semantics that exist in the source and
are unrelated to the ATA reservation invented in `ADR-0003`. Do not conflate the
two names.

---

## 8. Item identity: four codes, not one

`RN14` states that `insumo.codigo` is globally unique and immutable. The data
carries four independent identifiers for the same item:

| Identifier | Example | Where it lives |
| --- | --- | --- |
| `SKU` | `CLORDEG21`, `SER5D` | CAME internal mnemonic (`SKU` sheet, 1.425 rows) |
| `CÓDIGO` / `mercadoriaCodigoCliente` / `CÓD INTEGRAÇÃO` | `26829`, `916891` | DOMS client code — the closest thing to `INSUMO.codigo` |
| `mercadoriaId` | `3678` | DOMS internal surrogate |
| `Nº ITEM` | `15` | position within a pregão/ATA, not an item identity |

Additionally, `Controle de ITENS` carries item lifecycle the model has no place
for: `ITEM SUBSTITUIDO POR ITEM 43204`, `ITEM DESCONTINUADO`. The CAME dashboard
surfaces the same concept as `SUGESTÕES DE TROCA`. An item that is substituted
keeps historical NEs pointing at the old code — which is exactly the case `RN14`
forbids and the operation performs. See OQ-29 and OQ-23.

---

## 9. Manual sources (not DOMS)

Tracked in `Controle CAME 2026`; these have no export contract and would be
typed into SIGI.

| Sheet | Rows | Feeds |
| --- | --- | --- |
| `Controle de ITENS` | 3.099 | `ATA`, `ITEM_ATA`, processo licitatório |
| `EMPENHOS` | 992 | `NOTA_EMPENHO`, `ITEM_NOTA_EMPENHO`, NF links |
| `MÉDIA DE CONSUMO POR ITENS` | 15.721 | consumption history, group/subgroup |
| `SKU` | 1.425 | identifier mapping |
| `SALDO DE ATAS` *(backup)* | 1.045 | saldo per item, in quantity |
| `ESTOQUE <3` … `>12`, `SEM GIRO`, `POR DEMANDA` | 156 / 167 / 102 / 71 / 278 / 135 / 259 | coverage bands |

### `Controle de ITENS` — where ATA and processo are conflated

| Column | SIGI destination |
| --- | --- |
| `SEI DA ATA` | `ATA.numero` — stored as a number (`1.9596093E7`) |
| `Nº PREGÃO` | `530/2023` — **no destination** |
| `TOTAL DA ATA` · `COMPRADO` · `SALDO` · `SALDO CALCULADO` | `ITEM_ATA.quantidade` — **in quantity, per item**, see §10 |
| `VALOR UNITÁRIO` | `ITEM_ATA.valor_unitario` |
| `STATUS DA ATA` | `ATA.status` — **17 values against an ENUM of 5**, see §11 |
| `STATUS PREGÃO` | **no destination** — 7 values |
| `DATA LIMITE REAJUSTE` | **no destination** — answers part of OQ-08 |
| `VALIDADE` | `ATA.vigencia_fim` |
| `GRUPO DE COMPRAS` · `SUB-GRUPOS DE COMPRAS` | `INSUMO.categoria` (flat) |
| `FORNECEDOR` | `ATA.fornecedor_id` — but see OQ-11 resolution |
| `MARCA` · `OBSERVAÇÕES 01/02` | **no destination** |

---

## 10. Saldo: quantity per item, not value per ATA

`SPEC-0006` and `ADR-0003` define saldo as
`valor_contratado − valor_reservado − valor_empenhado` — **monetary, per ATA**.

The operation tracks `TOTAL DA ATA` / `COMPRADO` / `SALDO` — **quantity, per
item**, and `SALDO DE ATAS` repeats the shape (`TOTAL` `250`, `RESTANTE` `195`).
The purchase decision is taken on the quantity figure; the monetary figure is
what an auditor asks about. Both are real; only one is modelled. See OQ-20.

### Empirical support for ADR-0003

`Controle de ITENS` keeps `SALDO` **and** `SALDO CALCULADO` side by side —
a stored balance next to a derived one.

| Rows carrying both | Divergent | Share |
| --- | --- | --- |
| 951 | **309** | **32,5%** |

A third of the stored balances disagree with the computed ones. ADR-0003
predicted this failure mode in the abstract; here it is, measured, in the
spreadsheet SIGI is meant to replace. Recorded in that ADR.

---

## 11. Two state machines in one column

`STATUS DA ATA` mixes the ATA's own lifecycle with the procurement process that
precedes it:

| Belongs to the ATA | Belongs to the processo licitatório |
| --- | --- |
| `VIGENTE` (770) · `VENCIDA` (608) · `SALDO ZERO` (115) · `PRORROGADA` (66) · `CANCELADO` (2) | `SAP` (414) · `FRACASSADO` (228) · `CONSTRUÇÃO EDITAL` (202) · `EM LICITAÇÃO` (113) · `PGM` (75) · `COMPRAS` (46) · `DESERTO` (27) · `COMPR. CINCATARINA` (22) · `ANÁLISE DE ITENS` (19) · `TERMO DE REFERÊNCIA` (15) · `ETP REVISADO` (1) · `Aguardando desbloqueio` (2) |

`SPEC-0002 §2` already separates stored `status` from derived
`situacao_vigencia`. It does not anticipate a **third** axis — the acquisition
process — which `FRACASSADO` and `DESERTO` (a failed or bidder-less pregão) can
only belong to. A `VENCIDA` ATA whose replacement pregão is `DESERTO` is a
different operational situation from one whose replacement is `EM LICITAÇÃO`,
and the current model cannot say which. See OQ-21.

A separate `AÇÃO` vocabulary (11 values) governs what is being done about a
critical item: `AGUARDANDO ENTREGA` (39) · `SEM ATA` (23) · `COM ESTOQUE` (22) ·
`FAZER COMPRA` (20) · `ATA VENCIDA` (18) · `SOLICITAÇÃO DE PRÉ-EMPENHO` (9) ·
`AGUARDANDO RETORNO SAP` (8) · `SEM SALDO DE ATA` (8) · `AGUARDANDO ASSINATURAS`
(5) · `AGUARDANDO DOTAÇÃO ACO` (3) · `ITEM DO ESTADO` (1).

`SOLICITAÇÃO DE PRÉ-EMPENHO` is the NE state machine leaking into this
vocabulary — evidence the two are coupled, not independent.

---

## 12. Format hazards — input for the import capability

Every one of these appears in the supplied files. An importer that assumes
otherwise corrupts data silently.

> **Numbering note.** Earlier drafts called strict import validation `RF30`.
> That number belongs to `docs/rfc-sigi-v1.7.md`, which is **superseded** and
> whose `RF04`–`RF30` range collides with `requirements/functional.md` (`RF05`
> and `RN11` mean different things in each). No requirement number is cited here
> until one is allocated from `functional.md`'s own sequence. See OQ-28.

| Hazard | Observed | Consequence |
| --- | --- | --- |
| Dates as Excel serials | `46213.70138888889`, `45447.0` | Parsed as a number, a date becomes a quantity |
| Money as formatted text | `R$ 4.892,88000` | `.` thousands, `,` decimal, **5 decimal places** |
| Money at 5 decimals | `valorUnitario` `0,00599` | `NUMERIC(15,2)` truncates to `0,01` — a 67% error |
| Unit price at 4 decimals | `ITEM_ATA.valor_unitario NUMERIC(15,4)` | Correct for `4,582`, still lossy for `0,00599` |
| **Unit collision on the same concept** | `diasEstoque` = `119` (**days**, DOMS) vs. `TEMPO DE ESTOQUE` = `2,876` (**months**, CAME) | Same name, same meaning, 30× apart |
| SEI in scientific notation | `1.9596093E7` | Loses leading zeros and formatting |
| Codes typed as floats | `mercadoriaId` `2888.0`, `empenho` `1316.0` | `1316.0` is not a key that joins to `1316` |
| Code embedded in the name | `26829 - CLOREXIDINA 2% - 1 L` | Two facts in one field |
| Leading whitespace | supplier names arrive as `" RAZAO SOCIAL LTDA"` | Breaks equality joins |
| CNPJ formatted | `NN.NNN.NNN/0001-NN` | Punctuation must be normalised before check-digit validation |

The meeting raised this class of problem in the abstract — a field sized for 32
characters receiving 16 or 64. The files confirm it concretely.

---

## 13. LGPD

Columns carrying personal data, by source:

| Source | Columns |
| --- | --- |
| `ENTRADAS NFS (CSV)` | **`pacienteNome`**, `judicial`, `responsavel`, `usuarioAtesto`, `usuarioFinalizador` |
| `REQUISIÇÃO ENTRE UNIDADES (CSV)` | `requerente`, `autorizador`, `aprovador`, `finalizador` |
| `FORNECEDORES CADASTRADOS` | `CNPJ`, `Telefone`, `E-mail` |

`pacienteNome` alongside `judicial` identifies a named individual receiving a
judicially mandated supply. That is health data about an identified person —
the most sensitive category the project could touch, in a flow the RFC places
**out of scope** (`fórmulas e suplementos`, 150–200 cases) yet which arrives
inside the export anyway.

Consequences, which are not optional:

1. `ENTRADAS NFS` is not ingested in the MVP (§7). This is now also a privacy
   control, not only a data-quality one.
2. If it is ever ingested, `pacienteNome` must be dropped **at the importer**,
   before any persistence, and never written to a log or an error report.
3. `docs/security/lgpd.md` currently maps no health data because the RFC assumed
   none. That assumption is contradicted by the export. See OQ-24.
4. The workbooks must not be committed to this repository.

---

## 14. Cadence

| Source | Refresh |
| --- | --- |
| `COBERTURA DE ESTOQUE` | Monthly — *"utilizamos todo mês para atualizar a posição do estoque"* |
| `TRANSFERENCIA CONSOLIDADO` · `REQUISIÇÃO ENTRE UNIDADES` | On demand, period-selectable |
| `Controle de ITENS` · `EMPENHOS` | Continuous manual editing |

Monthly is the real cadence of the coverage signal. Any requirement promising a
daily shortage view is promising freshness the source does not provide, unless
the export cadence itself is renegotiated with the entity. See OQ-25.

---

## 15. Summary of what this changes

| Finding | Affects |
| --- | --- |
| An NE covers up to 37 insumos; 27,8% are multi-item | ADR-0007, SPEC-0004, SPEC-0006, data-model |
| Saldo is tracked per item in quantity | OQ-20 (resolved) — model both |
| 32,5% divergence between stored and derived saldo | ADR-0003 (confirms) |
| 17 ATA statuses spanning two state machines | OQ-21 (resolved) — `PROCESSO_LICITATORIO` |
| Four item identifiers; items get substituted | OQ-29, OQ-23, SPEC-0003, RN14 |
| Three-level material hierarchy | OQ-29, SPEC-0003 |
| Five fulfilment quantities; no `UNIDADE` entity | OQ-26 (resolved) — `UNIDADE`, `SOLICITACAO`, `ITEM_SOLICITACAO` |
| Inventory parameters already computed at source | ADR-0008 (accepted) — `POSICAO_ESTOQUE_SNAPSHOT` |
| 6,4% of ATAs have more than one fornecedor | OQ-11 (resolved) |
| No ATA export exists | OQ-02 (resolved), OQ-19 |
| `pacienteNome` in the export | OQ-24, lgpd.md |
| Coverage refreshed monthly, not daily | OQ-25 (resolved) — `data_referencia` on every surface |
