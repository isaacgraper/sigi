---
id: SPEC-0004
title: Fluxo de Notas de Empenho
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF13, RF11, RN03, RN08, RN09, RN10, RN11, RN13, RN17]
depends_on: [SPEC-0001, SPEC-0002, SPEC-0003, SPEC-0007]
milestone: M2
---

# SPEC-0004 — Fluxo de Notas de Empenho

## 1. Purpose

The NE flow is the core of SIGI. Everything else — ATAs, insumos, saldo, NFs,
the audit trail — exists to serve it. This spec defines the five-stage state
machine, who may move it, what is checked at each transition, and what is
recorded. Mariana's problem ("where is this process right now?") is answered
here or nowhere.

## 2. Scope

**In scope**
- Creating an NE request against an ATA and an item.
- The five-stage sequential machine and its guards.
- Reversal with justification.
- Stage counters for the module header (emitidas / em andamento / total).
- The NE número, typed in at emission (§9).

**Out of scope**
- Saldo computation and reservation semantics → SPEC-0006 (this spec calls it
  and defines when it is checked).
- NF registration → SPEC-0005.
- E-mail dispatch → SPEC-0008 (this spec *emits the events*).

**Multi-item NEs are in scope** (ADR-0007). An NE covers one or more insumos of
a single ATA; 27,8% of the entity's real empenhos do, the largest covering 37.

## 3. Domain model touched

`NOTA_EMPENHO` (created), `ITEM_NOTA_EMPENHO` (created), `ATA` (read + row lock),
`ITEM_ATA` (read), `HISTORICO_MOVIMENTACAO` (append).

The NE is a **header**: `numero`, `processo_sei`, `status`, `ata_id`,
`responsavel_id`. Quantity and value live on `ITEM_NOTA_EMPENHO`, one row per
insumo. `NOTA_EMPENHO.valor` is derived — `Σ ITEM_NOTA_EMPENHO.valor` — never
stored, for the same reason saldo is not (ADR-0003, ADR-0007).

Invariants this spec owns:
- I1: an NE's `status` only ever moves along the declared transition table.
- I2: every `ITEM_NOTA_EMPENHO.item_ata_id` resolves to an `ITEM_ATA` whose
  `ata_id` equals the parent `NOTA_EMPENHO.ata_id` — enforced by DB trigger DB2.
  All items of an NE therefore share one ATA, which is what makes the header's
  `ata_id` meaningful rather than redundant (OQ-06).
- I3: no NE exists without a `processo_sei`.
- I4: a non-cancelled NE always has at least one item (RN09).
- I5: an item's `valor_unitario` is fixed when the NE is opened. A later
  reajuste of the `ITEM_ATA` never changes an existing NE.

## 4. Behaviour

### 4.1 The state machine

```
                        ┌──────────────────────────────────────┐
                        │            reversal (gestor)         │
                        ▼                                      │
   ┌─────────┐   ┌──────────────────┐   ┌──────────────┐   ┌────────────────┐   ┌─────────────┐
   │ demanda │──▶│ validacao_saldo  │──▶│ pre_empenho  │──▶│ envio_fornecedor│──▶│ ne_emitida  │
   └─────────┘   └──────────────────┘   └──────────────┘   └────────────────┘   └─────────────┘
        │                 │                                                            │
        │                 └── saldo insuficiente ──▶ blocked, stays in validacao_saldo  │
        │                                                                              │
        └── cancelamento (gestor, com justificativa) ──▶ [cancelada] ◀──────────────────┘
                                                                    (not allowed from ne_emitida)
```

`ne_emitida` is terminal. `cancelada` is terminal and reachable from any
non-terminal state by a `gestor` with a justification. **The RFC does not
mention cancellation; it is added here because an NE opened in error otherwise
has no exit and would permanently hold reserved saldo.** See OQ-07.

