---
id: SPEC-0002
title: ATAs de Registro de Preços
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF04, RF08, RF11, RF15, RF16, RF19, RN04, RN11, RN13, RN15]
depends_on: [SPEC-0001]
milestone: M2
---

# SPEC-0002 — ATAs de Registro de Preços

## 1. Purpose

The ATA is the root of every supply cycle. Without it there is no item, no
saldo and no NE. This spec covers its lifecycle, its registration, the reajuste that falls
due a year after the budget date, and the renewal alert that gives Mariana
warning before an ATA lapses.

## 2. Lifecycle vs. vigência

The RFC conflates two orthogonal concepts: the ENUM `(em_andamento, concluida,
cancelada)` in the data model, and the badges `Vigente / A vencer / Vencida /
Encerrada / Suspensa` in Tela 4. These are separated here.

- **`status`** (stored, explicit lifecycle): `rascunho → vigente → encerrada`,
  with `suspensa` and `cancelada` reachable from `vigente`.
- **`situacao_vigencia`** (derived, never stored): `vigente` |
  `a_vencer` (≤ 90 days remaining) | `vencida`, computed from
  `vigencia_fim` against the current date.

Storing a derived date state guarantees it goes stale the moment nobody runs the
job that refreshes it.

## 3. Behaviour

*(v0.4)* **This is an MVP slice.** Criteria marked *deferred* are real
requirements whose proof needs a spec that depends on this one (SPEC-0003,
SPEC-0004, SPEC-0006). They are not tested here; each is proven when its spec is
implemented. Nothing is renumbered.

### 3.1 Registering and reading an ATA

**AC-0002-01** — A gestor registers an ATA
```gherkin
Given a gestor
When  an ATA is registered with numero, objeto, orgao, fornecedor, vigencia_inicio,
      vigencia_fim, valor_total and data_orcamento_planilhado
Then  the response is 201 and the ATA has status "rascunho" and the gestor as responsavel
And   an audit row "ata.criada" records it
When  any of those fields is missing or malformed
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming each one
And   no ATA is created
```
`fornecedor` is given as `{cnpj, razao_social}` (AC-0002-25). `data_emissao` is
optional. One fornecedor sits on the ATA (OQ-11): the 29 of 456
ATAs that have two or three record the others on their items, where
`ITEM_ATA.fornecedor_id` overrides the ATA's (SPEC-0003).

**AC-0002-02** — `numero` is unique
```gherkin
Given an ATA with numero "123/2026"
When  a gestor registers another ATA with numero "123/2026"
Then  the response is 409 with error code "ATA_DUPLICADA"
And   no second ATA is created
```

**AC-0002-03** — The vigência is a real interval
```gherkin
Given a gestor registering or editing an ATA
When  vigencia_fim is not after vigencia_inicio
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming vigencia_fim
```

**AC-0002-04** — The valor is positive and exact
```gherkin
Given a gestor registering or editing an ATA
When  valor_total is zero, negative, or has more than two decimals
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming valor_total
And   nothing is rounded
```

**AC-0002-05** — Only a gestor writes
```gherkin
Given a servidor, and separately an auditor
When  either registers, edits, transitions, closes or adds an aditivo or a reajuste request to an ATA
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
And   nothing is created or changed
And   the denial produces the audit row of SPEC-0001 AC-0001-18
```
RN04 names issuing and closing; the rest of the write actions follow it because no
stakeholder has said anyone else records them (OQ-45).

**AC-0002-23** — Every profile can read ATAs
```gherkin
Given a signed-in gestor, servidor or auditor
When  the ATA list is requested
Then  a page of ATAs is returned, each with its status and its derived situacao_vigencia
And   the list can be filtered by status and by situacao_vigencia
When  one ATA is requested by id
Then  its fields, its aditivos and its reajuste requests are returned
When  the id does not exist
Then  the response is 404 with error code "NOT_FOUND"
```
RN07's scope by unidade and grupo de materiais applies to insumos, not to ATAs, so
no ATA is hidden from a profile.

**AC-0002-24** — What can be edited
```gherkin
Given an ATA in "rascunho"
When  a gestor edits any of its fields
Then  the change is saved and an audit row "ata.editada" records the prior values
Given an ATA that is not "rascunho"
When  a gestor edits numero, vigencia_inicio, vigencia_fim, valor_total or data_orcamento_planilhado
Then  the response is 409 with error code "ATA_NAO_EDITAVEL"
And   nothing is changed
```
After activation, the figures change only through an aditivo (AC-0002-13), so the
history of what was contracted is never overwritten. objeto, orgao and
responsavel stay editable. `ATA_NAO_EDITAVEL` is new in v0.4.

