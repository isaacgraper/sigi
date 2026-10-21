---
id: SPEC-0014
title: Telas de insumos
status: Approved
version: 1.0
owner: Isaac Kleimmann Graper
satisfies: [RF03, RF07, RF11, RF15, RN07, RN14, RN15]
depends_on: [SPEC-0003, SPEC-0010, SPEC-0011, SPEC-0013]
milestone: M2
---

# SPEC-0014 — Telas de insumos

## 1. Purpose

SPEC-0003 gave the insumo catalogue, its grupos, the items of an ATA, the two CSV
imports and RN07's grupo axis their backend. Nobody can use any of it without a
client. This spec gives every perfil the screens to search the catalogue and read
an ATA's items, a servidor and a gestor the screens to register and correct
insumos, and the gestor the screens to import, keep the grupos, add and correct an
ATA's items, and set a servidor's grupos.

The screens add no rule. Every decision is SPEC-0003's and the API's; the screens
ask, show the answer, and show the API's refusal in its own words.

## 2. Scope

**In scope**
- `/insumos`: the catalogue, searched and filtered, a page at a time.
- `/insumos/novo` and `/insumos/{id}/editar`: registering and correcting an insumo.
- `/insumos/{id}`: the insumo, its substitute, the ATAs it is an item of, and the
  gestor's actions: change the SKU, discontinue, substitute, reactivate.
- `/insumos/grupos`: the three-level tree, and the gestor's create and rename.
- `/insumos/importar`: the catalogue file, checked before it is written.
- An "Itens" section on `/atas/{id}`: the items, their sum beside the ATA's
  valor_total, and the gestor's add, correct, remove and aditivo de quantidade.
- `/atas/{id}/itens/importar`: an ATA's items file, checked before it is written.
- On `/members`, a gestor sets a servidor's grupos.
- "Insumos" in the sidebar for every perfil, after "ATAs".
- The loading, empty and error states of every page.

**Out of scope**
- The lock on an item with an NE (AC-0003-25), which lands with SPEC-0004.
- Stock, coverage and the `estoque` column (ADR-0008); the catalogue import names
  the column and ignores it (AC-0003-06).
- The insumo's and the ATA's audit history on screen (SPEC-0007).
- Moving or deleting a grupo, deleting an insumo: no control exists, because the
  API has none (AC-0003-10, -13).

*(0.1)* SPEC-0003 §6 planned three documents: a catalogue spec, a SPEC-0013
revision for the items and a SPEC-0010 revision for the grupos. They are one here,
so the screens of one backend are approved, built and proven together, and two
specs already `Implemented` are not reopened.

## 3. Domain model touched

None. The screens call SPEC-0003's endpoints and one it gains for them,
`GET /api/v1/usuarios/{id}/grupos-materiais` (SPEC-0003 AC-0003-32), so the
member dialog can show what a servidor has before it is replaced.

## 4. Behaviour

### 4.1 Navigation

**AC-0014-01** — Every perfil finds Insumos in the sidebar
```gherkin
Given a signed-in usuario of any perfil
When  any page of the shell is shown
Then  the sidebar lists "Insumos" after "ATAs" and before "Membros"
And   choosing it opens /insumos, whose page header reads "Insumos"
```
The slot `docs/product/user-map.md` reserves for it.

### 4.2 The catalogue

**AC-0014-02** — The catalogue is listed and searched
```gherkin
Given insumos registered
When  /insumos is shown
Then  a table lists them with the columns SKU, Descrição, Unidade, Grupo, Código DOMS and Situação,
      ordered by SKU
And   Grupo reads as its path, "MATERIAL ODONTOLÓGICO › RESTAURADORES"
And   each row opens that insumo
When  "clorex" is typed in "Buscar por SKU, código DOMS ou descrição"
Then  the list holds the insumos the API returns for q "clorex"
When  there are more than 25
Then  the list shows 25 and a control to move between pages, with the total
```
SKU and Código DOMS are codes, in monospace. The search waits for 300 ms of no
typing before it asks, so a word typed is one request, not one per letter.