**AC-0004-01** — Opening a multi-item NE
```gherkin
Given an ATA "ATA 002/2026" that is vigente with saldo disponível of R$ 2.840.000,00
And   an ITEM_ATA for "Notebook corporativo i7 16GB" at R$ 7.800,00 with 50 units remaining
And   an ITEM_ATA for "Monitor 24 polegadas" at R$ 1.200,00 with 20 units remaining
When  a gestor opens an NE with processo_sei "00301.000451/2026-12" and itens
      [10 × notebook, 5 × monitor]
Then  the NE is created with status "demanda"
And   it has exactly 2 ITEM_NOTA_EMPENHO rows
And   each item copies its ITEM_ATA's valor_unitario, and its valor is quantidade × valor_unitario rounded half up to the centavo (ADR-0016)
And   its derived valor is R$ 84.000,00
And   its numero is empty until it is issued (AC-0004-28)
And   a HISTORICO_MOVIMENTACAO row exists with acao "ne.criada" and the gestor's usuario_id
```
A single-item NE is the same criterion with one entry in `itens`; it is not a
separate path.

**AC-0004-02** — Mandatory fields (RN09)
```gherkin
Given a gestor
When  an NE is opened without processo_sei, without ata_id, with an empty itens
      list, or with any item missing item_ata_id or quantidade
Then  the response is 422 with error code "INVALID_DATA"
And   the error body lists each missing field individually by name
And   a failure inside itens names the index of the offending item
And   no NE row and no ITEM_NOTA_EMPENHO row is created
```
An empty `itens` list is a missing mandatory field, not an empty collection:
RN09 requires an insumo, and an NE committing nothing is not an administrative
act.

**AC-0004-03** — Processo SEI format
```gherkin
Given a gestor
When  an NE is opened with processo_sei "12345"
Then  the response is 422 with error code "PROCESSO_SEI_INVALIDO"
And   the message explains the expected format "NNNNN.NNNNNN/AAAA-DD"
```
Rationale: Carlos's transcription errors are the single most cited pain. Format
validation is the cheapest mitigation available (RF08, ADR-0002).

**AC-0004-04** — Sequential advance
```gherkin
Given an NE in status "demanda"
When  the gestor advances it
Then  its status becomes "validacao_saldo"
And   a HISTORICO_MOVIMENTACAO row records the transition with dados_anteriores containing status "demanda"
```

**AC-0004-05** — Skipping is rejected (RN08)
```gherkin
Given an NE in status "demanda"
When  a transition directly to "ne_emitida" is requested
Then  the response is 409 with error code "TRANSICAO_INVALIDA"
And   the NE status is unchanged
And   a HISTORICO_MOVIMENTACAO row exists with acao "ne.bloqueada" and motivo "TRANSICAO_INVALIDA"
```
The full transition table below is exhaustive; the test suite asserts every cell.

| from \ to | demanda | validacao_saldo | pre_empenho | envio_fornecedor | ne_emitida | cancelada |
| --- | --- | --- | --- | --- | --- | --- |
| **demanda** | — | ✅ | ❌ | ❌ | ❌ | ✅ gestor |
| **validacao_saldo** | ↩ gestor | — | ✅ guarded | ❌ | ❌ | ✅ gestor |
| **pre_empenho** | ❌ | ↩ gestor | — | ✅ | ❌ | ✅ gestor |
| **envio_fornecedor** | ❌ | ❌ | ↩ gestor | — | ✅ | ✅ gestor |
| **ne_emitida** | ❌ | ❌ | ❌ | ❌ | — | ❌ |
| **cancelada** | ❌ | ❌ | ❌ | ❌ | ❌ | — |

↩ = reversal, one step only, gestor with justification (RN03).

**AC-0004-06** — Reversal and cancellation require justification (RN03)
```gherkin
Given an NE in status "pre_empenho"
When  a gestor reverses or cancels it without a justificativa
Then  the response is 422 with error code "INVALID_DATA" naming the field justificativa
And   the NE status is unchanged
```

**AC-0004-07** — Reversal is recorded
```gherkin
Given an NE in status "pre_empenho"
When  a gestor reverses it with justificativa "valor divergente da proposta"
Then  its status becomes "validacao_saldo"
And   a HISTORICO_MOVIMENTACAO row exists with acao "ne.revertida", the justificativa, and dados_anteriores containing status "pre_empenho"
And   the reserved saldo of the ATA is unchanged
```

**AC-0004-08** — Servidor may advance but not open, edit, reverse or cancel
```gherkin
Given an NE in status "demanda"
When  a servidor advances it
Then  the response is 200 and the status becomes "validacao_saldo"
When  the same servidor opens an NE, edits its itens, reverses it or cancels it
Then  each response is 403 with error code "PERFIL_NAO_AUTORIZADO"
And   each denial writes a HISTORICO_MOVIMENTACAO row with acao "auth.negada"
```