**AC-0002-06** — *Withdrawn in v0.3.* It specified a CSV upload of ATAs exported
from e-Publica. No such export exists, and the stakeholder confirmed that ATAs
are informed through SEI and recorded in a spreadsheet (question 1; OQ-02,
OQ-19), so a gestor registers each one (AC-0002-01). The items of an ATA are
imported by CSV under SPEC-0003 (AC-0003-06). The number is kept, because no AC
is ever renumbered.

**AC-0002-07** — *Withdrawn in v0.3.* Atomic import per file remains a rule, but
for the items: SPEC-0003 AC-0003-07 owns it.

**AC-0002-25** — A fornecedor is found by its CNPJ, or created
```gherkin
Given a gestor registering an ATA with fornecedor {cnpj, razao_social}
When  no fornecedor has that CNPJ
Then  a fornecedor is created and the ATA points to it
When  a fornecedor already has that CNPJ
Then  the ATA points to the existing one and its razao_social is not changed
When  the CNPJ is malformed, or its check digits are wrong
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming fornecedor.cnpj
And   no ATA and no fornecedor is created
```
The data model asks for the CNPJ to be validated with its check digits and gives
the fornecedor no screen of its own, so the ATA is where one first appears. The
CNPJ is stored as its 14 digits, whatever punctuation was typed.

### 3.2 Lifecycle

**AC-0002-22** — The lifecycle has a fixed set of moves
```gherkin
Given an ATA
When  a gestor moves it along rascunho to vigente, vigente to suspensa, suspensa to vigente,
      vigente or suspensa to encerrada, or rascunho, vigente or suspensa to cancelada
Then  the status changes and an audit row for that move is written
When  a gestor asks for any other move, including any move out of "encerrada" or "cancelada"
Then  the response is 409 with error code "TRANSICAO_INVALIDA"
And   the status is unchanged
When  the move is to "cancelada" and no justification is given
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming justification
```
The set of moves is an assumption (OQ-45): nobody at the entity has described it.

**AC-0002-10** — Closing records who and when
```gherkin
Given a "vigente" or "suspensa" ATA with no NE in a non-terminal state
When  a gestor closes it
Then  its status is "encerrada"
And   the audit row "ata.encerrada" carries the gestor and the time
```

**AC-0002-11** — *Deferred to SPEC-0004.* Closing needs the NEs to exist (RN13)
```gherkin
Given an ATA with an NE in a non-terminal state
When  a gestor closes it
Then  the response is 409 with error code "ATA_COM_NE_PENDENTE"
And   the message names the blocking NEs
And   the ATA stays as it was
```
Terminal means `ne_emitida` or `cancelada` (SPEC-0004 AC-0004-11).

**AC-0002-12** — *Deferred to SPEC-0004.* A suspended ATA takes no new NE
```gherkin
Given a "suspensa" ATA
When  an NE is opened against it
Then  the response is 409 with error code "ATA_NAO_ELEGIVEL"
And   the ATA's audit rows are still readable
```
RN11 lists `cancelada` and `encerrada`; `suspensa` is added here because an ATA
suspended and still accepting commitments would defeat suspending it (OQ-45).

**AC-0002-17** — An ATA is never deleted
```gherkin
Given any ATA
When  a DELETE is sent to its address
Then  the response is 405 and the ATA still exists
```
Only cancellation exists, and it keeps the history (AC-0002-22).

### 3.3 Vigência and alerts

**AC-0002-15** — `situacao_vigencia` is derived
```gherkin
Given an ATA with vigencia_fim 31/12/2026
When  it is read with the clock at 01/06/2026, at 15/12/2026 and at 15/01/2027
Then  situacao_vigencia is "vigente", "a_vencer" and "vencida" respectively
And   no write happened between the reads
```

**AC-0002-09** — The renewal alert
```gherkin
Given a vigente ATA whose vigencia_fim is within 90 days, with no aditivo de prazo
When  the renewal alert is read by any profile
Then  the ATA appears, ordered by days remaining ascending
Given a vigente ATA with an aditivo de prazo recorded
Then  it does not appear (RF19)
```
Aditivos of value or quantity do not remove an ATA from the alert, because they do
not move the date.

### 3.4 Aditivos

