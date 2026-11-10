---
id: SPEC-0009
title: Relatórios e exportações
status: Approved
version: 1.1
owner: Isaac Kleimmann Graper
satisfies: [RF12]
depends_on: [SPEC-0001, SPEC-0002, SPEC-0004, SPEC-0005, SPEC-0006, SPEC-0007]
milestone: M4
---

# SPEC-0009 — Relatórios e exportações

## 1. Purpose

Ana's deliverable. A report that cannot be reproduced six months later cannot be
used in an audit, so reproducibility is the governing requirement, not layout.

## 2. Behaviour

**AC-0009-01** (RF12)
Given a gestor or an auditor
When they request one of the four reports as `csv` or as `pdf`
Then the file is served as a download
And the reports are execução orçamentária por ATA, posição de saldo consolidada,
    notas fiscais em conferência and indicadores de fornecedores

**AC-0009-02**
Given any export
When it is generated
Then it opens with its title, its identifier, the instant it was generated, the
    name of who requested it, the data de referência and the filters applied
And the period it covers: up to the data de referência, or from `inicio` to it
    when a window was asked for (AC-0009-09)

An export without provenance is an anonymous spreadsheet.

**AC-0009-03**
Given a report generated with a data de referência
When ATAs, NEs or NFs change afterwards and the report is requested again with
    the same filters and the same data de referência
Then every figure is the same as before
And a report without a data de referência is computed at the instant of the request

**AC-0009-04**
Given an export served
When the history is read
Then a `relatorio.exportado` row holds who exported, which report, the format,
    the data de referência and the filters
And its `entidade_id` is the identifier printed in the file
And it holds the `inicio` and the `colunas` asked for, when there were any

**AC-0009-05**
Given an auditor
When they request any report
Then it is served
And a servidor is refused with 403 `PERFIL_NAO_AUTORIZADO`
And no report route accepts a write

**AC-0009-06**
Given a CSV export
When it is opened in Excel in the pt-BR locale
Then it needs no import wizard: UTF-8 with BOM, `;` as the separator and the
    comma as the decimal mark
And a text cell that would start a formula is neutralised

Getting this wrong means every user "fixes" the file by hand, and the fixed
copies become the records people actually circulate.

**AC-0009-07** *(withdrawn)*
Every report is generated on request and served in the response, whatever its
size. There is no asynchronous generation, no task queue and no download link.

Product owner, 2026-11-10: a report downloads at once, with no task queue. The
criterion asked for a report of more than 5.000 rows to be generated
asynchronously; it is withdrawn and its number is not reused.

**AC-0009-08**
Given a report requested with `colunas`
When it is generated
Then the file holds only the columns named, in the report's own order
And a report without `colunas` holds every column
And a column the report does not have is refused with 422 `INVALID_DATA`, the
    message listing the columns it has

**AC-0009-09**
Given a report requested with `inicio`
When it is generated
Then it holds only the NEs and the NFs created from `inicio` to the data de
    referência, each as it stood at the data de referência
And the file says the period it covers, from `inicio` to the data de referência
And `posicao-saldo` refuses `inicio` with 422 `INVALID_DATA`, because a saldo
    summed over part of the NEs would read as the saldo of the ATA
And an `inicio` after the data de referência is refused with 422 `INVALID_DATA`

## 2.1 The reports

Every figure is read as it stood at the data de referência.

| Report | One row per | Columns |
| --- | --- | --- |
| `execucao-orcamentaria` | NE of each ATA | ATA, Fornecedor, Processo SEI, Pré-empenho, NE, Etapa, Valor, Data de emissão |
| `posicao-saldo` | ATA | ATA, Fornecedor, Situação, Fim da vigência, Valor contratado, Valor reservado, Valor empenhado, Saldo disponível, Comprometimento (%), Alto consumo |
| `notas-fiscais-em-conferencia` | NF in `em_conferencia` | NF, Fornecedor, NE, ATA, Data de emissão, Valor |
| `indicadores-fornecedores` | fornecedor with an ATA | Fornecedor, CNPJ, ATAs, Valor contratado, Valor empenhado, NFs lançadas, NFs aprovadas, NFs devolvidas, Valor aprovado |

`colunas` names a column by its key, in the same order as above (AC-0009-08):

