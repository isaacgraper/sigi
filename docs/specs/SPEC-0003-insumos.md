---
id: SPEC-0003
title: Catálogo de insumos e itens da ATA
status: Approved
version: 1.1
owner: Isaac Kleimmann Graper
satisfies: [RF03, RF07, RF11, RF15, RN07, RN14, RN15]
depends_on: [SPEC-0001, SPEC-0002]
milestone: M2
---

# SPEC-0003 — Catálogo de insumos e itens da ATA

## 1. Purpose

The insumo catalogue is where nomenclature consistency with DOMS is won or lost.
A.V.'s reported pain, "integração entre plataformas dificulta a nomenclatura e
especificidade dos itens, causando retrabalho", is addressed here or not at all.

This spec also covers what an ATA contracted, item by item: `ITEM_ATA`, its
quantity and unit price, the fornecedor of an item when it is not the ATA's, and
the aditivo de quantidade that SPEC-0002 deferred here. Without items there is no
NE (SPEC-0004) and no quantity saldo (SPEC-0006).

## 2. A resolved contradiction

RF03 says the insumo carries "ATA vinculada". The data model uses `ITEM_ATA` as
an N:N join. Both cannot be true: an insumo owned by one ATA cannot be reused,
and the same paper appearing in three ATAs would be three catalogue entries with
three codes, destroying DOMS correspondence.

**Resolution:** the insumo is a global catalogue entry with a unique `sku`. Its
relationship to ATAs is exclusively through `ITEM_ATA`, which carries quantity and
unit price. Tela 3's "ATA" column shows the ATAs an insumo participates in, not an
ownership field. (OQ-01)

## 3. Behaviour

*(v0.4)* **This is an MVP slice.** Criteria marked *deferred* are real
requirements whose proof needs SPEC-0004 (an NE referencing an item). They are
not tested here. The screens are specified separately (§6).

### 3.1 The catalogue

**AC-0003-01** — A servidor or a gestor registers an insumo
```gherkin
Given a servidor or a gestor
When  an insumo is registered with sku, descricao, unidade and grupo_id
Then  the response is 201 with the insumo
And   an audit row "insumo.criado" records it
When  codigo_doms, codigo_externo or quantidade_referencia are also given
Then  they are stored with it
When  sku, descricao, unidade or grupo_id is missing, or grupo_id names no grupo
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming each one
And   no insumo is created
When  an auditor tries it
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
`codigo_doms` and `codigo_externo` (DOMS `mercadoriaId`) exist only to join with
the DOMS exports. *(v0.4)* `grupo_id` is required: an insumo with no grupo would be
invisible to every scoped servidor (AC-0003-29), and every row of the source files
carries one. `unidade` is the dispensing unit as text (`UN`, `CX`, `L`), trimmed.

**AC-0003-02** — The SKU and the DOMS code are checked by format
```gherkin
Given a servidor or a gestor registering or editing an insumo
When  the sku is " clordeg21 "
Then  it is stored as "CLORDEG21"
When  the sku, once trimmed and uppercased, does not match the SKU pattern
Then  the response is 422 with error code "INVALID_SKU", and the message shows the format and an example
When  codigo_doms is not digits only, for example "2888.0"
Then  the response is 422 with error code "INVALID_DOMS_CODE"
And   nothing is trimmed or rounded to make it fit
```
The pattern is configurable, default `^[A-Z0-9]+$`, which fits the two examples in
the CAME sheet, `CLORDEG21` and `SER5D` (RF07). Uppercasing is normalisation, as the
CNPJ's is (AC-0002-25); `2888.0` is how the source files spell some codes, and
turning it into `2888` would be a guess about the file.

**AC-0003-03** — The SKU and the DOMS code are unique
```gherkin
Given an insumo with sku "CLORDEG21" and codigo_doms "26829"
When  another insumo is registered, or one is edited, with sku "CLORDEG21" or codigo_doms "26829"
Then  the response is 409 with error code "INSUMO_DUPLICADO"
And   the message names the existing insumo by sku and descricao when the caller can see it
And   nothing is created or changed
```
So the operator reuses the entry rather than inventing a variant. A scoped servidor
(AC-0003-29) is told only that the code is taken.

**AC-0003-04** — A gestor can change a `sku`, with a justification
```gherkin
Given an insumo, whether or not an ITEM_ATA references it
When  a gestor changes its sku to a value no other insumo has, with a justification
Then  the sku is changed, every ATA, NE and NF that referenced the insumo still does
And   an audit row "insumo.sku_alterado" holds the previous sku and the justification
When  the justification is missing
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming it
When  the new sku belongs to another insumo
Then  the response is 409 as in AC-0003-03
When  a servidor or an auditor tries it
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
*(v0.3.)* RN14 used to make the SKU immutable once referenced. The stakeholder said
new codes must be easy to add and to change *"pois compramos muitos itens pela
primeira vez"*, so a code is sometimes only known after the first purchase. Links
go by `id`, so changing the SKU breaks none of them; the history keeps the old one.