**AC-0014-03** — The catalogue filters by grupo and situação
```gherkin
Given /insumos
When  a grupo and a situação are chosen
Then  the list holds only the insumos the API returns for them, the grupos below the chosen one included
And   the search, the filters and the page live in the URL (?q=clorex&grupo=…&situacao=ativo&pagina=2)
And   reloading the page keeps them
When  the filters are cleared
Then  the full list returns, from its first page
```
The grupo filter lists every grupo of the tree the API returns, as its path; the
situação filter lists Ativo, Descontinuado and Substituído.

**AC-0014-04** — Situação reads as text
```gherkin
Given an insumo in the list or on its page
Then  "ativo" reads "Ativo" with no mark
And   "descontinuado" reads "Descontinuado" in muted text
And   "substituido" reads "Substituído por {sku do substituto}" in muted text
```
DESIGN.md §4: a status is text, never a pill. The situação is the API's
(AC-0003-12); the screen never derives it.

**AC-0014-05** — An empty catalogue says why
```gherkin
Given no insumo registered
When  /insumos is shown
Then  the list reads "Nenhum insumo cadastrado."
And   a gestor is offered "Cadastrar insumo" and "Importar catálogo", a servidor "Cadastrar insumo"
Given a search or filters that match nothing
Then  it reads "Nenhum insumo com esses filtros." with a control to clear them
Given a servidor with no grupos de materiais
Then  it reads "Você ainda não tem grupos de materiais. Peça a um gestor para definir os seus."
And   "Cadastrar insumo" is not offered
```
A servidor with no grupos sees an empty tree (AC-0003-29), which is how the screen
knows; without the sentence an empty list would read as an empty catalogue.

**AC-0014-06** — A servidor is told what it sees
```gherkin
Given a servidor with grupos on /insumos
Then  the page header's description reads "Insumos dos seus grupos de materiais: {nomes}"
```
`{nomes}` are the roots of the tree the API returns to the servidor. The scope is
the API's (AC-0003-29); the sentence only says it.

**AC-0014-07** — Loading and failure
```gherkin
Given a request of any page of this spec still pending
When  the page is shown
Then  each block shows a skeleton of its own shape, announced once as "Carregando..."
Given a request that fails
Then  the error notice of DESIGN.md §6 shows in place of that block, with the gestor contact (AC-0010-57)
And   no block reads as empty
```

### 4.3 Registering and correcting an insumo

**AC-0014-08** — A servidor or a gestor registers an insumo on its own page
```gherkin
Given a gestor or a servidor on /insumos
When  "Cadastrar insumo" is chosen
Then  /insumos/novo opens with the page header "Novo insumo" and the fields
      SKU, Descrição, Unidade, Grupo, Código DOMS (opcional), Código externo (opcional)
      and Quantidade de referência (opcional)
And   Grupo is chosen from the grupos the API returns to this usuario, each as its path, never typed
When  "Cadastrar insumo" is chosen with SKU, Descrição, Unidade and Grupo filled
Then  POST /api/v1/insumos is called once
And   the new insumo's page opens, with no banner
When  "Voltar" is chosen
Then  /insumos returns and nothing is sent
Given an auditor
Then  "Cadastrar insumo" is not offered
And   /insumos/novo, opened by its address, says "Seu perfil não permite esta ação." with a link back
```
No review step: an insumo is seven fields, four of them required, and a mistake is
corrected by "Editar" (AC-0014-10). Hiding the control is cosmetic; the API refuses
the write (AC-0003-01).

**AC-0014-09** — The API's refusal lands on the field it names
```gherkin
Given the registration or the edit page
When  the API answers 422 "INVALID_DATA" with `fields`
Then  each named field shows its message below it and is marked invalid
And   focus moves to the first of them, and every value typed is kept
When  the API answers 422 "INVALID_SKU"
Then  SKU shows the API's message, which states the format and an example
When  the API answers 422 "INVALID_DOMS_CODE"
Then  Código DOMS shows the API's message
When  the API answers 409 "INSUMO_DUPLICADO"
Then  SKU shows the API's message, which names the existing insumo when the usuario can see it
```
The page checks only that a required field is not empty. The SKU is shown as
typed and normalised by the API (AC-0003-02); the screen does not uppercase it,
so what is stored is what the API says it stored.

