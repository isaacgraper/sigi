# Data Model

Status: Draft · Source: RFC v1.6 §5.2, with corrections noted inline.

Revised 2026-09-02 against the stakeholders' operational data — see
`data-sources.md`. Changes of that round are marked *(2026-09-02)*.

## Entities

### USUARIO
`id UUID PK`, `nome`, `email UNIQUE`, `senha_hash`, `perfil ENUM(gestor,
servidor, auditor)`, `ativo BOOL`, `status ENUM(pendente, ativo, bloqueado,
desativado)`, `criado_em TIMESTAMPTZ`, `anonimizado_em TIMESTAMPTZ NULL`.

`status` is added: the mockup shows Pendente and Bloqueado, which a single
boolean cannot express. `ativo` is retained as a derived convenience.

### FORNECEDOR
`id UUID PK`, `cnpj UNIQUE`, `razao_social`, `email`, `ativo BOOL`.
CNPJ validated including check digits.

### ATA
`id UUID PK`, `numero UNIQUE`, `objeto`, `orgao`, `fornecedor_id FK`,
`data_emissao DATE`, `vigencia_inicio DATE`, `vigencia_fim DATE`,
`valor_total NUMERIC(15,2)`, `data_orcamento_planilhado DATE`,
`status ENUM(rascunho, vigente, suspensa, encerrada, cancelada)`,
`responsavel_id FK → USUARIO`.

Changes from the RFC: `fornecedor_id` added (Tela 5 shows a supplier per ATA but
the model had no link); `status` values replaced (`em_andamento/concluida/
cancelada` could not express the five badges in Tela 4); `situacao_vigencia` is
**not** a column — it is derived (SPEC-0002 §2).

***(2026-09-02)* Two state machines are conflated in the source.** The
spreadsheet's `STATUS DA ATA` holds 17 distinct values, of which only five
belong to the ATA (`VIGENTE`, `VENCIDA`, `SALDO ZERO`, `PRORROGADA`,
`CANCELADO`). The rest describe the **acquisition process** that precedes or
replaces the ATA — `SAP` (414), `FRACASSADO` (228), `CONSTRUÇÃO EDITAL` (202),
`EM LICITAÇÃO` (113), `PGM` (75), `DESERTO` (27), `TERMO DE REFERÊNCIA` (15).
`status` here stays the ATA's own lifecycle; the process axis needs its own
entity and is not modelled yet. See OQ-21.

***(2026-09-02)* `fornecedor_id` is not always singular.** 29 of 456 ATAs (6,4%)
carry more than one fornecedor, up to three. OQ-11 is resolved as "yes, it
happens"; the modelling response is deferred to SPEC-0002.

`CHECK (vigencia_fim > vigencia_inicio)`, `CHECK (valor_total > 0)`.

### ATA_ADITIVO *(new)*
`id UUID PK`, `ata_id FK`, `tipo ENUM(quantidade, valor, prazo)`,
`percentual NUMERIC(5,2)`, `valor_acrescimo NUMERIC(15,2)`,
`nova_vigencia_fim DATE NULL`, `justificativa TEXT`, `criado_por FK`, `criado_em`.

Required by RF15/RN15 and by the alternative flow "solicitar aditivo à ATA".
`valor_contratado` is `ATA.valor_total + Σ aditivos`.

### INSUMO
`id UUID PK`, `codigo UNIQUE`, `descricao`, `unidade`,
`grupo_id FK → GRUPO_MATERIAL NULL`, `sku VARCHAR NULL`,
`codigo_externo VARCHAR NULL`, `quantidade_referencia NUMERIC NULL`,
`ativo BOOL`, `substituido_por_id FK → INSUMO NULL`,
`descontinuado_em DATE NULL`.

**No `ata_id`.** RF03's "ATA vinculada" is realised through `ITEM_ATA` (SPEC-0003 §2).

