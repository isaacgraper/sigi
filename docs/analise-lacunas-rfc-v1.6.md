# Análise de Lacunas — RFC SIGI v1.6 × Reunião de Stakeholders (17/08/2026)

> **Status: histórico.** *(Atualizado em 2026-09-03.)* Esta análise foi escrita
> antes de as planilhas do Eduardo chegarem e antes de a branch `dev` ser
> conhecida. Seus achados foram, depois, verificados contra os dados reais e
> incorporados ao repositório da forma que o processo exige — não no
> `rfc-sigi-v1.7.md`, que está **superado**, mas em:
>
> - `ADR-0007` — a NE é multi-item (achado que esta análise não tinha)
> - `ADR-0008` — ingestão de sinais de estoque do DOMS
> - `ADR-0009` — dados operacionais como fonte de verdade
> - `docs/architecture/data-sources.md` — o de-para campo a campo
> - `docs/open-questions.md` — as questões resolvidas por dado
>
> Vários pontos daqui foram **corrigidos** pela evidência: a cadência é mensal e
> não diária, o estoque mínimo vem pronto do DOMS, e a "decisão D1" sobre o
> aditivo de 25% era redundante — `RF15`/`RN15` já fixavam isso.
> Permanece como registro do raciocínio, não como fonte.

> Documento de trabalho. Confronta o **RFC_SIGI_v1_6.docx** (última versão; a cópia de
> 21/08 é byte-idêntica, portanto a reunião ainda **não** foi incorporada a nenhum
> documento) com duas fontes novas:
>
> 1. Transcrições dos dois áudios da reunião de 17/08/2026 com Anderson e Eduardo.
> 2. `RELATÓRIO GERAL CAME` — o painel que os stakeholders compartilharam em tela
>    (Looker Studio, 4 páginas), que é **o sistema que eles usam hoje**.

---

## 1. Conclusão principal

O RFC v1.6 descreve um **sistema de governança documental do ciclo ATA → NE → NF**.
O relatório CAME e a reunião descrevem um **cockpit de cobertura de estoque e de
antecipação de compra**, no qual ATA, NE e NF são *insumos para a decisão de comprar*,
não o produto final.

Essa divergência não é de detalhe: entre a v1.5 e a v1.6 o documento **removeu
deliberadamente** o controle de estoque como capacidade de primeira classe —

| Versão | Texto |
| :-- | :-- |
| v1.4 / v1.5 | "Controle de estoque por ATA com **saldo atualizado em tempo real**" |
| **v1.6** | "Visão de saldo por ATA como **dado derivado** do ciclo de empenhos, **não como módulo de controle de estoque independente**" |

E RF03 hoje afirma que a quantidade de referência "é opcional e serve apenas para
**alertas de processo, não para controle de estoque**".

As evidências da reunião apontam na direção oposta. A decisão que o setor toma todos
os dias é: *"a cobertura deste item caiu abaixo de 3 meses — preciso comprar, e a ATA
vigente ainda me atende?"*. Recomendo tratar isso como a correção mais importante da
v1.7.

---

## 2. O que o RELATÓRIO GERAL CAME contém de fato

Extraí o texto vetorial das 4 páginas do PDF. Estrutura:

### Página 1 — Atendimento por mercadoria e por unidade
- Tabela **MERCADORIAS**: item × `SOLICITADO` × `ATENDIDO` × `VALOR`
  (ex.: `AGULHA 210.990 / 199.200`; `AGUA 915 / 846 / R$ 9.280,62`).
- Tabela **UNIDADE**: `ESF | ESB | EMULT | EMAP | EAPP | EMAD | MULT | AUT | POPULAÇÃO`
  para ~11 unidades (Ubsf Bucarein, Costa E Silva, Floresta, Fátima, Comasa,
  Jarivatuba, Jardim Paraíso, Hospital São José, Pa Norte 24h, Upa Leste 24h,
  Upa Sul 24h, Ambulatório).
- Barras de **VALOR ATENDIDO por unidade**: R$ 10.939.673,18 (maior) … R$ 385.533,16.

### Página 2 — Série temporal
- `SOLICITADO` × `ATENDIDO` mês a mês, **mai/2025 → jun/2026** (faixa ~R$ 1,63 mi a
  R$ 2,64 mi/mês).
- Scorecards: `MÉDIA SOLICITADO | MÉDIA ATENDIDO`, `ESTOQUE ATUAL`.