**AC-0014-10** — A servidor or a gestor corrects an insumo
```gherkin
Given a gestor or a servidor on an insumo's page
When  "Editar" is chosen
Then  /insumos/{id}/editar opens with the page header "Editar insumo {sku}" and the fields of
      AC-0014-08 but SKU, filled and editable
And   SKU is shown, not editable, with "Para mudar o SKU, use Alterar SKU na página do insumo."
When  the edit is saved
Then  PATCH /api/v1/insumos/{id} carries only the fields that changed
And   an optional field emptied is sent as null, which clears it
And   the insumo's page opens with the new values, with no banner
And   a refusal lands on its field as in AC-0014-09
Given an auditor
Then  "Editar" is not offered
```

**AC-0014-11** — Quantities are typed in pt-BR and sent exactly
```gherkin
Given Quantidade de referência, Quantidade, Valor unitário or Quantidade acrescida
When  "1.000" is typed in a quantity
Then  the API receives "1000"
When  "2,5" is typed in a quantity
Then  the API receives "2.5"
When  "0,00599" is typed in Valor unitário
Then  the API receives "0.00599"
When  "1,23456789" is typed in Valor unitário
Then  the API receives "1.23456789" and refuses it, and nothing is rounded (AC-0003-20)
```
As money is in AC-0013-09: text to text, never through a floating-point number.

### 4.4 The insumo page

**AC-0014-12** — The insumo page shows the insumo as the API holds it
```gherkin
Given an insumo
When  /insumos/{id} is shown
Then  the page header reads the SKU, with the situação of AC-0014-04 and the descrição
And   it shows Descrição, Unidade, Grupo (its path), Código DOMS, Código externo,
      Quantidade de referência and Cadastrado em
And   an empty optional field reads "—"
When  the insumo is substituído
Then  "Substituído por" names the substitute's SKU and descrição, and opens it
And   "Descontinuado em" reads its date
When  the id does not exist, or the insumo is outside a servidor's grupos
Then  the page reads "Insumo não encontrado." with a link back to /insumos
```
The two cases read the same because the API answers 404 to both (AC-0003-29).

**AC-0014-13** — The ATAs an insumo is an item of
```gherkin
Given an insumo that is an item of two ATAs
When  its page is shown
Then  a table "ATAs" has the columns ATA, Status, Quantidade and Valor unitário
And   each row opens that ATA
When  it is an item of none
Then  the table reads "Este insumo não é item de nenhuma ATA."
```
This is Tela 3's "ATA" column as SPEC-0003 §2 resolved it: the ATAs the insumo
takes part in, not an owner.

**AC-0014-14** — A gestor changes the SKU, with a justification
```gherkin
Given a gestor on an insumo's page
When  "Alterar SKU" is chosen
Then  a dialog asks for the Novo SKU and a Justificativa, up to 500 characters
And   "Alterar SKU" stays disabled until both are filled
When  it is confirmed
Then  POST /api/v1/insumos/{id}/alterar-sku carries both
And   the page shows the new SKU, with no banner
When  the API answers "INVALID_SKU" or "INSUMO_DUPLICADO"
Then  Novo SKU shows the API's message and the dialog stays open
```

**AC-0014-15** — A gestor discontinues, substitutes and reactivates
```gherkin
Given a gestor on an "ativo" insumo
Then  "Descontinuar" and "Substituir" are offered
When  "Descontinuar" is chosen
Then  a confirmation says the insumo stops entering new items and every ATA that holds it keeps it,
      and asks for a Justificativa
When  "Substituir" is chosen
Then  a dialog asks for the Substituto, searched by SKU or descrição among the "ativo" insumos,
      and a Justificativa
When  the API answers "INVALID_SUBSTITUTE"
Then  Substituto shows the API's message
Given a gestor on a "descontinuado" or "substituido" insumo
Then  "Reativar" is offered, and asks for a Justificativa
When  any of the three is confirmed
Then  the page shows the situação the API returned, with no banner
Given a servidor or an auditor
Then  none of the three, nor "Alterar SKU", is offered
```
The offers mirror AC-0003-14 to -16 so a gestor is not shown a dead button; the API
stays the authority, and a refusal it sends is shown in the dialog.

