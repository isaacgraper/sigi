---
id: SPEC-0005
title: Notas Fiscais e conferência
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF05, RF11, RF17, RN02, RN05, RN12]
depends_on: [SPEC-0004]
milestone: M2
---

# SPEC-0005 — Notas Fiscais e conferência

## 1. Purpose

The NF closes the cycle: it is the evidence that what was committed was
delivered. Carlos registers it, and Carlos mistypes, so validation quality here
determines whether the −70% error-reduction KPI is achievable.

## 2. Scope

**In scope**

- Registering an NF against an issued NE, with its header and the lines of what
  arrived, typed from the paper or PDF document.
- Correcting an NF before it is sent to conference, or after it is returned.
- The conference statuses `aguardando → em_conferencia → aprovada | devolvida`.
- Quarantine, a flag with a reason, for a note or a material with a problem.
- What each NE item still waits for: `quantidade_recebida`,
  `quantidade_em_quarentena` and `quantidade_faltante`, on the NE detail.

**Out of scope**

- The `ENTRADAS NFS` CSV import, and with it every patient field
  (`pacienteNome`). Out by the product owner's decision of 2026-11-04 (OQ-24,
  OQ-55): an NF here is a document between the entity and a fornecedor, and no
  NF field names a person who is not a member.
- The atesto deadline (OQ-22) and any payment step.
- XML or e-Publica intake (ADR-0002): the NF is typed in.

## 3. Domain model touched

`NOTA_FISCAL` and `ITEM_NOTA_FISCAL`, as in `docs/architecture/data-model.md`.

| Column | Type | Note |
| --- | --- | --- |
| `nota_fiscal.numero` | `VARCHAR(20)` | Alphanumeric, unique with the fornecedor |
| `nota_fiscal.data_emissao` | `DATE` | Not in the future |
| `nota_fiscal.valor` | `NUMERIC(15,2)` | Greater than zero, typed from the document |
| `nota_fiscal.nota_empenho_id` | `UUID` | The only link upward (RN02) |
| `nota_fiscal.fornecedor_id` | `UUID` | The fornecedor of the NE's ATA |
| `nota_fiscal.responsavel_id` | `UUID` | Who registered it |
| `nota_fiscal.status` | `VARCHAR(20)` | `aguardando`, `em_conferencia`, `aprovada`, `devolvida` |
| `nota_fiscal.justificativa_devolucao` | `TEXT` | Required while `devolvida` |
| `nota_fiscal.quarentena` | `BOOLEAN` | With `motivo_quarentena` set exactly when true |
| `item_nota_fiscal.item_nota_empenho_id` | `UUID` | A line of the NF's own NE |
| `item_nota_fiscal.quantidade` | `NUMERIC(15,3)` | Greater than zero |

There is no `ata_id` on either table. The database holds three invariants as a
backstop of the service's own checks:

- **DB1**: an NF is bound only to an NE in `ne_emitida`.
- **DB6**: Σ `nota_fiscal.valor` of an NE, `devolvida` excluded, never exceeds
  Σ `item_nota_empenho.valor` of that NE (RN12).
- **DB14**: an NF line names a line of the NF's own NE, as DB2 does for the NE.

## 4. Behaviour

**AC-0005-01** — A servidor registers an NF with número, data de emissão, valor,
the CNPJ of the fornecedor as printed on the document, the NE it belongs to, and
at least one line (RN05); any missing field returns 422 `INVALID_DATA` naming it
individually in `fields`. A malformed CNPJ returns 422 naming
`fornecedor_cnpj`.

**AC-0005-02** — The NF binds to `nota_empenho_id` only. There is no route,
schema field or column allowing a direct ATA link (RF05, RN02). The ATA is read
through the NE.

**AC-0005-03** — Binding to an NE whose status is not `ne_emitida` returns 409
`NE_NAO_EMITIDA`, with a test for each of the four non-terminal statuses.

**AC-0005-04** — `data_emissao` may not be in the future; 422 if it is.

**AC-0005-05** — A `data_emissao` earlier than the NE's issuance date
```gherkin
Given an issued NE with data_emissao 2026-10-10
When  an NF dated 2026-10-01 is registered without confirmation
Then  the response is 409 with error code "DATA_ANTERIOR_AO_EMPENHO" and nothing is stored
When  it is registered again with confirmar_data_anterior true
Then  the NF is stored and its audit row records the confirmation
```
This is a data-quality signal, and blocking it would make legitimate back-dated
documents impossible to register.