***(2026-09-02)* Identity is plural.** The data carries four identifiers:
`SKU` (CAME mnemonic, e.g. `CLORDEG21`), the DOMS client code (`26829`), the
DOMS surrogate `mercadoriaId` (`3678`), and `Nº ITEM` (a position within a
pregão, not an identity). `codigo` holds the DOMS client code — the only one
shared across sources; `sku` and `codigo_externo` carry the other two so imports
can join. `Nº ITEM` belongs to `ITEM_ATA`, not here. See OQ-29.

***(2026-09-02)* `categoria` is replaced by `grupo_id`.** The real hierarchy has
three levels (15 groups, 44 group/subgroup pairs), which a flat string cannot
express.

***(2026-09-02)* Substitution.** `substituido_por_id` and `descontinuado_em`
record `ITEM SUBSTITUIDO POR ITEM 43204` / `ITEM DESCONTINUADO`, which the
operation performs and RN14 currently forbids. See OQ-23.

### GRUPO_MATERIAL *(new, 2026-09-02)*
`id UUID PK`, `nome`, `nivel SMALLINT`, `grupo_pai_id FK → GRUPO_MATERIAL NULL`,
`UNIQUE(nome, grupo_pai_id)`.

Self-referencing, three levels: `Grupo mercadoria` → `SubGrupo Mercadoria` →
`Classificao SubGrupo Mercadoria`. Sourced from
`TRANFERENCIA DE MERCADORIA (CSV)`.

### ITEM_ATA
`id UUID PK`, `ata_id FK`, `insumo_id FK`, `quantidade NUMERIC`,
`valor_unitario NUMERIC(15,4)`, `UNIQUE(ata_id, insumo_id)`.

Unit price uses four decimals: unit prices for consumables are frequently
sub-centavo, and rounding at storage time compounds across thousands of units.

### NOTA_EMPENHO
`id UUID PK`, `numero UNIQUE`, `processo_sei VARCHAR`, `data_emissao DATE`,
`status ENUM(demanda, validacao_saldo, pre_empenho, envio_fornecedor,
ne_emitida, cancelada)`, `ata_id FK`, `responsavel_id FK`, `criado_em`,
`atualizado_em`, `versao INT`.

`cancelada` is added (SPEC-0004 §4.1). `versao` supports optimistic locking for
`CONFLITO_DE_VERSAO`.

***(2026-09-02)* The NE is a header, not a line.** `quantidade`, `valor`,
`item_ata_id` and `insumo_id` are removed and live in `ITEM_NOTA_EMPENHO`.
Measured on real data: 27,8% of empenhos cover more than one insumo, the largest
covering 37. ADR-0007.

`ata_id` is retained deliberately: every item of an NE belongs to one ATA, so
the FK carries that invariant rather than leaving it to convention. This narrows
OQ-06 — the `insumo_id`/`item_ata_id` redundancy it warned about no longer
exists on this table.

`valor` is **derived**: `Σ ITEM_NOTA_EMPENHO.valor`. Same reasoning as ADR-0003,
one level down.

### ITEM_NOTA_EMPENHO *(new, 2026-09-02)*
`id UUID PK`, `nota_empenho_id FK`, `item_ata_id FK`, `quantidade NUMERIC`,
`valor_unitario NUMERIC(15,4)`, `valor NUMERIC(15,2)`,
`UNIQUE(nota_empenho_id, item_ata_id)`.

One row per insumo committed by the NE. **No status column** — the five-stage
flow describes the administrative document, so there is no partially advanced
NE (ADR-0005 unaffected). `valor_unitario` is copied from `ITEM_ATA` at opening
time, because a later reajuste must not retroactively change an issued empenho.

An NE with zero items cannot leave `demanda` (RN09).

### NOTA_FISCAL
`id UUID PK`, `numero`, `data_emissao DATE`, `valor NUMERIC(15,2)`,
`nota_empenho_id FK`, `fornecedor_id FK`, `servidor_id FK`,
`status ENUM(aguardando, em_conferencia, aprovada, devolvida)`,
`justificativa_devolucao TEXT NULL`,
`UNIQUE(numero, fornecedor_id)`.

`status` and `justificativa_devolucao` added (Tela 7 has statuses the RFC model
lacks — OQ-12). No `ata_id`: the ATA is reached through the NE (RN02).