### 4.5 Grupos de materiais

**AC-0014-16** — The grupos are shown as a tree
```gherkin
Given grupos at three levels
When  /insumos/grupos is shown, from "Grupos de materiais" on /insumos
Then  the page header reads "Grupos de materiais"
And   every grupo is listed under its parent, indented by its nivel, in the order the API returns
When  there is none
Then  it reads "Nenhum grupo cadastrado."
And   a gestor is offered "Novo grupo" and "Importar catálogo", which creates them (AC-0003-06)
```
A servidor sees its own grupos and those below them, as the API returns them
(AC-0003-29).

**AC-0014-17** — A gestor creates and renames grupos
```gherkin
Given a gestor on /insumos/grupos
When  "Novo grupo" is chosen
Then  a dialog asks for the Nome and creates a grupo at nivel 1
When  "Adicionar subgrupo" is chosen on a nivel 1 or nivel 2 grupo
Then  the same dialog creates it below that grupo
And   a nivel 3 grupo offers no "Adicionar subgrupo"
When  "Renomear" is chosen on any grupo
Then  the dialog is filled with its nome, and saving it sends only the new nome
When  the API answers 409 "DUPLICATE_GROUP"
Then  Nome shows the API's message and the dialog stays open
When  either succeeds
Then  the tree shows the grupo where the API put it, with no banner
Given a servidor or an auditor
Then  no create or rename control is offered
```
The screen does not offer a fourth level, mirroring AC-0003-09; the API refuses one.

### 4.6 Importing a file

**AC-0014-18** — A gestor checks a catalogue file before importing it
```gherkin
Given a gestor on /insumos
When  "Importar catálogo" is chosen
Then  /insumos/importar opens with the page header "Importar catálogo", the columns the file takes,
      which are required, and "Baixar modelo"
When  "Baixar modelo" is chosen
Then  a file "modelo-catalogo.csv" downloads with the header line of AC-0003-06, separated by ";"
When  a .csv file is chosen and "Conferir arquivo" is chosen
Then  POST /api/v1/insumos/importacao?dry_run=true carries the file's bytes unchanged, as text/csv
And   nothing has been written
```
The file goes as bytes, not as text the browser decoded, so a Windows-1252 file
reaches the API as Windows-1252 and the API reads it (AC-0003-18).

**AC-0014-19** — The check shows what the import will do
```gherkin
Given a file the dry run accepts
Then  the page shows "O arquivo pode ser importado" and how many insumos will be created, updated and
      left unchanged, and how many descrições will be corrected
And   every ignored column is named, with the API's note beside it, such as the one for estoque
And   "Importar" and "Escolher outro arquivo" are offered
When  "Importar" is chosen
Then  the same file is sent without dry_run, once
And   the page shows "Importação concluída" with the counts the API returned and a link to the catalogue
Given a file the dry run refuses with "IMPORT_REJECTED"
Then  the page shows the API's message and a table of Linha, Coluna and Problema, one row per entry
      of `rows`, in the order the API returns
And   "Importar" is not offered, only "Escolher outro arquivo"
Given a file refused with "INVALID_FILE"
Then  the page shows the API's message and only "Escolher outro arquivo"
```
The import is all or nothing (AC-0003-07), so the screen never offers to import the
valid lines. The second request repeats the first, and the counts it returns are
the ones shown, because the catalogue may have changed in between.

**AC-0014-20** — A gestor imports an ATA's items the same way
```gherkin
Given a gestor on a "Vigente" or "Suspensa" ATA's page
When  "Importar itens" is chosen
Then  /atas/{id}/itens/importar opens with the page header "Importar itens da ATA {número}",
      the columns of AC-0003-26, which are required, and "Baixar modelo"
And   "Baixar modelo" downloads "modelo-itens-ata.csv" with that header line, separated by ";"
And   the file is checked, shown and imported as in AC-0014-18 and -19, against
      POST /api/v1/atas/{id}/itens/importacao, with the counts of items added, corrected and unchanged
When  the import is concluded
Then  "Voltar para a ATA" opens the ATA's page, with the items the API now returns
Given a servidor or an auditor, or an ATA that is "Encerrada" or "Cancelada"
Then  "Importar itens" is not offered
And   the page, opened by its address, says "Seu perfil não permite esta ação." or shows the API's
      "ATA_NAO_EDITAVEL" message, with a link back
```