**AC-0004-09** — Auditor is read-only
```gherkin
Given an NE in any status
When  an auditor opens an NE, edits its itens, advances, reverses or cancels it
Then  each response is 403 with error code "PERFIL_NAO_AUTORIZADO"
When  the auditor reads the NE
Then  the response is 200
```

**AC-0004-10** — Reversal is one step only
```gherkin
Given an NE in status "envio_fornecedor"
When  a gestor requests reversal to "demanda"
Then  the response is 409 with error code "TRANSICAO_INVALIDA"
```
Multi-step reversal must be performed one step at a time, each with its own
justification, so that the audit trail explains each retreat rather than one
unexplained jump.

**AC-0004-11** — `ne_emitida` is terminal
```gherkin
Given an NE in status "ne_emitida"
When  any transition, including cancellation, is requested
Then  the response is 409 with error code "TRANSICAO_INVALIDA"
```
Once budget is committed and the supplier notified, correction happens through a
new administrative instrument, not by mutating the record.

### 4.2 Saldo guard

**AC-0004-12** — Insufficient saldo blocks pré-empenho (RN10)
```gherkin
Given an ATA with saldo disponível of R$ 50.000,00
And   an NE in status "validacao_saldo" whose itens total R$ 78.000,00
When  the gestor advances it to "pre_empenho"
Then  the response is 409 with error code "SALDO_INSUFICIENTE"
And   the message states the available saldo and the shortfall in BRL
And   the NE remains in "validacao_saldo"
And   no item of the NE is reserved
```
The guard is evaluated against the NE's total, and reservation is
all-or-nothing. A partially reserved NE would commit budget for an empenho that
was never issued.

**AC-0004-13** — Concurrency across multi-item NEs
```gherkin
Given an ATA with saldo disponível of R$ 100.000,00
And   two NEs in "validacao_saldo", each with three itens totalling R$ 60.000,00
When  both are advanced to "pre_empenho" simultaneously
Then  exactly one succeeds
And   the other receives 409 "SALDO_INSUFICIENTE"
And   the ATA's valor_reservado is exactly R$ 60.000,00, never R$ 120.000,00
      and never a partial sum of one NE's itens
```
Implementation note: the guard reads the ATA with `SELECT ... FOR UPDATE` inside
the same transaction as the status change. Reading saldo, then writing status,
in separate transactions is the defect this criterion exists to prevent.

**AC-0004-14** — Reservation on entering pré-empenho
```gherkin
Given an ATA with valor contratado R$ 100.000,00 and no NEs
When  an NE whose itens total R$ 30.000,00 reaches "pre_empenho"
Then  the ATA's valor_reservado is R$ 30.000,00
And   its valor_empenhado is R$ 0,00
And   its saldo_disponivel is R$ 70.000,00
And   each ITEM_ATA's reserved quantity increases by that item's quantidade
```

**AC-0004-15** — Commitment on issuance
```gherkin
Given the NE from AC-0004-14 advancing to "ne_emitida"
When  the transition completes
Then  the ATA's valor_reservado is R$ 0,00
And   its valor_empenhado is R$ 30.000,00
And   its saldo_disponivel is still R$ 70.000,00
```
Only how the saldo is shown changes: `700 (300)` while reserved, `700` once issued
(SPEC-0006 AC-0006-13). Delivery is tracked on the NE and never touches it
(AC-0006-14, ADR-0015).

**AC-0004-16** — Cancellation releases reservation
```gherkin
Given an NE in "pre_empenho" whose itens total R$ 30.000,00
When  a gestor cancels it with a justificativa
Then  the ATA's saldo_disponivel returns to its prior value
And   every ITEM_ATA's reserved quantity returns to its prior value
And   a HISTORICO_MOVIMENTACAO row exists with acao "ne.cancelada", the justificativa and valor_liberado R$ 30.000,00
```
An NE cancelled in `demanda` or `validacao_saldo` reserved nothing, so its row
reads `valor_liberado` R$ 0,00.

### 4.3 ATA eligibility