### Página 3 — Andamento dos processos licitatórios
- Tabela: `ANO | Nº ITEM | ITEM | OBJETO | STATUS ACOMPANHAMENTO | SKU |
  PREVISÃO DE ABERTURA | NOVO PROCESSO | VENCIMENTO VIGENTE | PROGRESSO`.
- Gráfico **PLANEJADO × REAL** em dias (eixo 0–320) sobre as etapas:
  `COMUNICADO → ACP → SAP → PGM → LCT → PUBLICAÇÃO DO EDITAL → PREGÃO →
  PROPOSTAS → HOMOLOGAÇÃO`.
- Indicadores: `PROCESSO CONCLUÍDO EM 310 DIAS`, `25,59%`,
  `TEMPO SEM PROCESSO VIGENTE`.

### Página 4 — Visão-mestre do item (a tela mais densa)
Colunas identificadas: `SKU | ITEM | GRUPO | CONSUMO MÊS | DIAS EST | EST. CLASSIF |
STATUS EST | PROCESSO SEI | ANO | VENCIMENTO | DIAS S/ PROC. | PREGÃO | ATA |
MOVIMENT | QTD SALDO | STATUS DA ATA | STATUS DO PREGÃO | SUGESTÕES DE TROCA |
INFORMAÇÕES EXTRAS | EMPENHO`.

- Classificação de estoque em faixas **A / B / C / D / S**.
- `STATUS EST`: `BAIXO ESTOQUE`, `DISPONÍVEL`, percentuais (63,6% / 32,1% / 80%).
- `STATUS DA ATA`: `VIGENTE`, `VENCIDA`, `PRORROGADA`, `SALDO ZERO`.
- `STATUS DO PREGÃO`: `FINALIZADO`, `AGUARDANDO`, `EM PUBLICAÇÃO`,
  `ANÁLISE DE ITENS`, `EM ANDAMENTO`.

> **Leitura**: as páginas 3 e 4 mostram que o setor já opera um objeto de domínio que o
> RFC não modela — o **processo licitatório com ciclo de vida próprio**, anterior à ATA.

---

## 3. Lacunas por severidade

### P0 — Contradições diretas entre o RFC e o que foi dito na reunião

#### P0.1 Autenticação: Gov.br está errado
- **RFC**: RF01 e §6.2 — "e-mail institucional **ou Gov.br**", "Gov.br OAuth 2.0".
- **Reunião**: os servidores **já possuem matrícula e usuário** provisionados pela TI
  ("já foi feito um processo da TI, no usuário de vocês"). A discussão foi sobre
  **Entra ID** ("É uma Entra, né?" / "Dá pra colocar. É possível."). Gov.br **não foi
  mencionado em momento algum**.
- **Por que importa**: Gov.br é federação **cidadão→Estado**; o público do SIGI é
  servidor interno. Manter Gov.br no RFC promete uma integração que ninguém pediu e
  omite a que foi efetivamente discutida.
- **Ação**: trocar Gov.br por **Entra ID / SSO institucional** em RF01, UC01, §6.2 e na
  Tela 1. Mover Gov.br para "futuro" ou remover.

#### P0.2 Diagrama de casos de uso não separa os atores
- **Feedback textual**: *"aqui você tinha escrito muito, assim, o gestor e servidor…
  eles não faziam a mesma coisa, como se fossem os mesmos casos de uso, e só fazendo a
  mesma coisa"*.
- **Estado do RFC**: a tabela §2.2 (UC01–UC12) **não tem coluna de ator**. A matriz RBAC
  de §6.2 diferencia os perfis, mas o diagrama — que é o que eles viram — não.
- **Ação**: adicionar coluna **Ator** em §2.2 e redesenhar o diagrama. Confirmado na
  reunião: Anderson e Eduardo = acesso completo; demais restritos; **página de
  administração** para atribuir acesso por usuário.

#### P0.3 Papéis reais ausentes do modelo RBAC
O RFC tem 3 perfis (`gestor`, `servidor`, `auditor`). A reunião introduz dois que não
existem no documento:
- **Comprador** — tem **lista de tarefas própria**, segmentada por *grupo de materiais*;
  recebe alerta quando um item entra na lista de compra. Foi descrito como "um módulo a
  mais".
- **Gestor da unidade** — faz as solicitações dentro das janelas do cronograma; **não
  enxerga o estoque central** ("elas não têm visão do nosso estoque").