**AC-0003-05** — `quantidade_referencia` is not stock
```gherkin
Given an insumo with quantidade_referencia 500
When  its quantidade_referencia changes to any value, or to none
Then  no saldo, no ITEM_ATA figure and no dashboard figure changes
```
It is a process-alert threshold only. No endpoint, report or calculation treats it
as stock on hand (ADR-0008).

**AC-0003-11** — A servidor or a gestor corrects an insumo
```gherkin
Given an insumo
When  a servidor or a gestor edits descricao, unidade, grupo_id, codigo_doms, codigo_externo or quantidade_referencia
Then  the change is saved and an audit row "insumo.editado" holds the prior values
When  the edit sends a sku
Then  the response is 422 with error code "INVALID_DATA", because the sku changes only by AC-0003-04
```

**AC-0003-12** — Every profile reads and searches the catalogue
```gherkin
Given a signed-in gestor, servidor or auditor
When  the insumo list is requested with q "clorex"
Then  a page of insumos whose sku, codigo_doms or descricao contains "clorex", in any case, is returned
And   each carries its grupo path, its situação and its codes
And   the list can be filtered by grupo_id, which includes the grupos below it, and by situação
When  one insumo is requested by id
Then  its fields, its grupo path, its substitute if any, and the ATAs it is an item of are returned
When  the id does not exist
Then  the response is 404 with error code "NOT_FOUND"
```
The situação is derived, never stored: `ativo`, `descontinuado` or `substituido`
(§3.3). The list is ordered by sku. A servidor sees only its scope (AC-0003-29).

**AC-0003-10** — No insumo is deleted
```gherkin
Given any insumo
When  a DELETE is sent for it
Then  the response is 405
And   the insumo still exists
```
*(v0.4)* An insumo leaves the catalogue by being discontinued or substituted
(§3.3), which keeps every ATA, NE and NF that referenced it readable. The `ativo`
flag of v0.3 is gone: it said the same as `descontinuado_em`.

### 3.2 Grupos de materiais

**AC-0003-09** — Grupos are a three-level hierarchy
```gherkin
Given the grupo "MATERIAL ODONTOLÓGICO" with the subgrupo "RESTAURADORES" below it
When  the grupos are requested by any profile
Then  the tree is returned, each node with its nome, its nivel and its children
When  a gestor creates a grupo with no parent
Then  it is created at nivel 1, and an audit row "grupo_material.criado" records it
When  a gestor creates one below "RESTAURADORES"
Then  it is created at nivel 3
When  a gestor creates one below a nivel 3 grupo
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming grupo_pai_id
When  a sibling already has that nome, ignoring case and surrounding spaces
Then  the response is 409 with error code "DUPLICATE_GROUP"
When  a servidor or an auditor tries to create one
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
*(v0.4)* The three levels are the source's `Grupo mercadoria` → `SubGrupo
Mercadoria` → `Classificao SubGrupo Mercadoria`, measured at 15 groups and 44
group/subgroup pairs (`data-sources.md` §5). The 17/08 meeting made the same point:
*"só odontologia tem mais de 400 referências"*. The flat list of v0.3 (Expediente,
TI, Saúde, Limpeza, Mobiliário) came from the RFC and matched nothing in the data.
Free text is still refused: a grupo is picked from the tree, never typed into an
insumo.

**AC-0003-13** — A gestor renames a grupo
```gherkin
Given a grupo
When  a gestor changes its nome
Then  the change is saved, every insumo in it stays in it
And   an audit row "grupo_material.editado" holds the prior nome
When  a sibling already has that nome
Then  the response is 409 with error code "DUPLICATE_GROUP"
```
A grupo is never deleted nor moved to another parent: that would silently change
the scope of every servidor who owns it (AC-0003-29).

### 3.3 Substitution and discontinuation

**AC-0003-14** — A gestor discontinues an insumo
```gherkin
Given an "ativo" insumo
When  a gestor discontinues it with a justification
Then  descontinuado_em is today and its situação is "descontinuado"
And   every ITEM_ATA, NE and NF that referenced it still does, unchanged
And   an audit row "insumo.descontinuado" records the justification
When  the justification is missing
Then  the response is 422 with error code "INVALID_DATA"
```
The source sheet `Controle de ITENS` carries `ITEM DESCONTINUADO`.

**AC-0003-15** — A gestor records that an insumo is substituted by another
```gherkin
Given an "ativo" insumo A and an "ativo" insumo B
When  a gestor substitutes A by B with a justification
Then  A points to B, descontinuado_em is today and A's situação is "substituido"
And   A's sku, descricao and every link to A stay as they were
And   an audit row "insumo.substituido" records B and the justification
When  B is A itself, or B is not "ativo"
Then  the response is 409 with error code "INVALID_SUBSTITUTE"
```
The source carries `ITEM SUBSTITUIDO POR ITEM 43204`, and the CAME dashboard shows
it as `SUGESTÕES DE TROCA`. Substitution is a link, never a rewrite, so historical
NEs keep showing the original item (OQ-23, confirmed by the stakeholder; RN14).
Because B must be `ativo`, a chain can grow but never loop.

**AC-0003-16** — A gestor reactivates an insumo discontinued by mistake
```gherkin
Given a "descontinuado" or "substituido" insumo
When  a gestor reactivates it with a justification
Then  descontinuado_em and the substitute are cleared and its situação is "ativo"
And   an audit row "insumo.reativado" holds the prior values and the justification
```

**AC-0003-17** — A discontinued insumo enters no new item
```gherkin
Given a "descontinuado" or "substituido" insumo
When  a gestor adds it to an ATA, by hand or by import
Then  the response is 409 with error code "INSUMO_DESCONTINUADO", naming the substitute when there is one
And   an item that already holds it stays as it is
```
The ATA already contracted the existing item, so it stays; whether an NE may still
be opened on it is SPEC-0004's.

### 3.4 Importing the catalogue

**AC-0003-06** — The catalogue file
```gherkin
Given a gestor and a CSV file with the columns
      sku, descricao, unidade, grupo, subgrupo, classificacao, codigo_doms, codigo_externo, quantidade_referencia