**AC-0004-17** — Expired, suspended or closed ATA (RN11)
```gherkin
Given an ATA whose vigencia_fim is in the past, whose vigencia_inicio is in the future, or whose status is "suspensa", "encerrada" or "cancelada"
When  an NE is opened against it
Then  the response is 409 with error code "ATA_NAO_ELEGIVEL"
And   the message names the reason (vencida / não iniciada / suspensa / encerrada / cancelada)
And   the ATA's audit rows are still readable
```
*(v0.5)* `suspensa` and the readable audit rows come from SPEC-0002 AC-0002-12,
deferred here because it needs NEs: an ATA suspended and still accepting
commitments would defeat suspending it (OQ-45).

**AC-0004-25** — An ATA with NEs in progress is not closed (RN13)
```gherkin
Given an ATA with an NE in a non-terminal state
When  a gestor closes it
Then  the response is 409 with error code "ATA_COM_NE_PENDENTE"
And   the message names the blocking NEs
And   the ATA stays as it was
```
Terminal means `ne_emitida` or `cancelada` (AC-0004-11). Carried from SPEC-0002
AC-0002-11, deferred here because it needs NEs.

**AC-0004-26** — An NE emitida locks the ATA's figures
```gherkin
Given an ATA with at least one NE at "ne_emitida"
When  a gestor edits numero, fornecedor, vigencia_inicio, vigencia_fim, valor_total or data_orcamento_planilhado
Then  the response is 409 with error code "ATA_NAO_EDITAVEL"
And   nothing is changed
```
From then on the figures change only through an aditivo (SPEC-0002 AC-0002-13),
because an NE was committed against them. Carried from SPEC-0002 AC-0002-26.

### 4.4 Indicators

**AC-0004-18** — Stage counters (RF13)
```gherkin
Given 1 NE in "ne_emitida", 4 NEs in intermediate stages and 1 cancelled
When  GET /api/v1/notas-empenho/indicadores is read
Then  it reports emitidas = 1, em andamento = 4, total = 6
```
A cancelled NE counts in `total` and never in `em andamento`.

### 4.5 Item composition *(new in v0.3 — ADR-0007)*

**AC-0004-19** — An NE may not be emptied
```gherkin
Given an NE in status "demanda" with exactly one item
When  a gestor removes that item
Then  the response is 422 with error code "NE_SEM_ITENS"
And   the item is not removed
```

**AC-0004-20** — The same ITEM_ATA may not appear twice
```gherkin
Given a gestor opening an NE against "ATA 002/2026"
When  the itens list contains the same item_ata_id twice
Then  the response is 422 with error code "ITEM_DUPLICADO"
And   the message names the duplicated insumo
And   no NE row is created
```
Two lines for one insumo would make the reserved quantity ambiguous. Increase
the quantity instead.

**AC-0004-21** — Every item belongs to the NE's ATA (I2)
```gherkin
Given a gestor opening an NE against "ATA 002/2026"
When  the itens list contains an item_ata_id belonging to "ATA 005/2026"
Then  the response is 422 with error code "ITEM_DE_OUTRA_ATA"
And   the message names the offending insumo and the ATA it belongs to
And   no NE row is created
```
Enforced in the service and again by trigger DB2, because an NE spanning two
ATAs would make its saldo deduction unattributable.

**AC-0004-22** — Items are frozen from pré-empenho onward (OQ-27)
```gherkin
Given an NE in status "pre_empenho" with two itens
When  a gestor adds, removes or changes the quantity of any item
Then  the response is 409 with error code "NE_ITENS_CONGELADOS"
And   the message says the NE must be cancelled and reopened
And   the itens are unchanged
```
Saldo is reserved from `pre_empenho`. Editing items afterwards would move a
reservation without a state transition to explain it in the audit trail.
Correction is cancel-and-reopen, which leaves both acts recorded. **This
implements the proposed answer to OQ-27, now marked `Assumed`.**

**AC-0004-23** — Unit price is snapshotted at opening (I5)
```gherkin
Given an NE opened with an item at valor_unitario R$ 7.800,00
When  the underlying ITEM_ATA is later reajustado to R$ 8.400,00
Then  the NE's item still reads R$ 7.800,00
And   the NE's derived valor is unchanged
```
An issued empenho commits the price agreed on the day it was issued. A reajuste
that reached backwards would alter a value already sent to the supplier.