### HISTORICO_MOVIMENTACAO
`id UUID PK`, `entidade_tipo`, `entidade_id UUID`, `acao`, `usuario_id FK`,
`timestamp TIMESTAMPTZ`, `dados_anteriores JSONB`, `justificativa TEXT NULL`,
`correlation_id UUID`.

Partitioned by year. `REVOKE UPDATE, DELETE` from the application role plus a
`BEFORE UPDATE OR DELETE` trigger. Index on
`(entidade_tipo, entidade_id, timestamp DESC)` and on `(usuario_id, timestamp DESC)`.

## Relationships

```
USUARIO 1─────* ATA                (responsável)
USUARIO 1─────* HISTORICO_MOVIMENTACAO
FORNECEDOR 1──* ATA
FORNECEDOR 1──* NOTA_FISCAL
ATA 1─────────* ITEM_ATA *─────────1 INSUMO
ATA 1─────────* ATA_ADITIVO
ATA 1─────────* NOTA_EMPENHO       (all items of an NE share one ATA)
NOTA_EMPENHO 1* ITEM_NOTA_EMPENHO *1 ITEM_ATA
NOTA_EMPENHO 1* NOTA_FISCAL
GRUPO_MATERIAL 1* INSUMO
GRUPO_MATERIAL 1* GRUPO_MATERIAL     (3 levels)
```

## Invariants enforced in the database

| # | Invariant | Mechanism |
| --- | --- | --- |
| DB1 | An NF's NE must be `ne_emitida` | Trigger on insert/update |
| DB2 | Every `ITEM_NOTA_EMPENHO.item_ata_id` resolves to the parent `NOTA_EMPENHO.ata_id` | Trigger *(2026-09-02, replaces the old NE-level check)* |
| DB3 | Audit rows are immutable | Privileges + trigger |
| DB4 | An ATA cannot be `encerrada` with non-terminal NEs | Trigger |
| DB5 | Monetary columns are `NUMERIC`, never `FLOAT` | Column types |
| DB6 | `Σ NF.valor` per NE ≤ `Σ ITEM_NOTA_EMPENHO.valor` | Trigger (RN12) *(2026-09-02)* |
| DB7 | An NE may not leave `demanda` with zero items | Trigger (RN09) *(2026-09-02)* |

Application-level enforcement is the first line, not the only one. Every rule an
auditor may one day rely on is also expressed where a buggy migration script or
a well-meaning `psql` session cannot bypass it.

## What is deliberately absent

- **No `saldo` column anywhere.** ADR-0003.
- **No `estoque` computed or mutated by SIGI.** SIGI is not the system of record
  for physical stock. *(2026-09-02)* It does hold an **imported, dated**
  snapshot — `POSICAO_ESTOQUE_SNAPSHOT` — written only by the importer, with no
  endpoint, service or UI that mutates it, and no `entrada de estoque`
  operation. ADR-0008, accepted by ADR-0009.
- **No `area`/`setor` on USUARIO or INSUMO** — those field names never existed in
  the operation. *(2026-09-02)* RN07's "área de competência" turns out to be two
  axes the data does carry: **unidade** and **grupo de materiais**, both now
  entities. RN07 becomes implementable as a scope on `USUARIO` referencing
  `UNIDADE` and `GRUPO_MATERIAL`; the columns land with the SPEC-0001 revision
  that adopts them, not before. OQ-04 resolved, OQ-26.

## Entities required by the operation

*(2026-09-02, ADR-0009)* These were recorded as gaps when the RFC governed
scope. Under ADR-0009 the operational data governs, so they are requirements.
Every field below exists in an export the entity supplies today — see
`data-sources.md`. Attribute lists are the modelling intent; the migrations land
with the specs that adopt them.

### UNIDADE
`id UUID PK`, `codigo_externo VARCHAR UNIQUE` (`unidadeId`, e.g. `289`), `nome`,
`tipo ENUM(ubsf, upa, hospital, ambulatorio, caf, central)`,
`regiao VARCHAR NULL`, `populacao INT NULL`, `equipes JSONB NULL`, `ativo BOOL`.