**AC-0002-13** — A gestor records an aditivo
```gherkin
Given a vigente ATA
When  a gestor records an aditivo of value, or of prazo, with a justification
Then  the aditivo is stored as its own record with its justification
And   valor_contratado is valor_total plus every aditivo of value
And   an aditivo of prazo sets the new vigencia_fim
And   an audit row "ata.aditivo_registrado" records it
When  the justification is missing, or an aditivo of value is not positive
Then  the response is 422 with error code "INVALID_DATA"
When  the ATA is not "vigente"
Then  the response is 409 with error code "ATA_NAO_VIGENTE"
```
*Deferred:* that the new `saldo_disponivel` rises is SPEC-0006's observable
(AC-0006-12), and an aditivo of quantity needs SPEC-0003's items.

**AC-0002-14** — The 25% ceiling
```gherkin
Given an ATA with valor_total R$ 100.000,00 and aditivos of value of R$ 20.000,00
When  a gestor records a further aditivo of value of R$ 6.000,00
Then  the response is 422 with error code "ADITIVO_ACIMA_DO_LIMITE"
And   nothing is stored
```
The ceiling is cumulative over the original valor_total (RF15, RN15). The same limit
on quantity is *deferred* to SPEC-0003. No limit is known for an aditivo of prazo.

### 3.5 Audit

**AC-0002-16** — Every mutation is audited in the same transaction
```gherkin
Given any ATA mutation in the table of §3.7
When  it succeeds
Then  one HISTORICO_MOVIMENTACAO row with that acao exists, written in the same transaction
And   dados_anteriores holds the prior values of what changed, and is empty on creation
When  the audit row cannot be written
Then  the mutation is not saved
```

### 3.6 Reajuste

**AC-0002-08** — A SEI process number is checked by format and nothing else
```gherkin
Given a gestor recording a reajuste request
When  the processo_sei is well formed
Then  it is accepted and no outbound request is made to any external system
```
The format and the refusal are AC-0004-03's and AC-0002-19's. No e-Publica or SEI
lookup exists (RF08, ADR-0002).

**AC-0002-18** — The reajuste date is derived (OQ-08)
```gherkin
Given an ATA with data_orcamento_planilhado 10/03/2026
When  its reajuste date is read
Then  it is 10/03/2027, one calendar year after the data do orçamento
And   no column stores it
```
A date that follows another date is never stored, for the reason `situacao_vigencia`
is not (§2). An orçamento dated 29/02 falls due on 28/02.