**AC-0005-06** — The CNPJ on the NF must match the fornecedor of the NE's ATA;
a mismatch returns 409 `FORNECEDOR_DIVERGENTE` naming both. The stored
`fornecedor_id` is the ATA's.

**AC-0005-07** — The sum of the values of the NFs bound to one NE, `devolvida`
excluded, may not exceed the NE value; exceeding returns 409
`VALOR_ACIMA_DO_EMPENHO` stating both figures (RN12). An NF in quarantine still
counts: it was delivered, and its value is still owed or contested.

**AC-0005-08** — An NF moves through the conference statuses
```gherkin
Given an NF in "aguardando"
When  a servidor sends it to conference
Then  it is "em_conferencia"
When  a gestor approves it
Then  it is "aprovada"
Given an NF in "em_conferencia"
When  a gestor returns it with a justificativa
Then  it is "devolvida" and the justificativa is stored
When  the justificativa is missing
Then  the response is 422 with error code "INVALID_DATA"
Given an NF in "devolvida"
When  it is sent to conference again
Then  it is "em_conferencia", after the checks of AC-0005-07 and AC-0005-12 pass again
When  any other move is asked for
Then  the response is 409 with error code "TRANSICAO_INVALIDA"
```
`aprovada` is final (RF17).

**AC-0005-09** — A gestor may approve or return an NF; a servidor may register,
correct and send but not approve or return. An auditor only reads.

**AC-0005-10** — Launching an NF reduces what the NE still waits for, and leaves the
ATA's saldo alone (OQ-03, ADR-0015). A test asserts that `saldo_disponivel` and
`valor_empenhado` are byte-identical before and after the launch, that
`quantidade_faltante` of each item falls by exactly that item's quantity on the NF,
and that an NF in quarantine, or in `devolvida`, moves nothing.

**AC-0005-12** — An NF lists what arrived
```gherkin
Given an issued NE with an item of 300 units
When  a servidor launches an NF with a line for that item of 100 units
Then  the NF is stored with that line and quantidade_faltante of the item is 200
When  a line names an item that is not on the NE, or has a quantity of zero or less
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming the line
When  the same item appears on two lines
Then  the response is 422 with error code "ITEM_DUPLICADO"
When  the lines of the NFs bound to the NE would exceed an item's quantity
Then  the response is 409 with error code "QUANTIDADE_ACIMA_DO_EMPENHO" stating both figures
And   nothing is stored
```
The NF's `valor` is still entered and RN12 still applies to it (AC-0005-07). An NF
counts from the moment it is launched, not when it is approved. The quantity cap
counts every NF of the NE but the `devolvida` ones, quarantine included, the way
RN12 does (OQ-46).

**AC-0005-13** — An NF with a problem is held in quarantine
```gherkin
Given an NF launched against an issued NE, in "aguardando" or "em_conferencia"
When  a servidor or a gestor puts it in quarantine with a reason
Then  the NF is flagged and the NE shows that its items arrived and are in quarantine
And   quantidade_faltante does not count its lines
And   an audit row "nf.quarentena_iniciada" records the reason
When  a gestor releases it
Then  quantidade_faltante counts its lines and an audit row "nf.quarentena_liberada" records it
When  the reason is missing
Then  the response is 422 with error code "INVALID_DATA"
When  an NF in quarantine is approved
Then  the response is 409 with error code "NF_EM_QUARENTENA"
```
Quarantine is a flag with a reason, not a fifth status: the four statuses were
confirmed (OQ-12). It is `Assumed` (OQ-46); the stakeholder asked only for *"uma
maneira de destacar que o item chegou porém está em quarentena"*.

**AC-0005-14** — An NF is corrected before conference
```gherkin
Given an NF in "aguardando" or "devolvida"
When  a servidor corrects its número, data, valor, CNPJ or lines
Then  the NF holds the new values, under the checks of AC-0005-01 to -07 and -12
And   an audit row "nf.corrigida" records the previous values
Given an NF in "em_conferencia" or "aprovada"
When  a correction is asked for
Then  the response is 409 with error code "NF_NAO_EDITAVEL"
```
The NE an NF belongs to is not corrected: an NF typed against the wrong NE is
returned and registered again.

**AC-0005-15** — One número per fornecedor
```gherkin
Given an NF número 123 of a fornecedor
When  another NF número 123 of the same fornecedor is registered
Then  the response is 409 with error code "NF_DUPLICADA"
When  NF número 123 of another fornecedor is registered
Then  it is stored
```

**AC-0005-16** — NFs are listed and read
```gherkin
Given NFs in several statuses
When  any member lists them with a filter on status, NE or quarantine
Then  only the matching NFs come back, newest first, with the total
When  one NF is read
Then  its lines come back with the insumo of each
When  the NF does not exist
Then  the response is 404 with error code "NOT_FOUND"
```