**AC-0004-24** — Quantity exhaustion blocks even with budget available (RN10, OQ-20)
```gherkin
Given an ITEM_ATA for "Monitor 24 polegadas" with 3 units remaining
And   an ATA with saldo disponível of R$ 500.000,00
And   an NE in "validacao_saldo" requesting 5 units of that monitor
When  the gestor advances it to "pre_empenho"
Then  the response is 409 with error code "QUANTIDADE_INSUFICIENTE"
And   the message names the insumo, the quantity available and the shortfall
And   the NE remains in "validacao_saldo"
```
The ATA can hold budget while the item it covers is exhausted. RN10 blocks on
whichever runs out first — value or quantity. This is the resolution recorded in
OQ-20, and it is why saldo is tracked in both units.

**AC-0004-27** — An item with an NE locks (from SPEC-0003 AC-0003-25)
```gherkin
Given an ITEM_ATA that an NE beyond "demanda" references
When  a gestor edits its insumo, quantidade or valor_unitario, or removes it
Then  the response is 409 with error code "ITEM_ATA_COM_NE"
And   nothing is changed
```
From then on the item's quantity changes only by an aditivo, as the ATA's figures
do (AC-0004-26).

**AC-0004-28** — The número is typed in at emission (§9)
```gherkin
Given an NE in status "envio_fornecedor"
When  it is advanced to "ne_emitida" without a numero
Then  the response is 422 with error code "INVALID_DATA" naming the field numero
When  it is advanced with numero "2026NE000045"
Then  its status becomes "ne_emitida" and its numero is "2026NE000045"
When  another NE is advanced to "ne_emitida" with the same numero
Then  the response is 409 with error code "NE_DUPLICADA"
```

## 5. Errors and edge cases

| Condition | HTTP | Error code | Message (pt-BR) |
| --- | --- | --- | --- |
| Missing or invalid field, including the justificativa and the numero | 422 | `INVALID_DATA` | Per field, in `fields`: "Informe {campo}." |
| Malformed Processo SEI | 422 | `PROCESSO_SEI_INVALIDO` | "Número de processo inválido. Formato esperado: NNNNN.NNNNNN/AAAA-DD." |
| Skipped or backward transition | 409 | `TRANSICAO_INVALIDA` | "Não é possível ir de {origem} para {destino}. Avance ou reverta uma etapa por vez." |
| Insufficient saldo | 409 | `SALDO_INSUFICIENTE` | "Saldo insuficiente na {ata}. Disponível: {saldo}. Necessário: {valor}. Ajuste o valor ou solicite aditivo." |
| Ineligible ATA | 409 | `ATA_NAO_ELEGIVEL` | "A {ata} está {motivo} e não pode receber novos empenhos. Escolha uma ATA vigente." |
| Wrong role | 403 | `PERFIL_NAO_AUTORIZADO` | "Seu perfil não permite esta ação. Peça a um gestor." |
| NE left with no itens | 422 | `NE_SEM_ITENS` | "A NE precisa de ao menos um insumo. Para encerrá-la, cancele a NE." |
| Repeated insumo in one NE | 422 | `ITEM_DUPLICADO` | "O insumo {insumo} aparece mais de uma vez. Ajuste a quantidade em vez de repetir o item." |
| Item from another ATA | 422 | `ITEM_DE_OUTRA_ATA` | "O insumo {insumo} pertence à {ata}. Todos os itens de uma NE devem ser da mesma ATA." |
| Editing itens after pré-empenho | 409 | `NE_ITENS_CONGELADOS` | "Os itens não podem ser alterados após o pré-empenho, pois o saldo já está reservado. Cancele a NE e abra outra." |
| Insufficient quantity on the item | 409 | `QUANTIDADE_INSUFICIENTE` | "Quantidade insuficiente de {insumo} na {ata}. Disponível: {qtd}. Necessário: {pedido}." |
| Closing an ATA with NEs in progress | 409 | `ATA_COM_NE_PENDENTE` | "A {ata} tem NEs em andamento: {numeros}. Conclua ou cancele essas NEs antes de encerrá-la." |
| Editing an ATA's figures after an NE emitida | 409 | `ATA_NAO_EDITAVEL` | "A {ata} já tem NE emitida. Altere os valores por um aditivo." |
| Editing an item an NE references | 409 | `ITEM_ATA_COM_NE` | "O item {insumo} já tem NE. Altere a quantidade por um aditivo." |
| Número already used | 409 | `NE_DUPLICADA` | "A NE {numero} já está registrada. Confira o número." |
| NE not found | 404 | `NOT_FOUND` | "NE não encontrada." |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Open an NE | ✅ | ❌ | ❌ |
| Edit the itens (before pré-empenho) | ✅ | ❌ | ❌ |
| Advance a stage | ✅ | ✅ | ❌ |
| Reverse a stage | ✅ | ❌ | ❌ |
| Cancel | ✅ | ❌ | ❌ |
| View | ✅ | ✅ | ✅ |