When  it is imported
Then  each row creates the insumo of its sku, or updates it when the sku exists
And   grupo, subgrupo and classificacao are found by nome under their parent, or created
And   the report counts the rows created, updated and unchanged
When  the file has a column the importer does not know, such as estoque or minimo
Then  the column is ignored and the report names it
And   for estoque the report says the stock figure is read by the coverage import (§4), not lost
When  a row has no sku, no descricao, no unidade or no grupo
Then  the file is refused and the report names that line
When  a servidor or an auditor imports
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
*(v0.4)* The columns follow the model, not v0.3's `nome, categoria, estoque,
minimo, ata`: the ATA link now has its own file (AC-0003-24), and `minimo` was
`quantidade_referencia` under another name. Only `sku`, `descricao`, `unidade` and
`grupo` are required; `subgrupo` and `classificacao` may be empty, and a
`classificacao` with no `subgrupo` refuses the line. The DOMS exports do not carry
the SKU, so the operator joins it from the SKU sheet first (OQ-43). An import is
the gestor's: a scoped servidor would need a per-line scope check for something
done once at deployment and rarely after.

**AC-0003-07** — An import is all or nothing
```gherkin
Given a file of 1.000 rows of which lines 12 and 480 are invalid
When  it is imported
Then  the response is 422 with error code "IMPORT_REJECTED"
And   `rows` lists every invalid line with its field and a pt-BR message, not only the first
And   nothing from the file is written
When  the same file is sent with dry_run
Then  the same report is returned and nothing is written, whether the file is valid or not
```
`dry_run` is how the screen shows what an import will do before the gestor
confirms it, as the ATA's review step does (AC-0002-01). The same rule held for the
withdrawn ATA import (AC-0002-07).

**AC-0003-08** — An import can be repeated
```gherkin
Given a file already imported
When  it is imported again unchanged
Then  no insumo is created, every row counts as unchanged and no audit row is written
When  a row of it now has an empty codigo_doms, codigo_externo or quantidade_referencia
Then  the value already stored is kept
```
An empty optional cell keeps the stored value so that a file with fewer columns
does not erase what another file filled in. Every row that does change writes its
own `insumo.criado` or `insumo.editado` row, marked as coming from an import.

**AC-0003-18** — The file's format is read as the entity writes it
```gherkin
Given a CSV file
When  its first line separates fields with ";"
Then  numbers are read with "," as the decimal mark and "." between thousands, so "1.234,5" is 1234.5
When  its first line separates them with ","
Then  numbers are read with "." as the decimal mark and no thousands mark
When  a number carries "R$ " in front
Then  it is read without it
When  the file is UTF-8, with or without a BOM, or Windows-1252
Then  accented letters are read correctly
When  it is neither, is larger than 5 MB or 10.000 lines, or lacks a required column
Then  the response is 422 with error code "INVALID_FILE" and nothing is written
```
`data-sources.md` §12 measured these: money as text, `R$ 4.892,88000`, with `.`
for thousands and `,` for decimals. The separator decides how a number reads
because `1.000` is a thousand in a Brazilian Excel file and one anywhere else, and
guessing per cell would read the same column two ways. 10.000 lines is seven times
the SKU sheet (1.425 rows). Those routes are the only ones allowed past the 64 KiB body
ceiling of AC-0001-42, which SPEC-0001 v1.10 amends for them.

**AC-0003-19** — The hazards measured in the source files are caught
```gherkin
Given a catalogue file
When  a cell starts or ends with spaces, as supplier names do (" RAZAO SOCIAL LTDA")
Then  the spaces are removed before anything else is checked
When  a codigo_doms or a codigo_externo is written as a float, "2888.0"
Then  the file is refused and the report names that line, as AC-0003-02 does
When  a descricao starts with the DOMS code, "26829 - CLOREXIDINA 2% - 1 L"
Then  the descricao is stored as "CLOREXIDINA 2% - 1 L"
And   when codigo_doms is empty it is filled with "26829"
And   when codigo_doms holds another code the file is refused and the report names that line
And   the report counts the descrições corrected
```
These are `data-sources.md` §12's code-in-the-name, codes-as-floats and
leading-whitespace rows. The code is lifted out of the descrição because both facts
are in the cell and only one belongs there; a float is refused because `2888.0`
joins to nothing and the file should be fixed where it was produced.

### 3.5 The items of an ATA

**AC-0003-20** — A gestor adds an item to an ATA
```gherkin
Given a "vigente" or "suspensa" ATA and an "ativo" insumo
When  a gestor adds the insumo with quantidade 1.000 and valor_unitario 0,00599
Then  the response is 201 with the item, its valor_unitario exactly 0,00599 and its valor_total R$ 5,99
And   an audit row "ata.item_adicionado" records it on the ATA
When  numero_item is given, as "12"
Then  it is stored with the item
When  quantidade or valor_unitario is zero or negative, quantidade has more than 3 decimals,
      or valor_unitario has more than 5
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming each one
And   nothing is rounded
When  the insumo is already an item of this ATA
Then  the response is 409 with error code "ITEM_ATA_DUPLICADO"
When  the ATA is "encerrada" or "cancelada"
Then  the response is 409 with error code "ATA_NAO_EDITAVEL"
When  a servidor or an auditor tries it
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
The unit price keeps five decimals and nothing else does (ADR-0016): `0,00599` is
a measured unit price, which `NUMERIC(15,2)` stores as `0,01`, a 67% error
(`data-sources.md` §12). Items are written where the ATA is, by the gestor
(AC-0002-05), and on the same ATAs an edit is allowed on (AC-0002-24). `numero_item`
is the item's position in the pregão (`Nº ITEM`), not an identity.