#### P0.4 KPIs do Dashboard foram rejeitados
- **RFC Tela 2**: "ATAs ativas" / "Insumos pendentes" / "**NFs lançadas hoje**".
- **Reunião**: *"Esse daí não é o que a gente tem… não é o que a gente quer ver"* e,
  sobre NF, *"imagina que se eu tiver NF aqui, isso não importa"*.
- **Substituto proposto pelos próprios stakeholders** — o **delta semanal da lista
  crítica**: *"10 entraram e 10 saíram, estamos no zero a zero… entraram mais 10 itens
  na lista crítica, eu tinha 30, estou com 40, piorou essa semana"*. E, no lugar de
  "NFs lançadas na semana", **"itens que entraram essa semana"**.

#### P0.5 Notificação por e-mail a cada mudança de status é inviável
- **RFC RF09**: notificar "quando o status de um fornecimento for alterado".
- **Reunião**: *"o pessoal da TI já me falou: e-mail demais, eles vão bloquear por spam.
  A gente tem que ser mais cauteloso… escolher as coisas que realmente são
  extremamente [importantes]"*.
- **Ação**: substituir por notificação **seletiva e agregada** (digest por comprador /
  por grupo de material), com limiar configurável.

#### P0.6 Importação do e-Publica não está validada
- **RFC**: UC03, RF04 e a Tela 4 afirmam "importação do e-Publica" por nº de processo.
- **Reunião**: *"a ATA não sai do DOMS da Abranet. Ela é do **República**"* e *"não sei
  se o República emite CSV — é uma coisa que a gente não foi ver se é possível"*.
- **Ação**: rebaixar a importação a **hipótese a validar**; assumir como caminho
  primário o **cadastro manual da ATA + upload CSV dos itens** (que foi explicitamente
  aprovado: *"a gente consegue, depois de criar a ATA, jogar um CSV com os itens
  dentro"*). Registrar "República" como plataforma — o nome não aparece no RFC.

---

### P1 — Domínio ausente do modelo de dados

O modelo de §5.2 tem `Usuario, Insumo, ATA, ItemATA, NotaEmpenho, NotaFiscal,
Fornecedor, HistoricoMovimentacao`. Faltam:

| Entidade ausente | Evidência | Impacto |
| :-- | :-- | :-- |
| **Unidade** | Página 1 inteira do relatório (11 unidades, equipes ESF/ESB/EMULT/EMAP/EAPP/EMAD, população); todo o áudio 1 | Sem ela não há consumo por unidade, nem cronograma, nem rateio |
| **Solicitação / Pedido** com `SOLICITADO` × `ATENDIDO` | Páginas 1 e 2 do relatório | É **o fato operacional central**; hoje não existe no RFC |
| **PosiçãoDeEstoque** (saldo físico, consumo mensal, cobertura) | Página 4 (`CONSUMO MÊS`, `DIAS EST`, `STATUS EST`) | Base de toda decisão de compra |
| **ProcessoLicitatório** com 9 etapas | Página 3 inteira; explicação longa no áudio 1 | O RFC só tem `processo_sei` como VARCHAR na NE |
| **GrupoMaterial / SubgrupoMaterial** | "além dos grupos, tem subgrupos… só odontologia tem mais de 400 referências" | RFC tem `categoria` como campo simples |
| **ClassificaçãoABC** (A/B/C/D/S) | `EST. CLASSIF` na página 4 | Ausente |
| **AçãoEmAndamento** sobre item em falta | Áudio 1: empenho / verificação de empréstimo / permuta com outras entidades / nenhuma | É a diferença entre "fotografia" e ação |

---

### P1 — Requisitos funcionais ausentes

1. **Gatilho de compra por cobertura.** Regra explícita: cobertura = estoque ÷ consumo;
   **abaixo de 3 meses dispara a compra**. Exemplo dado: luva com 10 semanas = 2,5 meses
   → comprar. Contra-exemplo: 9,5 meses → não comprar. E o gatilho é **condicionado**:
   ATA dentro da vigência? tem saldo? quanto falta para vencer? *"se ela vai vencer, não
   adianta eu esperar 2 meses para comprar"*. Depende ainda da **próxima ATA**, que
   depende do sucesso do processo licitatório.
2. **Estoque mínimo derivado do consumo** — "média [dos 3 meses] × 2 ou × 3",
   configurável. Contradiz RF03 ("apenas para alertas de processo").
3. **Painel de itens em falta**, atualizado **diariamente**, filtrável por grupo, com a
   **ação em andamento** de cada item. Hoje: 465 itens em falta = 32% do catálogo.
4. **Página 360° do item** — *o pedido mais enfatizado da reunião*: "situação atual,
   histórico de consumo, unidade que mais consumiu, status/data do item, próximo
   processo licitatório… **eu quero saber tudo daquele cara**"; "o que posso comprar hoje
   que já está disponível, previsão de demanda, saldo para compra, se é item renovável".
   **O RFC não tem tela de detalhe de item.**
5. **Cronograma de entrega por unidade** — janelas de solicitação e recebimento
   (1ª solicitação até dia 24 → recebe dia 2; 2ª até dia 8 → recebe dia 16), usado para
   distribuir a carga entre unidades.
6. **Portal de formulários** — glicosímetros, incubadoras, problema com fornecedor,
   **divergência de entrega** (a Abranet confere o pedido e reporta falta/sobra/lote
   errado), **devolução/redistribuição** de item próximo do vencimento.
7. **Histórico de atendimento de 12 meses por item e por unidade**, usado para
   **dimensionar a próxima licitação** ("pega o histórico, mais 20%").
8. **Faixas de cobertura com drill-down**: `<3, 3–6, 6–9, 9–12, >12 meses`, `por demanda`,
   `sem giro`; em **valor** e em **nº de itens**; clicar na barra abre a lista.
   Regra de negócio: **sem giro = 6 meses sem saída**.
9. **Taxa de atendimento (SOLICITADO × ATENDIDO)** — manchete de 2 das 4 páginas do
   relatório e **completamente ausente do RFC**.

---

### P2 — Inconsistências internas do próprio RFC

1. **§6.1 (A10 SSRF) e §6.3** ainda falam em "**chaves de API (DOMS, e-Pública)**" e
   allowlist de URLs, mas RF07/RF08 foram reescritos para "**não há integração
   automática via API**". Resíduo da v1.5 — remover.
2. **Persona 3** mistura duas pessoas: *"Ana, Auditora Interna (**Ana Carolina Souza —
   Gestora de Insumos**)"*. Além disso as personas são fictícias (Mariana/Carlos/Ana)
   enquanto os stakeholders reais e nomeados são **Anderson** (gerente) e **Eduardo**
   (que construiu a solução atual em Google Sites/Sheets e atua como comprador-gestor).