| Report | Keys |
| --- | --- |
| `execucao-orcamentaria` | `ata`, `fornecedor`, `processo_sei`, `numero_pre_empenho`, `ne`, `stage`, `value`, `issued_on` |
| `posicao-saldo` | `ata`, `fornecedor`, `status`, `vigencia_fim`, `valor_contratado`, `valor_reservado`, `valor_empenhado`, `saldo_disponivel`, `comprometimento_percentual`, `alto_consumo` |
| `notas-fiscais-em-conferencia` | `nf`, `fornecedor`, `ne`, `ata`, `issued_on`, `value` |
| `indicadores-fornecedores` | `fornecedor`, `cnpj`, `atas`, `valor_contratado`, `valor_empenhado`, `nfs_lancadas`, `nfs_aprovadas`, `nfs_devolvidas`, `valor_aprovado` |

With `inicio` (AC-0009-09), `execucao-orcamentaria` lists the NEs created in the
window, `notas-fiscais-em-conferencia` the NFs created in it, and
`indicadores-fornecedores` counts the NEs and the NFs created in it, while its
ATAs and valor contratado stay as at the data de referência.

Saldo follows SPEC-0006: reserved from `pre_empenho`, committed at `ne_emitida`,
and `Alto consumo` at 80% of commitment. RF12's "insumo lifecycle" is the cycle
of SPEC-0007 (AC-0007-07), not a fifth report.

## 2.2 The state at the data de referência

The tables keep only the current state. The past is read from the history
(SPEC-0007), which stores the prior value of every change:

- An ATA, an NE or an NF exists at the reference when it was created by then.
- A field that changed after the reference takes the prior value of its first
  change after it: the status of an ATA, an NE or an NF, the valor total and the
  fim da vigência of an ATA, the itens of an NE, the número, the valor and the
  data de emissão of an NF.
- An aditivo de valor counts when it was recorded by then.
- An NE shows its número de pré-empenho only from `pre_empenho` on, and its
  número and data de emissão only at `ne_emitida`.

One limit: the itens of an NE as they stood are priced at the item's current
valor unitário, because the history of `ne.itens_alterados` keeps quantities only.
An item's price is locked from `validacao_saldo` on (AC-0004-27), so this
reaches only an NE that had not reserved saldo yet.

## 2.3 API, permissions and errors

`GET /api/v1/relatorios/{relatorio}`, for the gestor and the auditor. RF12 names
the auditor; a servidor's RN07 scope would turn a consolidated report into a
partial one that reads as whole.

| Parameter | Meaning |
| --- | --- |
| `formato` | `csv` (default) or `pdf` |
| `referencia` | The data de referência, an instant with its offset. Defaults to now |
| `ata_id` | Restricts the report to one ATA |
| `colunas` | The columns to export, their keys separated by commas. Defaults to all |
| `inicio` | The start of the window, an instant with its offset. Defaults to none: everything up to `referencia` |

| Case | Answer |
| --- | --- |
| Unknown report | 404 `NOT_FOUND` |
| Unknown `ata_id` | 404 `NOT_FOUND` |
| Unknown `formato`, or `referencia` in the future | 422 `INVALID_DATA` |
| A key in `colunas` the report does not have, or none at all | 422 `INVALID_DATA` |
| `inicio` after `referencia`, or `inicio` on `posicao-saldo` | 422 `INVALID_DATA` |
| Servidor | 403 `PERFIL_NAO_AUTORIZADO` |

## 3. Implementation plan

No migration: every report is read from existing tables and the history.

1. `app/constants/relatorios.py`: the reports, their titles and columns, the
   formats, the CSV dialect and the messages. `relatorio` joins the
   `entidade_tipo` values of the history filter.
2. Repositories: the ATAs, NEs and NFs created by an instant, the aditivos de
   valor by then, and the history rows after it.
3. `app/services/relatorios.py`: the state at the reference, the four tables and
   the `relatorio.exportado` row. `app/services/relatorio_files.py` renders a
   table as CSV and as PDF.
4. `app/api/relatorios.py` for `GET /api/v1/relatorios/{relatorio}`.
5. Tests per AC in `tests/test_relatorios.py`, against PostgreSQL.

New dependency: `fpdf2`, to write the PDF. Pure Python, no system library.

## 4. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF12, Tela 8 |
| 1.0 | 2026-11-10 | Approved by the product owner. Criteria in Given/When/Then; §2.1 names the columns of each report, §2.2 says how the state at the data de referência is read from the history, §2.3 adds the API, the permissions and the errors. AC-0009-07 deferred by the product owner. `fpdf2` added |
| 1.1 | 2026-11-10 | Product owner, 2026-11-10: the export is customisable. AC-0009-08 adds `colunas`, AC-0009-09 adds `inicio`, a window that ends at the data de referência; AC-0009-02 and -04 carry both. AC-0009-07 withdrawn by the product owner on the same day: a report downloads at once, with no task queue |