**AC-0002-19** — A gestor records a reajuste request
```gherkin
Given a vigente ATA
When  a gestor records a reajuste request with a processo_sei and the date it was filed
Then  the request is stored against the ATA
And   an audit row records it with the gestor as actor
When  the processo_sei is malformed
Then  the response is 422 with error code "PROCESSO_SEI_INVALIDO", as in SPEC-0004 AC-0004-03
When  a servidor or an auditor tries to record one
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
The request is opened in SEI, outside SIGI; SIGI records that it was filed and
under which process (RF08, ADR-0002).

**AC-0002-20** — The reajuste alert
```gherkin
Given a vigente ATA whose reajuste date is within the alert window, or already past
And   no reajuste request is recorded for it
When  the reajuste alert is read
Then  the ATA appears, ordered by days remaining ascending, negative once the date has passed
When  a reajuste request is recorded for it
Then  it no longer appears
```
The window is 90 days and configurable (OQ-42, `Assumed`). A test freezes the
clock at three dates, as AC-0002-15 does.

**AC-0002-21** — Recording a request changes no price
```gherkin
Given an ITEM_ATA at valor_unitario R$ 7.800,00
When  a reajuste request is recorded for its ATA
Then  the ITEM_ATA still reads R$ 7.800,00
```
Applying a new price needs the index and who approves it, which nobody has said
(OQ-08). SPEC-0004 AC-0004-23 already guarantees that a later price change never
reaches an issued NE.


### 3.7 Permissions, errors and audit events

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Register, edit, move, close, cancel, aditivo, reajuste request | yes | no | no |
| List and read ATAs, read both alerts | yes | yes | yes |

| Condition | HTTP | Error code | Message (pt-BR) |
| --- | --- | --- | --- |
| Duplicate numero | 409 | `ATA_DUPLICADA` | "Já existe uma ATA com este número. Confira o número ou abra a existente." |
| Field missing or malformed | 422 | `INVALID_DATA` | "Verifique os campos destacados." |
| Closing with NEs in progress | 409 | `ATA_COM_NE_PENDENTE` | "Esta ATA tem NEs em andamento: {numeros}. Conclua ou cancele essas NEs antes de encerrá-la." |
| Aditivo above 25% | 422 | `ADITIVO_ACIMA_DO_LIMITE` | "O aditivo passa de 25% do valor original da ATA. Reduza o valor." |
| Malformed SEI process | 422 | `PROCESSO_SEI_INVALIDO` | "Número de processo SEI inválido. Use o formato NNNNN.NNNNNN/AAAA-DD." |
| Move not allowed | 409 | `TRANSICAO_INVALIDA` | "Esta ATA não pode passar de {origem} para {destino}." |
| ATA past "rascunho" edited in a locked field | 409 | `ATA_NAO_EDITAVEL` | "Depois de ativada, valores e prazos só mudam por aditivo." |
| Aditivo on an ATA that is not vigente | 409 | `ATA_NAO_VIGENTE` | "A ATA precisa estar vigente. Ative ou retome a ATA antes." |
| Unknown ATA | 404 | `NOT_FOUND` | "ATA não encontrada." |
| Not a gestor | 403 | `PERFIL_NAO_AUTORIZADO` | "Seu perfil não permite esta ação." |

| Mutation | `entidade_tipo` | `acao` |
| --- | --- | --- |
| Register | `ata` | `ata.criada` |
| Edit | `ata` | `ata.editada` |
| Activate, suspend, resume | `ata` | `ata.ativada`, `ata.suspensa`, `ata.retomada` |
| Close, cancel | `ata` | `ata.encerrada`, `ata.cancelada` (with the justification) |
| Aditivo | `ata` | `ata.aditivo_registrado` |
| Reajuste request | `ata` | `ata.reajuste_registrado` |

## 4. Open questions

OQ-02 (resolved: ATAs are entered by hand, confirmed by the stakeholder on
2026-10-02), OQ-08 (reajuste: window, request and alert specified, index and
approver still unknown), OQ-11 (resolved for the MVP: one fornecedor on the ATA, an optional
override on each item), OQ-45 (the MVP's lifecycle, what is editable and who
records an aditivo or a reajuste request), OQ-19 (the Cincatarina channel), OQ-42
(the reajuste alert's lead time).

## Revision 2026-09-02 — validated against operational data

Three assumptions in this spec were checked against the stakeholders' workbooks
(`docs/architecture/data-sources.md`) and two did not survive.

**There is no ATA import.** OQ-02 asked whether e-Publica import is a lookup or
a CSV upload. It is neither: the entity's export contract contains **no ATA
report at all**. ATAs are maintained by hand in a spreadsheet, and some arrive
through **Cincatarina**, a shared-purchase channel producing ATAs the entity did
not run itself. AC-0002-* covering import must be re-scoped to: manual ATA
registration, plus CSV import of the ATA's *items*. See OQ-19. *(Done 2026-10-02:
AC-0002-06 and -07 are withdrawn.)*

**`fornecedor_id` is not always singular.** 29 of 456 ATAs (6,4%) carry more
than one fornecedor, up to three. §2's model of one supplier per ATA is wrong
for those. The likely fix is to move fornecedor to `ITEM_ATA`, which also
matches how the source records it. Not applied here — it changes AC-0002-01 and
the data model, and belongs in a revision that can be reviewed on its own.

**A third status axis exists.** §2 separates stored `status` from derived
`situacao_vigencia`. The source's `STATUS DA ATA` holds 17 values, and 12 of
them describe neither: they describe the **acquisition process** — `SAP`,
`FRACASSADO`, `CONSTRUÇÃO EDITAL`, `EM LICITAÇÃO`, `PGM`, `DESERTO`,
`TERMO DE REFERÊNCIA`. A `VENCIDA` ATA whose replacement pregão is `DESERTO` is
operationally different from one `EM LICITAÇÃO`, and neither axis in this spec
can express the difference. See OQ-21.

**Reajuste, partially answered.** `Controle de ITENS` carries
`DATA LIMITE REAJUSTE` per item, so the window is per-item and already tracked.
Index and approver remain unknown, so RF16 stays unspecified (OQ-08). *(Specified
in part on 2026-10-02: see below.)*

## Revision 2026-10-02 — how ATAs arrive, and the reajuste

**ATAs arrive through SEI and live in a spreadsheet.** The validation
questionnaire asked how an ATA reaches the team. The answer (question 1) was that
they are *"informadas via SEI"* and *"cadastradas em uma planilha do drive"*, each
with a limit fixed beforehand in the licitatório and one year of validity. That
confirms there is no ATA import, so AC-0002-06 and -07, which still described an
e-Publica CSV upload and which the 2026-09-02 revision had marked for re-scoping,
are withdrawn. What stays open is the Cincatarina channel (OQ-19).

**The reajuste is specified, in part.** RF16 was unmapped for lack of the entity's
policy. Question 2 supplied what the first version needs: the reajuste falls due
*"um ano após a data do orçamento"*, is requested through a SEI process, and the
system must alert about it. AC-0002-18 to -21 specify the date, the request and
the alert. Still unknown are the index and who approves (OQ-08), so nothing here
changes a price, and the alert's lead time and whether the right lapses after the
date (OQ-42, `Assumed`).

## Implementation plan

*Written 2026-10-06, after the spec was approved.*

**Data** (migration `0003_atas`): `fornecedor`, `ata`, `ata_aditivo` and
`ata_reajuste`. `ata.status` and `ata_aditivo.tipo` are `VARCHAR` with `CHECK`,
like `usuario`. `ata.vigencia_fim > vigencia_inicio` and `valor_total > 0` are
`CHECK`s as well as validation (DB constraints, not only Python). The app role gets
`SELECT, INSERT, UPDATE` and **no `DELETE`**, which is what makes AC-0002-17 true in
the database. `situacao_vigencia`, the reajuste date and `valor_contratado` are
derived on read and have no column. `ata_aditivo` has no `percentual` column: the
ceiling is checked against the sum.

**Layers:** `models/ata.py`, `models/fornecedor.py`; `repositories/ata.py` (reads, the
`FOR UPDATE` lock, the alert queries); `services/atas.py` (every rule above, the
lifecycle table, the derivations); `schemas/ata.py`; `api/atas.py`. The clock is
`app/core/clock.py`, so a test freezes it without touching the system time
(AC-0002-15, -20).

**Endpoints**

| Method | Path | AC |
| --- | --- | --- |
| POST, GET | `/api/v1/atas` | 01 to 04, 23, 25 |
| GET, PATCH | `/api/v1/atas/{id}` | 23, 24 |
| POST | `/api/v1/atas/{id}/ativar`, `/suspender`, `/retomar`, `/encerrar`, `/cancelar` | 10, 22 |
| POST | `/api/v1/atas/{id}/aditivos` | 13, 14 |
| POST | `/api/v1/atas/{id}/reajustes` | 08, 19, 21 |
| GET | `/api/v1/atas/alertas/renovacao`, `/api/v1/atas/alertas/reajuste` | 09, 20 |

DELETE answers 405 (AC-0002-17). Reads are open to the three perfis, writes to the
gestor, through the same `Requires` matrix, and the matrix test gains the new
routes.

**Config:** `ata_alert_days` (default 90) for the renewal alert and the reajuste
alert, one key because OQ-42 assumes the two are alike.

**Audit:** the `acao` values of §3.7, written in the caller's transaction through
`services/audit.py`.

**Tests:** one file, `tests/test_atas.py`, a test per AC named `test_ac_0002_NN_*`;
AC-0002-11, -12 and the saldo and quantity parts of -13 and -14 are deferred
(§3) and have no test here. The DB checks are proven in `test_migration_atas.py`.

**Not in this slice:** the screens (a second PR), `ITEM_ATA` and its fornecedor
override (SPEC-0003), the NE guards (SPEC-0004), `ATA_COM_NE_PENDENTE`.

**No new dependency.**

## 5. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF04/RF08, Tela 4, mockup 9.2.2.1 |
| 0.2 | 2026-09-02 | Validated against operational data: no ATA export exists (OQ-02 resolved); multi-fornecedor ATAs confirmed (OQ-11); third status axis recorded (OQ-21) |
| 0.3 | 2026-10-02 | Stakeholder answers (questions 1 and 2): ATAs are informed through SEI and entered by hand, so AC-0002-06 and -07 (ATA import) are withdrawn; the reajuste is specified in part, AC-0002-18 to -21 (date one year after the orçamento, request by SEI process, alert), and RF16 is mapped. Index and approver still unknown (OQ-08); alert lead time assumed (OQ-42) |
| 0.4 | 2026-10-06 | MVP slice. Every criterion is Given/When/Then. Added: the lifecycle moves (AC-0002-22), reading for all profiles (AC-0002-23), what is editable (AC-0002-24), permissions, errors and audit events (§3.7). AC-0002-08 reworded; AC-0002-11, -12 and the saldo and quantity parts of -13 and -14 are *deferred* to SPEC-0003, SPEC-0004 and SPEC-0006. OQ-11 settled for the MVP (fornecedor on the ATA, optional override on the item). RF15 added to `satisfies`. OQ-45 opened |
| 1.0 | 2026-10-06 | Approved. AC-0002-25: a fornecedor is found by its CNPJ or created, with the check digits validated, because the ATA is the only place one first appears. Implementation plan added |