3. **§7.2 Cronograma**: "Não há cronograma de desenvolvimento" — mas §7.1 define 5 marcos
   em 16 semanas. Contradição literal.
4. **Números dos mockups são fictícios** e destoam da realidade agora conhecida:

   | RFC (mockup) | Realidade (relatório/áudio) |
   | :-- | :-- |
   | 48 ATAs ativas | 7 ATAs, 4 vigentes (Tela 4 do próprio RFC já diverge do card) |
   | 9 itens cadastrados | **~1.400 itens** no catálogo |
   | R$ 11.490.000 contratado | ~**R$ 19 mi** atendidos no período; ~**R$ 7 mi** em estoque |
   | — | **465 itens em falta (32%)**; **143 sem giro** (R$ 83 mil); **258 itens** com >1 ano de cobertura |
   | KPI "≥ 5 usuários ativos" | 11+ unidades, cada uma com gestor → meta subdimensionada |

5. **§2.6 Fora do Escopo** não registra dois itens que os **próprios stakeholders**
   excluíram: **controle de fórmulas e suplementos** (150–200 casos administrativos/
   judiciais — *"a gente não vai colocar agora dentro do sistema"*) e **gestão de pessoas
   / programação de férias**.

---

## 4. Decisões registradas

| # | Decisão | Data | Origem |
| :-- | :-- | :-- | :-- |
| D1 | **O teto do aditivo da ATA é 25%.** | 01/09/2026 | Isaac (autor do RFC) |

**Contexto de D1.** As duas transcrições divergem: o áudio de `21.39.27` diz *"o máximo do
aditivo, que é 25%"* e o de `21.39.59` diz *"pode pedir um aditivo de até 30%"*. Pelo
horário dos arquivos, `21.39.27` precede `21.39.59` — adotou-se a **primeira menção: 25%**.