Every stock and fulfilment row in every export is keyed by `unidadeId`. `regiao`
(`Centro`, `Norte`) comes from `REQUISIÇÃO ENTRE UNIDADES`; `populacao` and the
team composition (ESF, ESB, EMULT, EMAP, EAPP, EMAD) from the CAME dashboard.

### CENTRO_CUSTO
`id UUID PK`, `codigo_externo VARCHAR UNIQUE` (`centroCustoId`), `nome`,
`unidade_id FK → UNIDADE`.

A unidade requests through a centro de custo (`PEDIDO QUINZENAL`,
`CIAD CAME`). Stock and fulfilment are keyed by the pair, not by unidade alone.

### SOLICITACAO
`id UUID PK`, `codigo_externo VARCHAR` (`id` in the source),
`unidade_solicitante_id FK`, `centro_custo_solicitante_id FK`,
`unidade_atendente_id FK`, `cronograma_id FK NULL`,
`tipo ENUM(manual, administrativa)`, `urgente BOOL`,
`status VARCHAR`, `data_cadastro TIMESTAMPTZ`,
`data_autorizacao TIMESTAMPTZ NULL`, `autorizador_id FK NULL`,
`data_aprovacao TIMESTAMPTZ NULL`, `aprovador_id FK NULL`,
`data_finalizado TIMESTAMPTZ NULL`, `finalizador_id FK NULL`,
`valor_solicitado NUMERIC(15,2)`.

**`tipo` inverts the intuitive reading:** `manual` means the request *follows*
the cronograma; `administrativa` means it falls outside it. Source: the entity's
own `HUB` annotation.

Three approval stages, each with its own actor, timestamp and scheduling window.
This is a second state machine, independent of the NE flow.

### ITEM_SOLICITACAO
`id UUID PK`, `solicitacao_id FK`, `insumo_id FK`,
`quantidade_solicitada NUMERIC`, `quantidade_autorizada NUMERIC`,
`quantidade_atendida NUMERIC`, `quantidade_pendente NUMERIC`,
`quantidade_pendente_sem_estoque NUMERIC`,
`valor_unitario NUMERIC(15,4)`, `lote VARCHAR NULL`, `validade DATE NULL`.

**Five quantities, not two.** *Authorised* is a distinct administrative decision
from *fulfilled*, and `quantidade_pendente_sem_estoque` is the one that
separates a supply failure from an administrative refusal — the rupture metric.
A fulfilment rate computed as `atendida ÷ solicitada` would conflate them.

### CRONOGRAMA
`id UUID PK`, `nome VARCHAR` (`CAME 6 2026`), `periodicidade VARCHAR`
(`PEDIDO QUINZENAL`), `unidade_id FK NULL`,
`janela_pedido_inicio DATE`, `janela_pedido_fim DATE`,
`janela_entrega_inicio DATE`, `janela_entrega_fim DATE`.

The delivery calendar described in the 17/08 meeting — first request by day 24 to
receive on the 2nd, second by day 8 to receive on the 16th — and carried in the
export as four scheduling windows per request.

### POSICAO_ESTOQUE_SNAPSHOT
`id UUID PK`, `insumo_id FK`, `unidade_id FK`, `centro_custo_id FK NULL`,
`data_referencia DATE`, `estoque_atual NUMERIC`, `demanda_diaria NUMERIC`,
`demanda_mensal NUMERIC`, `dias_estoque INT`, `curva_abc CHAR(1) NULL`,
`curva_xyz CHAR(1) NULL`, `estoque_minimo NUMERIC NULL`,
`ponto_pedido NUMERIC NULL`, `estoque_maximo NUMERIC NULL`,
`valor_unitario NUMERIC(15,5)`, `importado_em TIMESTAMPTZ`,
`UNIQUE(insumo_id, unidade_id, centro_custo_id, data_referencia)`.

Written **only by the importer** (ADR-0008). No endpoint, service or UI mutates
a row. Values are copied verbatim from DOMS, which computes them; SIGI does not
recalculate. Every surface displaying one shows its `data_referencia`.
Refresh cadence is monthly (OQ-25).

`valor_unitario` carries five decimals because the source does
(`0,00599`); rounding to two would be a 67% error on the smallest items.