### 4.7 The items of an ATA

**AC-0014-21** — The ATA page lists its items
```gherkin
Given an ATA with items
When  /atas/{id} is shown
Then  a section "Itens" follows the ATA's fields, before "Aditivos"
And   a table has the columns Nº, SKU, Descrição, Unidade, Quantidade, Valor unitário, Valor total and
      Fornecedor, in the order the API returns
And   Valor unitário reads with at least 2 and up to 5 decimals, "R$ 0,00599", "R$ 1,50"
And   Valor total reads to the centavo, "R$ 5,99"
And   Quantidade reads the contracted quantity, and when an aditivo raised it, "120 (100 + 20)"
And   Fornecedor is empty on an item whose fornecedor is the ATA's, and names the razão social otherwise
And   each SKU opens its insumo
When  the ATA has no item
Then  the section reads "Nenhum item cadastrado."
And   a gestor is offered "Adicionar item" and "Importar itens" when the ATA is "Vigente" or "Suspensa"
```
Quantidade, Valor unitário and Valor total are the API's (AC-0003-21); the screen
formats them and never multiplies.

**AC-0014-22** — The sum of the items is shown beside the ATA's value
```gherkin
Given a gestor or an auditor on an ATA whose items add up to R$ 9.800,00 and whose valor_total is R$ 10.000,00
Then  below the items reads "Soma dos itens: R$ 9.800,00 · Valor total da ATA: R$ 10.000,00"
And   because the API says they differ, a notice reads
      "A soma dos itens difere do valor total da ATA. Confira os itens ou o valor da ATA."
When  they are equal
Then  the line shows with no notice
Given a servidor on an ATA's page
Then  the section's description reads "Itens dos seus grupos de materiais."
And   neither the sum nor the notice is shown
```
A servidor sees only its grupos' items (AC-0003-22, -29), so their sum would differ
from the ATA's total for a reason that is not an error. A difference is shown,
never refused (AC-0003-22).

**AC-0014-23** — A gestor adds an item
```gherkin
Given a gestor on a "Vigente" or "Suspensa" ATA
When  "Adicionar item" is chosen
Then  a dialog asks for the Insumo, searched by SKU or descrição among the "ativo" insumos,
      the Quantidade, the Valor unitário (R$) and the Nº do item (opcional)
And   "Fornecedor diferente do da ATA" reveals CNPJ do fornecedor and Razão social
When  it is submitted
Then  POST /api/v1/atas/{id}/itens carries it once
And   the item appears in "Itens", with no banner
When  the API answers 409 "ITEM_ATA_DUPLICADO" or "INSUMO_DESCONTINUADO"
Then  Insumo shows the API's message and the dialog stays open, every value kept
When  the API answers 422 "INVALID_DATA" with `fields`
Then  each named field shows its message, as in AC-0014-09
Given an ATA that is "Encerrada" or "Cancelada"
Then  "Adicionar item" is not offered
```
The CNPJ is shown and sent as AC-0013-09 does.

**AC-0014-24** — A gestor corrects or removes an item
```gherkin
Given a gestor on a "Vigente" or "Suspensa" ATA
When  "Ações para {sku}" is opened on an item
Then  it offers "Corrigir", "Aditivo de quantidade" when the ATA is "Vigente", and "Remover"
When  "Corrigir" is chosen
Then  the dialog of AC-0014-23 opens filled with the item
And   saving sends to PATCH /api/v1/atas/{id}/itens/{item_id} only the fields that changed
And   unticking "Fornecedor diferente do da ATA" sends fornecedor as null, which returns the item to the ATA's
When  "Remover" is chosen
Then  a confirmation names the item's SKU and says the item leaves the ATA and its sum
When  it is confirmed
Then  POST /api/v1/atas/{id}/itens/{item_id}/remover is called and the item leaves "Itens", with no banner
When  the API answers "ATA_NAO_EDITAVEL"
Then  the dialog shows the API's message and the page reloads the ATA
Given an ATA that is "Encerrada" or "Cancelada", or a servidor or an auditor
Then  no item action is offered
```