## 5. Errors and edge cases

| Condition | HTTP | Error code | Message (pt-BR) |
| --- | --- | --- | --- |
| Missing or invalid field, a line outside the NE, a missing justificativa or motivo | 422 | `INVALID_DATA` | Per field, in `fields`: "Informe {campo}." |
| Future `data_emissao` | 422 | `INVALID_DATA` | In `fields.data_emissao`: "A data de emissão não pode ser futura." |
| Repeated item in one NF | 422 | `ITEM_DUPLICADO` | "O insumo {insumo} aparece mais de uma vez. Some as quantidades em uma linha." |
| NE not issued | 409 | `NE_NAO_EMITIDA` | "A NE está em {etapa}. Só uma NE emitida recebe notas fiscais." |
| Date before the NE, unconfirmed | 409 | `DATA_ANTERIOR_AO_EMPENHO` | "A NF é de {data_nf}, anterior à NE, emitida em {data_ne}. Confirme a data para registrar." |
| CNPJ is not the ATA's fornecedor | 409 | `FORNECEDOR_DIVERGENTE` | "O CNPJ da NF ({cnpj_nf}) não é o do fornecedor da ATA ({fornecedor}, {cnpj_ata})." |
| Σ valor above the NE | 409 | `VALOR_ACIMA_DO_EMPENHO` | "O valor das NFs ({total}) passaria do valor da NE ({valor_ne})." |
| Σ quantity above an item | 409 | `QUANTIDADE_ACIMA_DO_EMPENHO` | "{insumo}: as NFs somariam {total}, acima das {empenhado} da NE." |
| Número already used by this fornecedor | 409 | `NF_DUPLICADA` | "A NF {numero} deste fornecedor já está registrada. Confira o número." |
| Move not allowed from the current status | 409 | `TRANSICAO_INVALIDA` | "Não é possível ir de {origem} para {destino}." |
| Approving an NF in quarantine | 409 | `NF_EM_QUARENTENA` | "A NF está em quarentena. Libere-a antes de aprovar." |
| Quarantine on an approved or returned NF, or releasing one not in quarantine | 409 | `TRANSICAO_INVALIDA` | "Não é possível ir de {origem} para {destino}." |
| Correcting an NF in conference or approved | 409 | `NF_NAO_EDITAVEL` | "A NF está {status} e não pode ser corrigida." |
| Wrong role | 403 | `PERFIL_NAO_AUTORIZADO` | "Seu perfil não permite esta ação. Peça a um gestor." |
| NF or NE not found | 404 | `NOT_FOUND` | "NF não encontrada." / "NE não encontrada." |

Every check of a write runs with the NE row locked (`SELECT … FOR UPDATE`), so
two NFs launched at once against one NE cannot both pass the caps.

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Register an NF | ✅ | ✅ | ❌ |
| Correct an NF | ✅ | ✅ | ❌ |
| Send to conference | ✅ | ✅ | ❌ |
| Approve | ✅ | ❌ | ❌ |
| Return | ✅ | ❌ | ❌ |
| Put in quarantine | ✅ | ✅ | ❌ |
| Release from quarantine | ✅ | ❌ | ❌ |
| View | ✅ | ✅ | ✅ |

## 7. API surface

| Method | Path | Purpose | AC |
| --- | --- | --- | --- |
| POST | `/api/v1/notas-fiscais` | Register; body carries `nota_empenho_id`, `numero`, `data_emissao`, `valor`, `fornecedor_cnpj`, `itens[]` and `confirmar_data_anterior` | 01–07, 12, 15 |
| PUT | `/api/v1/notas-fiscais/{id}` | Correct the header and lines, in `aguardando` or `devolvida` | 14 |
| GET | `/api/v1/notas-fiscais` | List with filters `status`, `nota_empenho_id`, `quarentena` | 16 |
| GET | `/api/v1/notas-fiscais/{id}` | Detail with the lines | 16 |
| POST | `/api/v1/notas-fiscais/{id}/enviar` | Send to conference | 08 |
| POST | `/api/v1/notas-fiscais/{id}/aprovar` | Approve | 08, 09, 13 |
| POST | `/api/v1/notas-fiscais/{id}/devolver` | Return; body requires `justificativa` | 08, 09 |
| POST | `/api/v1/notas-fiscais/{id}/quarentena` | Put in quarantine; body requires `motivo` | 13 |
| POST | `/api/v1/notas-fiscais/{id}/liberar` | Release from quarantine | 13 |