RFC §6.2 grants NE creation to gestor only; a servidor advancing an NE they
cannot create is intentional — it mirrors the real division of labour.

## 7. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| POST | `/api/v1/notas-empenho` | Open an NE; body carries `ata_id`, `processo_sei` and `itens[]` | 01–03, 17, 20, 21 |
| PUT | `/api/v1/notas-empenho/{id}/itens` | Replace the itens list; only while in `demanda` or `validacao_saldo` | 19, 22 |
| GET | `/api/v1/notas-empenho` | List with filters `etapa`, `ata_id`, `processo_sei` | 18 |
| GET | `/api/v1/notas-empenho/{id}` | Detail with full transition history | 07 |
| POST | `/api/v1/notas-empenho/{id}/avancar` | Advance one stage; the body carries `numero` when the next stage is `ne_emitida` | 04, 05, 08, 12, 13, 24, 28 |
| POST | `/api/v1/notas-empenho/{id}/reverter` | Reverse one stage; body requires `justificativa` | 06, 07, 10 |
| POST | `/api/v1/notas-empenho/{id}/cancelar` | Cancel; body requires `justificativa` | 16 |
| GET | `/api/v1/notas-empenho/indicadores` | Stage counters | 18 |

Transitions are explicit sub-resource actions rather than `PATCH {status}`, so
that guards and the required justification are part of the contract instead of
depending on the client sending the right next value.

## 8. Audit events

| Action | `entidade_tipo` | `acao` | `dados_anteriores` |
| --- | --- | --- | --- |
| Open | `nota_empenho` | `ne.criada` | `null` |
| Edit the itens | `nota_empenho` | `ne.itens_alterados` | `{itens}` |
| Advance | `nota_empenho` | `ne.avancada` | `{status, valor_reservado_ata}` |
| Reverse | `nota_empenho` | `ne.revertida` | `{status, justificativa}` |
| Cancel | `nota_empenho` | `ne.cancelada` | `{status, justificativa, valor_liberado}` |
| Blocked attempt | `nota_empenho` | `ne.bloqueada` | `{status, motivo, saldo_disponivel}` |

Blocked attempts are recorded deliberately: a pattern of repeated
`SALDO_INSUFICIENTE` against one ATA is exactly the "gargalo" the RFC's
stakeholders said they wanted to detect.

## 9. NE numbering

The número is issued outside SIGI, by the financial system, when the empenho is
emitted; the entity's own sheet `EMPENHOS` keeps it as a plain number (`empenho`
`1316`, `data-sources.md` §12). SIGI does not generate it. Until `ne_emitida` the
NE is identified by its `id`; the advance to `ne_emitida` requires the número,
typed in as issued, up to 20 letters and digits, unique (AC-0004-28). The NFs of
SPEC-0005 bind to that número.

## 10. Open questions

- **OQ-05** (multi-item NEs) — **Resolved** from operational data; this spec now
  models the header/item split. ADR-0007.
- **OQ-06** (denormalised FKs) — **Resolved**. `insumo_id` and `item_ata_id` left
  the header; the remaining `ata_id` carries invariant I2 rather than duplicating it.
- **OQ-03** (reservation semantics) — **Resolved** 2026-10-06, and the answer
  confirmed by the stakeholder's own example: reserved from `pre_empenho`, committed
  at `ne_emitida`, saldo unchanged by emission (ADR-0015, AC-0004-15). Delivery is
  tracked on the NE as `quantidade_faltante` (SPEC-0006 §2.3).