**AC-0003-21** — The item's value is rounded once, to the centavo
```gherkin
Given an item with quantidade 3 and valor_unitario 0,33335
When  the item is read
Then  its valor_total is R$ 1,00, quantidade_contratada × valor_unitario rounded half up to the centavo
And   no column stores valor_total
```
`quantidade_contratada` is `quantidade` plus the item's aditivos de quantidade
(AC-0003-27). The product is exact in `Decimal` and is rounded only on the way out,
once, so a sum over items adds centavos that were each rounded the same way.

**AC-0003-22** — The ATA's items are listed with their sum
```gherkin
Given an ATA with valor_total R$ 10.000,00 whose items add up to R$ 9.800,00
When  any profile requests the ATA's items
Then  the items are returned, ordered by numero_item and then by sku
And   each carries its insumo's sku, descricao, unidade and situação, and its fornecedor
And   valor_itens is R$ 9.800,00 and the response says it differs from valor_total
```
A difference is shown, not refused. The ATA is registered before its items, and
the gestor needs to see that the two disagree before deciding which is wrong.
`Controle de ITENS` keeps a stored balance next to a computed one and a third of
them disagree (`data-sources.md` §10), which is the case for showing both. Saldo
still starts from the ATA's `valor_contratado` (SPEC-0006). A servidor sees only
the items of its scope (AC-0003-29).

**AC-0003-23** — An item can have its own fornecedor
```gherkin
Given an ATA whose fornecedor is A
When  a gestor adds or edits an item with fornecedor {cnpj, razao_social} B
Then  the item's fornecedor is B and the other items' is still A
When  the item is given no fornecedor
Then  its fornecedor reads as A
```
The fornecedor is found by its CNPJ or created, with the check digits validated, as
on the ATA (AC-0002-25). 29 of 456 ATAs carry two or three fornecedores (OQ-11);
for the other 94%, `fornecedor_id` stays empty.

**AC-0003-24** — A gestor corrects or removes an item
```gherkin
Given an item of a "vigente" or "suspensa" ATA
When  a gestor edits its insumo, quantidade, valor_unitario, numero_item or fornecedor
Then  the change is saved and an audit row "ata.item_editado" holds the prior values
When  a gestor removes it
Then  it no longer appears among the ATA's items, nor counts in valor_itens
And   an audit row "ata.item_removido" holds what it was
When  the ATA is "encerrada" or "cancelada"
Then  the response is 409 with error code "ATA_NAO_EDITAVEL"
```
As with the ATA (AC-0002-24), an edit corrects what was typed and an aditivo
changes what was contracted. A removed item keeps its row with `removido_em`, so the
audit trail can name it, and the insumo becomes free to be added again.

**AC-0003-25** — *Deferred to SPEC-0004.* An item with an NE locks
```gherkin
Given an item that an NE beyond "demanda" references
When  a gestor edits its insumo, quantidade or valor_unitario, or removes it
Then  the response is 409 with error code "ITEM_ATA_COM_NE"
And   nothing is changed
```
From then on the item's quantity changes only by an aditivo, because an NE reserved
or committed against it, as for the ATA's figures (AC-0002-26).