**AC-0014-25** — A gestor records an aditivo de quantidade on an item
```gherkin
Given a gestor on a "Vigente" ATA
When  "Aditivo de quantidade" is chosen on an item
Then  a dialog names the item's SKU and its contracted quantity, and asks for the
      Quantidade acrescida and a Justificativa
When  it is submitted
Then  POST /api/v1/atas/{id}/aditivos carries kind "quantidade", the item and both values
And   the item's Quantidade shows the new contracted quantity, and the aditivo appears in "Aditivos",
      with no banner
When  the API answers 422 "ADITIVO_ACIMA_DO_LIMITE"
Then  Quantidade acrescida shows the API's message
When  a correction of the item's Quantidade is refused with "ADITIVO_ACIMA_DO_LIMITE"
Then  Quantidade shows the API's message in the dialog of AC-0014-24
```
The screen does not compute the 25% ceiling; the API does (AC-0003-28).

**AC-0014-26** — Aditivos de quantidade are listed with the others
```gherkin
Given an ATA with an aditivo de quantidade of 20 on the item of SKU "CLORDEG21", unidade "UN"
When  its page is shown
Then  the "Aditivos" table of AC-0013-11 shows it with Tipo "Quantidade" and
      Acréscimo ou novo fim "+20 UN · CLORDEG21"
When  the item is outside a servidor's grupos
Then  the row reads "+20" with no SKU
```

**AC-0014-27** — Readers read
```gherkin
Given a servidor or an auditor on an ATA's page
Then  the items are shown, a servidor's within its grupos
And   no add, correct, remove, import or aditivo control is offered
```

### 4.8 A servidor's grupos

**AC-0014-28** — A gestor sets a servidor's grupos from the member list
```gherkin
Given a gestor on /members
When  "Ações para {nome}" is opened on a servidor that is not desativado
Then  it offers "Grupos de materiais"
When  it is chosen
Then  a dialog "Grupos de materiais de {nome}" lists the tree with a checkbox per grupo,
      the servidor's current grupos ticked, as GET /api/v1/usuarios/{id}/grupos-materiais returns them
And   a grupo below a ticked one shows as included, ticked and disabled, with "Incluído por {grupo}"
And   it says "O servidor vê os insumos dos grupos marcados e dos grupos abaixo deles."
When  "Salvar grupos" is chosen
Then  POST /api/v1/usuarios/{id}/grupos-materiais carries the ticked grupos, never the included ones
And   the dialog closes, with no banner
When  every box is unticked and it is saved
Then  the dialog first says "Sem grupos, o servidor não vê nenhum insumo." and asks to confirm
Given a gestor or an auditor member, or a desativado servidor
Then  "Grupos de materiais" is not offered
Given an auditor on /members
Then  "Grupos de materiais" is not offered
```
Below a ticked grupo, the descendants are already in scope (AC-0003-29), so ticking
them would say nothing; sending only the ticked keeps the stored set as the gestor
chose it. The set replaces what the servidor had (AC-0003-30).

### 4.9 Field help

**AC-0014-29** — Every field says what it is
```gherkin
Given any form or dialog of this spec
Then  each field below has an "i" button beside its label, named "Sobre {label}"
And   it opens and closes as AC-0013-19 says
```