`GET /api/v1/notas-empenho/{id}` gains, per item, `quantidade_recebida`,
`quantidade_em_quarentena` and `quantidade_faltante` (AC-0005-10, AC-0006-15).

## 8. Audit events

| Action | `entidade_tipo` | `acao` | `dados_anteriores` |
| --- | --- | --- | --- |
| Register | `nota_fiscal` | `nf.registrada` | `null`, or `{confirmar_data_anterior}` when confirmed |
| Correct | `nota_fiscal` | `nf.corrigida` | `{numero, data_emissao, valor, itens}` |
| Send | `nota_fiscal` | `nf.enviada` | `{status}` |
| Approve | `nota_fiscal` | `nf.aprovada` | `{status}` |
| Return | `nota_fiscal` | `nf.devolvida` | `{status, justificativa}` |
| Quarantine | `nota_fiscal` | `nf.quarentena_iniciada` | `{motivo}` |
| Release | `nota_fiscal` | `nf.quarentena_liberada` | `{motivo}` |

## 10. Open questions

- **OQ-46** (`Assumed`): quarantine as a flag, and both caps counting an NF in
  quarantine. A stakeholder answer that differs changes AC-0005-07, -12 and -13.
- **OQ-22**: the atesto deadline, deferred.

## 11. Implementation plan

1. Migration `0007_notas_fiscais`: both tables, DB1, DB6 and DB14 as triggers,
   grants to the application role (`nota_fiscal` select, insert and update;
   `item_nota_fiscal` select, insert and delete).
2. `app/models/nota_fiscal.py`, `app/constants/notas_fiscais.py`,
   `app/repositories/nota_fiscal.py`.
3. `app/services/notas_fiscais.py` with the errors of §5 in
   `app/services/errors.py`; the NE detail reads the delivered quantities from
   the same repository.
4. `app/schemas/nota_fiscal.py` and `app/api/notas_fiscais.py`, with the
   permission matrix of §6.
5. Tests per AC, and AC-0006-14 and -15, against PostgreSQL.

No new dependency.

## Revision 2026-10-06 — what the NE still waits for

The stakeholder confirmed the four statuses (question 9, OQ-12) and that the
atesto deadline can wait for a later version (OQ-22), so the atesto SLA stays out
of the MVP.

Their example of delivery (question 6 and its follow-up) fixes how an NF matters:
an NE of 300 units with an NF of 100 launched *"só marca a quantidade faltante de
200"*, counted **at the launch** of the note, in units, and never changing the
ATA's saldo (ADR-0015). So the NF gains item lines (AC-0005-12), and a note with a
problem in the note or the material is held in quarantine instead of counted
(AC-0005-13). An earlier text of this revision counted an NF from its approval, in
value; that was a misreading and was removed before review.

## 12. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF05, §2.5 RN02/RN05, Tela 7 |
| 0.2 | 2026-09-02 | RN02 confirmed from real data; RN12 now aggregates over ITEM_NOTA_EMPENHO (ADR-0007); atesto SLA recorded as unmodelled (OQ-22); ENTRADAS NFS excluded on privacy and data-quality grounds (OQ-24) |
| 0.3 | 2026-10-06 | The stakeholder's delivery example (ADR-0015): AC-0005-10 now says launching an NF reduces `quantidade_faltante` and leaves the ATA's saldo alone. AC-0005-12: the NF lists what arrived, per NE item. AC-0005-13: quarantine for an NF with a problem. Four statuses confirmed (OQ-12), atesto deadline deferred (OQ-22). OQ-46 opened |
| 0.4 | 2026-10-13 | `ENTRADAS NFS` back in scope by the product owner, patient name included (OQ-24). Before approval this spec names the legal basis under LGPD art. 11, which perfis see `pacienteNome`, the audit of who read it, and its exclusion from logs and error messages. |
| 0.5 | 2026-10-27 | Moves to M2 by the product owner's request, so NFs can be launched against the NEs of SPEC-0004 in the same milestone. No criterion changed; the LGPD items of v0.4 still come before approval |
| 1.0 | 2026-11-04 | `Approved`. `ENTRADAS NFS` out of scope again by the product owner's decision, so the patient field and the LGPD items of v0.4 go with it (OQ-24, OQ-55). The fornecedor is checked by the CNPJ typed from the document (AC-0005-01, -06). AC-0005-05 confirms by a flag on a second request. Both caps exclude `devolvida` and count quarantine (AC-0005-07, -12). AC-0005-14 correction, -15 número per fornecedor, -16 listing. Scope, model, errors, permissions, API, audit and plan sections added |