**AC-0003-26** — A gestor imports an ATA's items
```gherkin
Given a "vigente" or "suspensa" ATA and a CSV file with the columns
      sku, quantidade, valor_unitario, numero_item, cnpj_fornecedor, razao_social_fornecedor
When  a gestor imports it into the ATA
Then  each row adds the item of its sku, or corrects it when the ATA already has it
And   an item of the ATA that is not in the file is left as it is
And   the report counts the items added, corrected and unchanged
When  a sku is not in the catalogue, or its insumo is "descontinuado" or "substituido"
Then  the file is refused and the report names that line
When  the same sku appears on two lines
Then  the file is refused and the report names both
```
Only `sku`, `quantidade` and `valor_unitario` are required. AC-0003-07, -08 and -18
apply to this file as to the catalogue's: all or nothing, `dry_run`, repeatable,
the same number and encoding rules, and the per-row rules of AC-0003-20 and -23.
The file does not create insumos: a sku that is not in the catalogue is a line to
fix, not a new entry made by accident. This is the way for an ATA with hundreds of
items; AC-0003-20 is the way for one.

### 3.6 Aditivo de quantidade

**AC-0003-27** — A gestor records an aditivo de quantidade on an item
```gherkin
Given a "vigente" ATA with an item of quantidade 100
When  a gestor records an aditivo de quantidade of 20 on that item, with a justification
Then  the aditivo is stored with the item it raises and its justification
And   the item's quantidade_contratada is 120 and its quantidade is still 100
And   an audit row "ata.aditivo_registrado" records it
When  the justification is missing or the quantidade is not positive
Then  the response is 422 with error code "INVALID_DATA"
When  the ATA is not "vigente"
Then  the response is 409 with error code "ATA_NAO_VIGENTE"
```
This is the "aditivo of quantity needs SPEC-0003's items" that AC-0002-13 deferred.
It goes through the same endpoint as the aditivos of value and prazo. That the
item's `quantidade_disponivel` rises is SPEC-0006's observable (AC-0006-12).

**AC-0003-28** — The 25% ceiling on quantity
```gherkin
Given an item with quantidade 100 and aditivos de quantidade of 20
When  a gestor records a further aditivo de quantidade of 6
Then  the response is 422 with error code "ADITIVO_ACIMA_DO_LIMITE"
And   nothing is stored
When  a gestor corrects the item's quantidade to 70
Then  the response is 422 with error code "ADITIVO_ACIMA_DO_LIMITE", because 20 is more than 25% of 70
```
The ceiling is cumulative over the item's own quantidade, the same rule AC-0002-14
applies to the ATA's value (RF15, RN15).

### 3.7 Scope (RN07)

**AC-0003-29** — A servidor sees the insumos of its grupos
```gherkin
Given a servidor whose grupos are "MATERIAL ODONTOLÓGICO"
And   an insumo in "RESTAURADORES", below it, and an insumo in "MATERIAL DE EXPEDIENTE"
When  the servidor lists insumos
Then  only the first is returned
When  the servidor requests the second by id
Then  the response is 404 with error code "NOT_FOUND"
When  the servidor reads an ATA's items
Then  only the items whose insumo is in its grupos are returned
When  the servidor registers or edits an insumo into "MATERIAL DE EXPEDIENTE"
Then  the response is 422 with error code "INVALID_DATA" and `fields` naming grupo_id
Given a servidor with no grupos
When  it lists insumos
Then  the list is empty
Given a gestor or an auditor
Then  every insumo and every item is visible to them
```
RN07 limits what a servidor sees to its área de competência, which the data showed
is two axes, unidade and grupo de materiais (OQ-04). *(v0.4)* Only the grupo axis
is enforced here, because it is the only one with a table: `UNIDADE` arrives with
the coverage and solicitation specs, and the unidade axis lands with it. An
out-of-scope read is a 404, not a 403, so the insumo's existence is not disclosed
(`api-conventions.md`). ATAs themselves are not scoped (AC-0002-23).

**AC-0003-30** — A gestor sets a servidor's grupos
```gherkin
Given a servidor
When  a gestor sets its grupos to "MATERIAL ODONTOLÓGICO" and "MATERIAL DE LIMPEZA"
Then  those two replace whatever it had, and its next request is scoped by them
And   an audit row "usuario.grupos_alterados" holds the prior grupos
When  the member is a gestor or an auditor
Then  the response is 422 with error code "INVALID_DATA", because neither is scoped
When  a servidor or an auditor tries it
Then  the response is 403 with error code "PERFIL_NAO_AUTORIZADO"
```
The scope is read on every request, not carried in the token, so a change applies
at once.

### 3.8 Audit

**AC-0003-31** — Every mutation is audited in the same transaction
```gherkin
Given any mutation in the table of §3.9
When  it succeeds
Then  one HISTORICO_MOVIMENTACAO row with that acao exists per insumo, grupo, item or member changed,
      written in the same transaction
And   dados_anteriores holds the prior values of what changed, and is empty on creation
When  the audit row cannot be written
Then  the mutation is not saved
```

### 3.9 Permissions, errors and audit events

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| Register and correct an insumo | yes | yes, in its grupos | no |
| Change a sku, discontinue, substitute, reactivate | yes | no | no |
| Import the catalogue | yes | no | no |
| Create and rename a grupo | yes | no | no |
| Add, correct, remove and import an ATA's items; aditivo de quantidade | yes | no | no |
| Set a servidor's grupos | yes | no | no |
| Read the catalogue, the grupos and an ATA's items | yes | yes, in its grupos | yes |