| Field | Explanation |
| --- | --- |
| SKU | Código do item no CAME, só letras e números, sem espaços nem pontos, ex. CLORDEG21. Não pode repetir outro insumo. |
| Descrição | Nome do item como deve aparecer nas ATAs e nas notas. Sem o código DOMS na frente. |
| Unidade | Unidade de dispensação, ex. UN, CX, L. |
| Grupo | Grupo de materiais do DOMS. Um servidor só vê os insumos dos seus grupos. |
| Código DOMS (opcional) | Código do item no DOMS, só números, ex. 26829. Não pode repetir outro insumo. |
| Código externo (opcional) | Identificador interno do DOMS (mercadoriaId), usado para cruzar arquivos. |
| Quantidade de referência (opcional) | Quantidade usada como referência para alertas. Não é estoque. |
| Novo SKU | Novo código do item. As ATAs e notas que usam o insumo continuam ligadas a ele, e o SKU anterior fica no histórico. |
| Substituto | Insumo ativo que passa a ser usado no lugar deste. As ATAs e notas antigas continuam com este. |
| Justificativa | Por que a mudança foi feita. Fica no histórico. |
| Nome (grupo) | Nome do grupo, como no DOMS. Não pode repetir outro grupo no mesmo nível. |
| Insumo | Insumo do catálogo. Um insumo descontinuado não entra em itens novos. |
| Quantidade | Quantidade registrada na ATA para o item, até 3 casas decimais. |
| Valor unitário (R$) | Preço por unidade como consta na ATA, até 5 casas decimais, ex. 0,00599. O valor do item é arredondado ao centavo. |
| Nº do item (opcional) | Número do item no pregão. |
| CNPJ do fornecedor | Fornecedor deste item, quando não é o da ATA. 14 caracteres, com ou sem pontuação. |
| Quantidade acrescida | Quanto o aditivo soma à quantidade do item. Todos os aditivos do item juntos não passam de 25% da quantidade original. |
| Arquivo CSV | Arquivo em CSV, separado por ";" ou ",", em UTF-8 ou Windows-1252, até 5 MB e 10.000 linhas. |

Every rule an explanation states is the API's (SPEC-0003), so the text describes
what the system enforces and enforces nothing itself.

### 4.10 Layout

**AC-0014-30** — Every page holds at every width
```gherkin
Given every page of this spec and the ATA page with its items, with their dialogs open and closed
When  they are shown at 360, 768 and 1440 px
Then  the page does not scroll sideways, and a wide table scrolls inside its own frame
And   they pass the accessibility check of AC-0010-44
And   every action, the insumo search of a dialog and the file choice can be reached and confirmed
      with the keyboard
```

## 5. Errors and edge cases

| Condition | What the screen shows |
| --- | --- |
| Request pending | Skeleton of the block's shape (AC-0014-07) |
| Request fails | Error notice with the gestor contact (AC-0014-07) |
| `INVALID_DATA`, `INVALID_SKU`, `INVALID_DOMS_CODE`, `INSUMO_DUPLICADO` | The API's message under the field it names (AC-0014-09) |
| `INVALID_SUBSTITUTE`, `DUPLICATE_GROUP` | The API's message under the field, dialog open (AC-0014-15, -17) |
| `ITEM_ATA_DUPLICADO`, `INSUMO_DESCONTINUADO` | The API's message under Insumo (AC-0014-23) |
| `ADITIVO_ACIMA_DO_LIMITE` | The API's message under the quantity (AC-0014-25) |
| `ATA_NAO_EDITAVEL`, `ATA_NAO_VIGENTE` | The API's message in the open dialog, and the ATA reloaded (AC-0014-24) |
| `IMPORT_REJECTED` | The API's message and the table of lines (AC-0014-19) |
| `INVALID_FILE` | The API's message (AC-0014-19) |
| `NOT_FOUND` on /insumos/{id} | "Insumo não encontrado." with a link back (AC-0014-12) |
| `PERFIL_NAO_AUTORIZADO` | The API's message; reachable only if the perfil changed while the page was open |
| Session expired | SPEC-0010's session handling, as on every page |

## 6. Permissions

| Action | gestor | servidor | auditor |
| --- | --- | --- | --- |
| See /insumos, /insumos/{id}, /insumos/grupos and an ATA's items | ✓ | ✓, its grupos | ✓ |
| Cadastrar and editar an insumo | ✓ | ✓, its grupos | — |
| Alterar SKU, descontinuar, substituir, reativar | ✓ | — | — |
| Import the catalogue; create and rename grupos | ✓ | — | — |
| Add, correct, remove and import items; aditivo de quantidade | ✓ | — | — |
| Set a servidor's grupos | ✓ | — | — |