Registrar em: nova regra de negócio na §2.5 (teto de aditivo sobre o valor da ATA) e no
campo "percentual do aditivo" da tela **ATAs a renovar** (§4.2), que hoje não tem o limite
documentado. A menção a 30% fica registrada aqui apenas como rastro — se um stakeholder
levantar o número, esta é a origem.

---

## 5. Divergências a confirmar com os stakeholders

| # | Questão | Evidência conflitante |
| :-- | :-- | :-- |
| 1 | O `Estoque` do SIGI é **saldo de ATA** (v1.6) ou **estoque físico**? | Todo o §3 desta análise. Decisão estruturante. |
| 2 | O SIGI **substitui** o painel CAME ou coexiste com ele? | O relatório é Looker Studio sobre Sheets; a reunião cogita "colocar no Data Studio" a partir do CSV do SIGI. |
| 3 | Qual o sistema de origem de cada dado — **DOMS**, **República**, **e-Publica**? | A reunião separa: estoque = DOMS/Abranet; ATA = República. O RFC atribui ATA ao e-Publica. |
| 4 | "Sincatarina" (citado no áudio 2 como opção de compra) é uma fonte a integrar? | Mencionado uma vez, não está no RFC. |

---

## 6. Lista de alterações proposta para a v1.7

**Estruturais**
- [ ] Reposicionar `Estoque` como capacidade de primeira classe (reverter a demoção da v1.6): RF03, RF14, §1.3, §4.1.
- [ ] Adicionar entidades: `Unidade`, `Solicitacao`/`ItemSolicitacao`, `PosicaoEstoque`, `ProcessoLicitatorio`/`EtapaProcesso`, `GrupoMaterial`/`Subgrupo`, `AcaoEmAndamento`.
- [ ] Novo RF: gatilho de compra por cobertura < 3 meses, condicionado a vigência e saldo da ATA.
- [ ] Novo RF: estoque mínimo = média de consumo (3 meses) × fator configurável.
- [ ] Novo RF: taxa de atendimento (solicitado × atendido) por item, unidade e mês.
- [ ] Nova tela: **detalhe 360° do insumo**.
- [ ] Nova tela: **itens em falta por grupo**, com ação em andamento, atualização diária.
- [ ] Nova tela: **acompanhamento de processos licitatórios** (planejado × real, 9 etapas).
- [ ] Novo módulo (pós-MVP): **lista de tarefas do comprador** por grupo de materiais.

**Correções**
- [ ] RF01/UC01/§6.2/Tela 1: Gov.br → **Entra ID / SSO institucional**.
- [ ] §2.2: adicionar coluna **Ator**; redesenhar o diagrama de casos de uso.
- [ ] §6.2: adicionar perfis **comprador** e **gestor de unidade**.
- [ ] RF09: notificação seletiva/agregada, não por mudança de status.
- [ ] UC03/RF04/Tela 4: importação e-Publica → hipótese a validar; CSV como caminho primário; registrar **República**.
- [ ] §6.1 A10 e §6.3: remover referências a chaves de API DOMS/e-Publica.
- [ ] §2.1: corrigir a Persona 3; ancorar personas nos papéis reais.
- [ ] §7.2: resolver a contradição do cronograma.
- [ ] Telas 2–8: substituir números fictícios por ordens de grandeza reais.
- [ ] §2.6: incluir fórmulas/suplementos e gestão de pessoas como fora de escopo.
- [x] Teto do aditivo definido em **25%** (D1) — falta escrever a RN em §2.5 e o limite na tela ATAs a renovar.

---

## 7. O que o RFC v1.6 já acerta

Para não perder o que está bom:

- O **fluxo de 5 etapas da NE** (Demanda → Validação de Saldo → Pré-empenho → Envio ao
  Fornecedor → NE emitida) não foi contestado em nenhum momento.
- A decisão da v1.6 de **abandonar a integração automática via API** com DOMS/e-Publica
  em favor de validação de formato está **correta** e alinhada à realidade descrita
  (alimentação por CSV/planilha).
- **RN02** (NF vincula-se à NE, não à ATA) está correta e é coerente com o domínio.
- **Histórico auditável imutável** é requisito real e foi reforçado pelos stakeholders.
- A preocupação de Isaac com **formatação/tamanho de campo no CSV** (32 vs 16/64
  caracteres) é legítima e deve virar requisito explícito de validação de importação.