| Condition | HTTP | Error code | Message (pt-BR) |
| --- | --- | --- | --- |
| Field missing or malformed | 422 | `INVALID_DATA` | "Verifique os campos destacados." |
| Malformed SKU | 422 | `INVALID_SKU` | "SKU inválido. Use só letras e números, sem espaços nem pontos, como CLORDEG21." |
| Malformed DOMS code | 422 | `INVALID_DOMS_CODE` | "Código DOMS inválido. Use só números, como 26829." |
| SKU or DOMS code in use | 409 | `INSUMO_DUPLICADO` | "Já existe um insumo com este código: {sku} {descricao}. Use o existente." |
| Grupo nome in use under that parent | 409 | `DUPLICATE_GROUP` | "Já existe um grupo com este nome aqui." |
| Substitute is the insumo itself, or not ativo | 409 | `INVALID_SUBSTITUTE` | "O substituto precisa ser outro insumo, ativo." |
| Discontinued insumo into an item | 409 | `INSUMO_DESCONTINUADO` | "Este insumo foi descontinuado e não entra em itens novos. Use {sku_substituto}." |
| Insumo already an item of the ATA | 409 | `ITEM_ATA_DUPLICADO` | "Este insumo já é um item desta ATA. Corrija o item existente." |
| Item with an NE (deferred) | 409 | `ITEM_ATA_COM_NE` | "Este item tem NE. Use um aditivo para mudar a quantidade." |
| Aditivo above 25% | 422 | `ADITIVO_ACIMA_DO_LIMITE` | "O aditivo passa de 25% da quantidade do item. Reduza a quantidade." |
| Items of an encerrada or cancelada ATA | 409 | `ATA_NAO_EDITAVEL` | "Uma ATA encerrada ou cancelada não pode ser editada." |
| Aditivo on an ATA that is not vigente | 409 | `ATA_NAO_VIGENTE` | "A ATA precisa estar vigente." |
| File unreadable, too large or missing a column | 422 | `INVALID_FILE` | "Não foi possível ler o arquivo. Use CSV em UTF-8, até 5 MB, com as colunas do modelo." |
| A line of the file is invalid | 422 | `IMPORT_REJECTED` | "Nenhuma linha foi importada. Corrija as linhas indicadas e envie de novo." |
| Unknown, or outside the servidor's grupos | 404 | `NOT_FOUND` | "Insumo não encontrado." |
| Profile not allowed | 403 | `PERFIL_NAO_AUTORIZADO` | "Seu perfil não permite esta ação." |

`IMPORT_REJECTED` carries `rows: [{line, field, message}]`, one entry per invalid
cell, with the line numbered as a spreadsheet numbers it (the header is line 1).

| Mutation | `entidade_tipo` | `acao` |
| --- | --- | --- |
| Register, correct | `insumo` | `insumo.criado`, `insumo.editado` |
| Change sku | `insumo` | `insumo.sku_alterado` (with the justification) |
| Discontinue, substitute, reactivate | `insumo` | `insumo.descontinuado`, `insumo.substituido`, `insumo.reativado` (with the justification) |
| Create, rename a grupo | `grupo_material` | `grupo_material.criado`, `grupo_material.editado` |
| Add, correct, remove an item | `ata` | `ata.item_adicionado`, `ata.item_editado`, `ata.item_removido` |
| Aditivo de quantidade | `ata` | `ata.aditivo_registrado` |
| Set a servidor's grupos | `usuario` | `usuario.grupos_alterados` |

An import writes the row of each insumo or item it creates or corrects, with the
`acao` above and the justificativa "Importado de arquivo CSV.". Item rows sit on the
ATA, so the ATA's history shows its items; because the row's entity is the ATA,
`dados_anteriores` names the item (`item_ata_id`, `sku`) even on an addition. A
substitution's row names the substitute's SKU the same way.

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

## 5. Open questions

None open. OQ-01, OQ-04 (grupo axis), OQ-11, OQ-23, OQ-29 and OQ-43 are resolved
and cited where they apply. The unidade axis of RN07 waits for `UNIDADE`, which is
a sequencing matter, not a question.

## 6. Screens

The catalogue (`/insumos`, its form and its import) and the items section of the
ATA page (add, correct, remove, import, aditivo de quantidade) are specified as
screens after this spec is approved: the catalogue in a new screen spec, the ATA's
items as a revision of SPEC-0013. The member page gains the servidor's grupos as a
revision of SPEC-0010. Each follows `DESIGN.md` and updates `docs/product/user-map.md`.

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
the same point — *"só odontologia tem mais de 400 referências"*. *(Written into
AC-0003-09 in v0.4.)*