The API enforces it (SPEC-0003 §3.9, invariant 8). The screens only hide what a
perfil cannot do.

## 7. API surface

One endpoint added to SPEC-0003 for these screens, `GET
/api/v1/usuarios/{id}/grupos-materiais` (AC-0003-32). The rest are SPEC-0003's:

| Method | Path | Used by |
| --- | --- | --- |
| GET | `/api/v1/insumos?page=&size=&q=&grupo_id=&status=` | AC-0014-02, -03, -05, -15, -23 |
| POST | `/api/v1/insumos` | AC-0014-08, -09 |
| GET, PATCH | `/api/v1/insumos/{id}` | AC-0014-10, -12, -13 |
| POST | `/api/v1/insumos/{id}/alterar-sku`, `descontinuar`, `substituir`, `reativar` | AC-0014-14, -15 |
| POST | `/api/v1/insumos/importacao?dry_run=` | AC-0014-18, -19 |
| GET, POST | `/api/v1/grupos-materiais` | AC-0014-03, -06, -08, -16, -17, -28 |
| PATCH | `/api/v1/grupos-materiais/{id}` | AC-0014-17 |
| GET, POST | `/api/v1/atas/{id}/itens` | AC-0014-21, -22, -23 |
| PATCH | `/api/v1/atas/{id}/itens/{item_id}` | AC-0014-24, -25 |
| POST | `/api/v1/atas/{id}/itens/{item_id}/remover` | AC-0014-24 |
| POST | `/api/v1/atas/{id}/itens/importacao?dry_run=` | AC-0014-20 |
| POST | `/api/v1/atas/{id}/aditivos` (`kind: "quantidade"`) | AC-0014-25, -26 |
| GET, POST | `/api/v1/usuarios/{id}/grupos-materiais` | AC-0014-28 |

## 8. Audit events

None of its own. Every write is SPEC-0003's endpoint, which writes its audit row in
the same transaction (AC-0003-31). The new GET writes nothing.

## 9. Open questions

None block this version.

## 10. Implementation plan

- Backend: `GET /api/v1/usuarios/{id}/grupos-materiais` in `api/users.py`, gestor
  only, answering `UserGruposOut` from `insumos.grupos_of_user`, 404 for an unknown
  member; a test for AC-0003-32 and its row in the permission matrix. No migration.
- Modules:
  - `NAV_MODULES` in `frontend/lib/constants.ts` gains "Insumos" after "ATAs".
  - `frontend/lib/insumos/` holds the types, the words for each situação, the
    import columns and the field help (`constants.ts`), the grupo paths and the
    "included by" rule of AC-0014-28 (`grupos.ts`), and the model files
    (`template.ts`).
  - `frontend/lib/format.ts` gains pt-BR quantity parsing and formatting, and the
    unit price with 2 to 5 decimals.
  - `frontend/app/(app)/insumos/` holds the list, `novo/`, `[id]/`, `[id]/editar/`,
    `grupos/` and `importar/`; `frontend/app/(app)/atas/[id]/itens/importar/` the
    items import.
  - `frontend/components/insumos/` holds the insumo form, the situação, the grupo
    picker, the insumo search, the action dialogs, the grupo tree and the import
    flow, shared by both files; `frontend/components/atas/items.tsx` the items
    section and its dialogs; `frontend/components/members/grupos-dialog.tsx`.
- New dependencies: none.
- Tests:
  - `frontend/tests/insumos.test.ts` (Vitest) covers quantity and unit price
    parsing and formatting, the grupo paths, the "included by" rule and the model
    files.
  - `frontend/e2e/insumos.spec.ts` (Playwright, against the real API) has one test
    per AC; AC-0014-30 joins `responsive.spec.ts` and `accessibility.spec.ts`.

## 11. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-21 | Initial draft. The screens for SPEC-0003 v1.1: the catalogue, its form and its page with the gestor's actions, the grupo tree, both imports with a check before writing, the items section of the ATA page with the aditivo de quantidade, and a servidor's grupos on the member list. One endpoint added to SPEC-0003 (AC-0003-32). |
| 1.0 | 2026-10-21 | Approved by the product owner as drafted, with SPEC-0003 v1.2. |