- **OQ-07** (cancellation absent from the RFC) — **Resolved** 2026-10-02, confirmed
  by the stakeholder. Implemented as `cancelada`, gestor-only, justification
  mandatory (AC-0004-16).
- **OQ-27** (may an item be removed after `pre_empenho`?) — **Resolved**
  2026-10-02, confirmed by the stakeholder. No: AC-0004-22 freezes the itens and
  directs the user to cancel and reopen.

Both were confirmed by the stakeholder on 2026-10-02, so AC-0004-16 and
AC-0004-22 stand as written.

To take to the stakeholders, each with the assumption this spec is built on:
**OQ-50** (where the número comes from, §9), **OQ-51** (who opens, reverses and
cancels), **OQ-52** (RN07 on NEs) and **OQ-53** (undoing an issued empenho).

## 11. Implementation plan

_Filled by `/plan SPEC-0004`._

## Revision history

**v0.4 (2026-10-06)** — OQ-03 is resolved by the stakeholder's example: reserved
from `pre_empenho`, committed at `ne_emitida`, and emission leaves the saldo
unchanged. AC-0004-14 and -15 keep their v0.3 meaning, and AC-0004-15 now points
at how the saldo is shown and at delivery. OQ-07 and OQ-27 are confirmed. The
state machine and every other criterion are untouched.

**v0.3 (2026-09-02)** — the acceptance criteria promised by v0.2 are now written.
v0.2 described what ADR-0007 would change without touching the criteria, so that
the traceability matrix would not break mid-analysis. That debt is paid here:
AC-0004-01, -02, -12, -13, -14 and -16 are rewritten for the header/item split,
and AC-0004-19 through -24 are new. **No existing AC was renumbered**, so every
row in `traceability.md` still resolves.

The state machine (AC-0004-04 through -11) is untouched. Status describes the
administrative document, not the line: there is no per-item status and no
partially advanced NE.

## 12. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC v1.6 §2.3 RF13, §2.5 RN03/RN08/RN09/RN10, §3.1, §4.2 Tela 6 |
| 0.2 | 2026-09-02 | OQ-05 resolved from data: NEs are multi-item (27,8%, up to 37 insumos). ADR-0007. Impact on AC-0004-01/02/12-16 described; state machine unaffected; OQ-27 opened |
| 0.3 | 2026-09-02 | ACs rewritten for multi-item NEs (ADR-0007): 01, 02, 12, 13, 14, 16 revised; 19–24 added, covering empty NEs, duplicate and foreign items, frozen itens (OQ-27), price snapshot and quantity exhaustion (OQ-20). OQ-05/OQ-06 resolved; OQ-07/OQ-27 marked Assumed |
| 0.4 | 2026-10-06 | OQ-03 resolved by the stakeholder's example: reserved from `pre_empenho`, committed at `ne_emitida`, saldo unchanged by emission (ADR-0015). AC-0004-15 points at the display (`700 (300)`, then `700`) and at delivery. OQ-07 and OQ-27 confirmed |
| 0.5 | 2026-10-20 | Carries the three SPEC-0002 criteria that need NEs: a suspended ATA takes no NE (AC-0004-17, from AC-0002-12), an ATA with NEs in progress is not closed (AC-0004-25, from AC-0002-11), an NE emitida locks the ATA's figures (AC-0004-26, from AC-0002-26). |
| 0.6 | 2026-10-27 | By the product owner's review. The número is typed in at emission, as the financial system issues it, not generated at opening (§9, AC-0004-28; `EMPENHOS` keeps it as a plain number). An item's price is copied from its ITEM_ATA and rounded once (AC-0004-01, -02). Missing fields and justifications answer `INVALID_DATA`, as the rest of the API; `CONFLITO_DE_VERSAO` is dropped. AC-0004-05, -06, -08, -09, -11, -16, -17 and -18 name their codes and audit rows; AC-0004-27 carries SPEC-0003 AC-0003-25. `ne.itens_alterados` audited. RN10, RN13 and RN17 claimed; SPEC-0006 leaves `depends_on` |
| 1.0 | 2026-10-27 | Approved by the product owner after the review of v0.6. No criterion changed; OQ-50 to OQ-54 stand as assumed |