**Items are substituted and discontinued.** `Controle de ITENS` carries
`ITEM SUBSTITUIDO POR ITEM 43204` and `ITEM DESCONTINUADO`; the CAME dashboard
surfaces it as `SUGESTÕES DE TROCA`. RN14 forbids changing the item's code once
referenced — correctly — but says nothing about substitution, which is the
operation's actual mechanism. Modelled as `substituido_por_id` and
`descontinuado_em`: a link, never a rewrite, so historical NEs stay correct.
Confirmed by the stakeholder on 2026-10-02 (OQ-23), and RN14 now says so.
*(Written into AC-0003-14 to -17 in v0.4.)*

**Import validation has concrete hazards now.** `data-sources.md` §12 lists what
the real files contain — codes typed as floats (`2888.0` will not join to
`2888`), the item code embedded in the description (`26829 - CLOREXIDINA 2% -
1 L`), leading whitespace on supplier names, and unit prices at five decimal
places (`0,00599`) that `NUMERIC(15,2)` would round to `0,01`. These belong in
this spec's validation ACs. *(Written into AC-0003-18, -19 and -20 in v0.4.)*

## Revision 2026-10-02 — the stakeholder chose the SKU

The validation questionnaire asked which of the four codes never changes and
should identify the item. The answer was **"Devemos utilizar o SKU"** (question
3), which reverses the proposal in OQ-29, where `codigo` was the DOMS client code.

- `INSUMO.sku` is the identity: `NOT NULL`, globally unique (RN14). Every `codigo`
  in ACs 01 to 04, 06 and 08 became `sku`, and the error code
  `CODIGO_DOMS_INVALIDO` became `INVALID_SKU`, in English as ADR-0013 asks of a
  code with no glossary noun in it. *(2026-10-06: the follow-up answer made the SKU
  changeable by a gestor, AC-0003-04, so `CODIGO_IMUTAVEL` is gone, not renamed.)*
- The DOMS client code gets its own column, `codigo_doms`, optional and unique,
  for joining DOMS exports. `mercadoriaId` stays in `codigo_externo`. The column
  `codigo` no longer exists.
- The SKU is the CAME's own mnemonic, kept in a sheet that maps it to the DOMS
  code. The DOMS exports do not carry it, so a catalogue import needs the SKU
  joined in first. *(2026-10-06: the stakeholder says every item has one, it is the
  integration code of the Branet stock, and none repeats, OQ-43 resolved. Who keeps
  the sheet was not answered.)*
- The group hierarchy, substitution and the import hazards above are untouched.

## Revision 2026-10-20 — the product owner's three decisions

Asked by the product owner while preparing this spec for approval:

- **Unit price at five decimals.** Only `ITEM_ATA.valor_unitario` keeps five places;
  every total, saldo and empenho stays at two. Recorded in ADR-0016, which replaces
  the four places `data-model.md` had, still lossy for `0,00599`.
- **The DOMS hierarchy for grupos.** Three levels, created by the catalogue import
  and by a gestor, never typed into an insumo (AC-0003-09, -13).
- **Items by CSV and one by one.** A file per ATA for the large ones (AC-0003-26),
  and adding or correcting a single item on the ATA's page (AC-0003-20, -24).

## Implementation plan

*Proposed with v0.4 and approved with the spec in v1.0.*

**Data** (migration `0005_insumos`):

- `grupo_material`: `id`, `nome`, `nivel SMALLINT CHECK (nivel BETWEEN 1 AND 3)`,
  `grupo_pai_id FK NULL`, unique on `(lower(nome), grupo_pai_id)` with the null
  parent covered by a partial index, and a `CHECK` that a nivel 1 has no parent.
- `insumo`: `id`, `sku VARCHAR(40) UNIQUE NOT NULL`, `codigo_doms VARCHAR(20) UNIQUE
  NULL`, `codigo_externo VARCHAR(40) NULL`, `descricao VARCHAR(300)`, `unidade
  VARCHAR(20)`, `grupo_id FK NOT NULL`, `quantidade_referencia NUMERIC(15,3) NULL`,
  `substituido_por_id FK → insumo NULL`, `descontinuado_em DATE NULL`, `CHECK`s for
  the SKU and DOMS formats and that a substitute implies `descontinuado_em`.
- `item_ata`: `id`, `ata_id FK`, `insumo_id FK`, `fornecedor_id FK NULL`,
  `numero_item VARCHAR(20) NULL`, `quantidade NUMERIC(15,3) CHECK > 0`,
  `valor_unitario NUMERIC(15,5) CHECK > 0`, `removido_em TIMESTAMPTZ NULL`, unique on
  `(ata_id, insumo_id)` where `removido_em IS NULL`.
- `ata_aditivo` gains `item_ata_id FK NULL` and `quantidade_acrescimo NUMERIC(15,3)
  NULL`; `ck_ata_aditivo_tipo` admits `quantidade`, and the shape check requires
  both for it and neither for the other two.
- `usuario_grupo_material`: `(usuario_id, grupo_id)` as the key.
- The app role gets `SELECT, INSERT, UPDATE` on the new tables and `DELETE` only on
  `usuario_grupo_material`, whose rows are a set replaced whole; the audit row keeps
  the prior set.

