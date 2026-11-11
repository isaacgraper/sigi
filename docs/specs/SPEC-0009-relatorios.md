---
id: SPEC-0009
title: Relatórios e exportações
status: Approved
version: 1.2
owner: Isaac Kleimmann Graper
satisfies: [RF12, RN07]
depends_on: [SPEC-0001, SPEC-0002, SPEC-0003, SPEC-0004, SPEC-0005, SPEC-0006, SPEC-0007, SPEC-0017]
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

**AC-0009-10** — Exporting a list
```gherkin
Given a member who sees the list of ATAs, the itens of an ATA, the insumos, the NEs or the NFs
When  they press "Exportar" on it, with its filters set
Then  the file holds the rows the list holds with those filters, every one, not a page
And   each row as it stood at the data de referência, created from `inicio` when there is one
And   the file opens with the provenance of AC-0009-02, its filters named
And   the `relatorio.exportado` row of AC-0009-04 holds the filters
```
Product owner, 2026-11-10: "vou ir la em ATAs, la dentro eu posso exportar aquela
tabela de ATAs e consequentemente para cada tela de itens que temos, como nf, ne e
tudo mais".

**AC-0009-11** — A list export keeps RN07
```gherkin
Given a servidor
When  they export the insumos or the itens of an ATA
Then  the file holds only the insumos of their grupos
And   they may export every list they see, and none of the reports of AC-0009-01 nor the Histórico
```
The four reports stay the gestor's and the auditor's (AC-0009-05).

**AC-0009-12** — Exporting the Histórico
```gherkin
Given a gestor or an auditor on the Histórico, with its filters set
When  they export it
Then  each event is a row with when, its label, the entity, who, and what it changed
      written as "Campo: antes → depois"
```
SPEC-0017 moved this export here, so it carries its provenance and its row.

**AC-0009-13** — The export dialog
```gherkin
Given a list with "Exportar"
When  it is pressed
Then  a dialog offers CSV or PDF, the columns, all of them chosen, the data de
      referência, today by default, and the start of the period, empty by default
And   "Exportar" in it downloads the file with the list's filters
And   a refusal of the API shows under the field it names
```

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

### The list exports (AC-0009-10 to -12)

| Export | One row per | Columns, by key | Filters, as the list names them |
| --- | --- | --- | --- |
| `atas` | ATA | `ata` Número, `objeto` Objeto, `fornecedor` Fornecedor, `vigencia_inicio` Início da vigência, `vigencia_fim` Fim da vigência, `valor_contratado` Valor contratado, `status` Status, `situacao` Situação da vigência | `status`, `situacao_vigencia` |
| `itens-ata` | item of one ATA | `numero_item` Item, `sku` SKU, `descricao` Descrição, `unidade` Unidade, `quantidade` Quantidade, `valor_unitario` Valor unitário, `valor_total` Valor total | `ata_id`, required |
| `insumos` | insumo | `sku` SKU, `descricao` Descrição, `unidade` Unidade, `grupo` Grupo, `codigo_doms` Código DOMS, `codigo_externo` Código externo, `situacao` Situação | `q`, `grupo_id`, `status` |
| `notas-empenho` | NE | `processo_sei` Processo SEI, `ata` ATA, `etapa` Etapa, `valor` Valor, `numero_pre_empenho` Pré-empenho, `ne` NE, `aberta_em` Aberta em | `etapa`, `ata_id`, `processo_sei` |
| `notas-fiscais` | NF | `nf` NF, `ne` NE, `ata` ATA, `data_emissao` Data de emissão, `valor` Valor, `status` Status, `quarentena` Em quarentena | `status`, `nota_empenho_id`, `quarentena` |
| `historico` | event | `quando` Quando, `acao` Ação, `entidade` Entidade, `entidade_id` Identificador da entidade, `quem` Quem, `alteracoes` Alterações, `detalhes` Detalhes | `entidade_tipo`, `entidade_id`, `usuario_id`, `de`, `ate` |

A filter reads the row as it stood at the data de referência, so the same filters
and the same reference give the same file (AC-0009-03). An insumo and an item of
an ATA are rewound from their history as §2.2 rewinds the others; an item removed
by the reference is not listed. The Histórico lists the events up to the reference,
and from `inicio` when there is one; each event's changes are SPEC-0007's
(AC-0007-10).

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

`GET /api/v1/relatorios/{relatorio}`. The four reports and the Histórico are
for the gestor and the auditor: RF12 names the auditor, and a servidor's RN07
scope would turn a consolidated report into a partial one that reads as whole.
A list export is for every perfil that reads the list, inside its RN07 scope
(AC-0009-11). The filters of each list export are parameters of the same names.

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
| Servidor, on a report or the Histórico | 403 `PERFIL_NAO_AUTORIZADO` |
| `itens-ata` without `ata_id`, or a filter the list refuses | 422 `INVALID_DATA` |

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
6. *(v1.2)* `app/services/list_exports.py`: the six list exports, each read at
   the reference with its filters and RN07, through the provenance and the audit
   row of `relatorios.export`. The route opens to every perfil and the service
   refuses a servidor the reports and the Histórico.
7. *(v1.2)* Frontend: `components/relatorios/export-dialog.tsx`, the shared
   dialog, and "Exportar" on the lists of ATAs, insumos, NEs and NFs, on the
   itens of an ATA and on the Histórico. E2e in `frontend/e2e/exportar.spec.ts`.

New dependency: `fpdf2`, to write the PDF. Pure Python, no system library.

## 4. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF12, Tela 8 |
| 1.0 | 2026-11-10 | Approved by the product owner. Criteria in Given/When/Then; §2.1 names the columns of each report, §2.2 says how the state at the data de referência is read from the history, §2.3 adds the API, the permissions and the errors. AC-0009-07 deferred by the product owner. `fpdf2` added |
| 1.1 | 2026-11-10 | Product owner, 2026-11-10: the export is customisable. AC-0009-08 adds `colunas`, AC-0009-09 adds `inicio`, a window that ends at the data de referência; AC-0009-02 and -04 carry both. AC-0009-07 withdrawn by the product owner on the same day: a report downloads at once, with no task queue |
| 1.2 | 2026-11-11 | Product owner, 2026-11-10: "Exportar" on every list. AC-0009-10 to -13: the lists of ATAs, itens of an ATA, insumos, NEs and NFs, and the Histórico moved from SPEC-0017, each with its filters, at the data de referência, through one shared dialog; a list export is for whoever reads the list, inside RN07. The four reports are unchanged |