### PROCESSO_LICITATORIO
`id UUID PK`, `numero_processo VARCHAR UNIQUE`, `numero_pregao VARCHAR NULL`,
`ano INT`, `objeto TEXT`, `modalidade VARCHAR NULL`,
`canal ENUM(proprio, cincatarina)`, `data_abertura DATE NULL`,
`previsao_homologacao DATE NULL`,
`status ENUM(termo_referencia, construcao_edital, etp_revisado, pgm, sap,
compras, em_licitacao, analise_itens, aguardando_abertura, selecao_fornecedor,
revisando_processo, homologado, finalizado, encerrado, fracassado, deserto,
cancelado)`.

The third status axis. Twelve of the seventeen values in the source's
`STATUS DA ATA` belong here, not on the ATA: a `VENCIDA` ATA whose replacement
pregão is `DESERTO` is operationally different from one `EM LICITAÇÃO`, and the
ATA's own lifecycle cannot express that. `canal` records Cincatarina, through
which some ATAs arrive without the entity running the pregão itself.

### ETAPA_PROCESSO
`id UUID PK`, `processo_id FK`, `etapa ENUM(comunicado, acp, sap, pgm, lct,
publicacao_edital, pregao, propostas, homologacao)`, `ordem SMALLINT`,
`dias_planejado INT NULL`, `dias_real INT NULL`, `concluida_em DATE NULL`.

Nine stages with planned-versus-actual in days, as tracked on page 3 of the CAME
dashboard.

### ITEM_PROCESSO
`id UUID PK`, `processo_id FK`, `insumo_id FK`, `quantidade_estimada NUMERIC`,
`UNIQUE(processo_id, insumo_id)`.

Links an insumo to the process that will replenish it — the basis for "how long
until this item has an ATA again".

### ACAO_ITEM
`id UUID PK`, `insumo_id FK`, `tipo ENUM(fazer_compra, sem_ata, sem_saldo_ata,
ata_vencida, com_estoque, solicitacao_pre_empenho, aguardando_entrega,
aguardando_retorno_sap, aguardando_assinaturas, aguardando_dotacao_aco,
item_do_estado, emprestimo, permuta)`, `descricao TEXT NULL`,
`responsavel_id FK NULL`, `criada_em TIMESTAMPTZ`,
`encerrada_em TIMESTAMPTZ NULL`.

What is being done about a critical item — the difference between a shortage
list and an actionable one. The first eleven values are observed in
`ESTOQUE <3 › STATUS`; `emprestimo` and `permuta` come from the 17/08 meeting,
where borrowing from and swapping with other entities were described as routine
responses. `solicitacao_pre_empenho` shows the NE state machine surfacing here,
so the two are coupled: an open action may reference an NE.

## Relationships added 2026-09-02

```
UNIDADE 1─────* CENTRO_CUSTO
UNIDADE 1─────* SOLICITACAO          (solicitante)
UNIDADE 1─────* POSICAO_ESTOQUE_SNAPSHOT
CRONOGRAMA 1──* SOLICITACAO
SOLICITACAO 1─* ITEM_SOLICITACAO *──1 INSUMO
INSUMO 1──────* POSICAO_ESTOQUE_SNAPSHOT
INSUMO 1──────* ACAO_ITEM
PROCESSO_LICITATORIO 1* ETAPA_PROCESSO
PROCESSO_LICITATORIO 1* ITEM_PROCESSO *1 INSUMO
PROCESSO_LICITATORIO 1* ATA           (a homologated process produces an ATA)
```

## Sequencing

These entities are not one migration. Suggested order, cheapest dependency
first: `GRUPO_MATERIAL` → `UNIDADE`/`CENTRO_CUSTO` →
`POSICAO_ESTOQUE_SNAPSHOT` (unlocks the coverage view, the highest-value
addition) → `SOLICITACAO`/`ITEM_SOLICITACAO` → `PROCESSO_LICITATORIO` and its
children → `ACAO_ITEM`. Each lands with the spec that adopts it; see
`roadmap.md` for the milestone impact, which is not small.