**Layers:** `models/insumo.py` (the four tables); `repositories/insumo.py`,
`repositories/item_ata.py`; `services/insumos.py` (the catalogue, grupos,
substitution, scope and the catalogue file), `services/itens_ata.py` (items, the
quantity ceiling and the items file), `services/importacao.py` (reading a file:
separator, numbers, encoding, the line report), shared by both imports;
`schemas/insumo.py`, `schemas/item_ata.py`; `api/insumos.py` (insumos and grupos),
the item routes in `api/atas.py`, the grupos of a servidor in `api/users.py`, and
`api/uploads.py` for the CSV body. Constants and messages in `app/constants/insumos.py`.
*(v1.1: as built; the plan named three model files and an `api/grupos.py`.)*

**Endpoints**

| Method | Path | AC |
| --- | --- | --- |
| GET, POST | `/api/v1/insumos` | 01 to 03, 12, 29 |
| GET, PATCH | `/api/v1/insumos/{id}` | 11, 12, 29 |
| POST | `/api/v1/insumos/{id}/alterar-sku`, `/descontinuar`, `/substituir`, `/reativar` | 04, 14 to 16 |
| POST | `/api/v1/insumos/importacao?dry_run=` | 06 to 08, 18, 19 |
| GET, POST | `/api/v1/grupos-materiais` | 09 |
| PATCH | `/api/v1/grupos-materiais/{id}` | 13 |
| GET, POST | `/api/v1/atas/{id}/itens` | 17, 20 to 23, 29 |
| PATCH | `/api/v1/atas/{id}/itens/{item_id}` | 23, 24, 28 |
| POST | `/api/v1/atas/{id}/itens/{item_id}/remover` | 24 |
| POST | `/api/v1/atas/{id}/itens/importacao?dry_run=` | 26 |
| POST | `/api/v1/atas/{id}/aditivos` (`tipo: "quantidade"`) | 27, 28 |
| POST | `/api/v1/usuarios/{id}/grupos-materiais` | 30 |

DELETE answers 405 (AC-0003-10). A file arrives as the request body, `Content-Type:
text/csv`, rather than as `multipart/form-data`, which FastAPI reads only through
`python-multipart`, a dependency it does not install. The CSV is read with the
standard library's `csv`, and the body is refused past `import_max_bytes` before it is
parsed. The matrix test gains the new routes.

**Config:** `sku_pattern` (default `^[A-Z0-9]+$`), `import_max_bytes` (5 MB) and
`import_max_lines` (10.000).

**Tests:** `tests/test_insumos.py`, `tests/test_itens_ata.py` and
`tests/test_importacao.py`, a test per AC named `test_ac_0003_NN_*`, with RN07 and
RN15 named in theirs; the DB checks in `tests/test_migration_insumos.py`.
AC-0003-25 is deferred and has no test here.

**Not in this slice:** the screens (§6), the unidade axis of RN07, and the NE guard
of AC-0003-25.

**No new dependency.**

## 7. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF03/RF07, Tela 3, mockup 9.2.2.2, §9.5 CAME mapping |
| 0.2 | 2026-09-02 | Four item identifiers recorded (OQ-29); three-level hierarchy replaces flat `categoria`; substitution/discontinuation modelled (OQ-23); concrete import hazards from real files |
| 0.3 | 2026-10-02 | The SKU is the item's identity, by the stakeholder's answer (OQ-29 resolved, reversing the DOMS-code proposal): ACs 01 to 04, 06 and 08 now key on `sku`, the DOMS code moves to `codigo_doms`, and a catalogue import refuses a row with no SKU. Substitution confirmed (OQ-23). OQ-43 resolved on 2026-10-06 (every item has one, none repeats); AC-0003-04: a gestor can change a SKU with a justification, because new codes are often known only after the first purchase |
| 0.4 | 2026-10-20 | Rewritten for approval, every criterion in Given/When/Then. The flat category list of AC-0003-09 is replaced by the three-level DOMS hierarchy it contradicted (`data-sources.md` §5), and `grupo_id` becomes required. Substitution, discontinuation and reactivation get criteria (AC-0003-14 to -17). The catalogue file follows the model and gains `dry_run`, the pt-BR number rules and the §12 hazards (AC-0003-06, -18, -19). `ITEM_ATA` is specified: by hand and by a file per ATA, the unit price at five decimals (ADR-0016), the item's own fornecedor (OQ-11), correction and removal (AC-0003-20 to -26). The aditivo de quantidade and its 25% ceiling, deferred by AC-0002-13 and -14, land here (AC-0003-27, -28). RN07 is claimed on the grupo axis (AC-0003-29, -30). The `ativo` flag is dropped for the derived situação. Permissions, errors, audit events and an implementation plan added. RF15 and RN15 claimed for their quantity half |
| 1.0 | 2026-10-20 | Approved by the product owner after review. No criterion changed |
| 1.1 | 2026-10-20 | While implementing: AC-0003-18's 5 MB file conflicted with the 64 KiB body ceiling of SPEC-0001 AC-0001-42; SPEC-0001 v1.10 gives the two import routes their own ceiling |
