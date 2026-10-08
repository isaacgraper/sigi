# RFC — SIGI

**Sistema Integrado de Gestão de Insumos**
Plataforma de Cobertura de Estoque e Rastreabilidade do Ciclo Administrativo

|  |  |
| :-- | :-- |
| Projeto | Meus Insumos |
| Tipo | Sistema Web |
| Versão do RFC | **1.7** |
| Status | Revisão 1.7 — incorpora a reunião de stakeholders de 17/08/2026 |
| Stack | Python · FastAPI (backend) \| Next.js (frontend) |
| Entidade-alvo | Entidade governamental estadual |
| Público-alvo | Servidores públicos internos |
| Data | 01/09/2026 |
| Autor | Isaac Kleimmann Graper |
| Linha de Projeto | Web / Plataforma |

> **Sobre esta versão.** A v1.7 revisa a v1.6 a partir de duas fontes novas: a reunião
> com Anderson e Eduardo em 17/08/2026 e o *Relatório Geral CAME*, o painel que o setor
> opera hoje. A mudança estrutural é o **reposicionamento do estoque como capacidade de
> primeira classe** — a v1.6 o havia rebaixado a "dado derivado", e as evidências da
> reunião apontam na direção oposta. O detalhamento dos achados está em
> [`analise-lacunas-rfc-v1.6.md`](./analise-lacunas-rfc-v1.6.md).
>
> Ver o [Changelog v1.6 → v1.7](#10-changelog-v16--v17) ao final.

---

# 1. Visão do Produto e Impacto

## 1.1 Contexto e Problema

Entidades governamentais estaduais conduzem diariamente processos administrativos
complexos de aquisição e fornecimento de insumos. Esse ciclo envolve múltiplos atores —
gestores, compradores, fornecedores e as unidades atendidas — além de documentos fiscais,
ATAs de Registro de Preços e plataformas institucionais de terceiros.

O controle é hoje fragmentado entre planilhas (o "Controle CAME"), e-mails e sistemas
legados. O setor mantém um painel próprio, construído em Google Sites e Google Sheets,
que já cobre boa parte da necessidade — mas depende de manutenção manual, não tem
histórico auditável e não é acessível às unidades.

Os problemas concretos são:

- **A decisão de compra é reativa.** Não há gatilho automático: a falta é percebida
  quando o item já acabou, não quando a cobertura projetada cai abaixo do limite.
- **As unidades não enxergam o estoque central.** Elas emitem solicitações sem saber o
  que existe, gerando pedidos impossíveis de atender e retrabalho de triagem.
- **Falta rastreabilidade do ciclo completo**, da abertura do processo licitatório até a
  conclusão do fornecimento.
- **Não há histórico consolidado e auditável** para prestação de contas.
- **Registro manual e redundante** de Notas de Empenho e Notas Fiscais em múltiplos
  sistemas.
- **Ausência de consistência de nomenclatura** entre as plataformas já utilizadas
  (DOMS, República, e-Publica).
- **Impossibilidade de antecipar vencimentos de ATA** e de saber se a ATA vigente cobre
  o consumo até a próxima.

## 1.2 Origem da Demanda e Evidências

**Demanda externa.** O projeto nasce de uma necessidade identificada junto ao PROCON/CAC,
em Santa Catarina. O responsável é **Anderson Viebranz**, Gerente de Insumos, Materiais e
Medicamentos.

**Interlocutores.** Duas pessoas conduzem a validação do produto:

| Interlocutor | Papel | Contribuição |
| :-- | :-- | :-- |
| **Anderson** | Gerente do setor | Define prioridade, regras de negócio e o recorte do que entra no sistema |
| **Eduardo** | Gestor e comprador | Construiu a solução atual em Google Sites/Sheets; é a fonte das regras operacionais e o principal usuário do futuro módulo de compras |

**Evidências de interesse.** Na reunião de 17/08/2026 os stakeholders demonstraram o
painel que operam hoje e validaram, ponto a ponto, o protótipo do SIGI. O pedido mais
enfatizado foi uma **visão completa por insumo** — *"eu quero saber tudo daquele cara"* —
reunindo situação de estoque, histórico de consumo, unidade que mais consome, saldo de
ATA disponível para compra e o próximo processo licitatório.

## 1.3 Análise de Soluções Existentes (Benchmark)

| Solução | Pontos Fortes | Limitações | Público-alvo |
| :-- | :-- | :-- | :-- |
| SIAD | Integrado ao SIAFI; padrão federal | Complexo, não adaptado a estados; UX defasada | Órgãos federais |
| SIGMAT | Controle de almoxarifado; relatórios | Sem rastreamento de ciclo ATA até conclusão | Prefeituras e estados |
| Planilhas Excel/Sheets | Flexibilidade; custo zero | Sem histórico auditável; erro humano elevado | Amplo uso atual |
| ERP Totvs Protheus | Módulo completo de estoque | Alto custo; não adaptado ao contexto público | Grandes empresas |
| Comprasnet / PNCP | Compras governamentais padronizadas | Foco em licitação, não em rastreamento pós-ATA | Órgãos públicos |
| **Painel CAME (atual)** | **Já modela cobertura, faixas de estoque e andamento de processos; feito sob medida** | **Manutenção manual; sem histórico auditável; inacessível às unidades; depende de uma pessoa** | **O próprio setor** |

### Diferencial do Projeto

O SIGI preenche uma lacuna específica: nenhuma das soluções existentes une **cobertura de
estoque orientada à decisão de compra** com **rastreabilidade auditável do ciclo
administrativo** — do processo licitatório à conclusão do fornecimento — adaptada ao
contexto da entidade estadual.

O projeto se diferencia por:

- **Cobertura de estoque como núcleo do produto**: estoque, consumo mensal e cobertura
  projetada por item, com gatilho automático de compra
- **Fluxo estruturado de Notas de Empenho** (Demanda → Validação de Saldo → Pré-empenho →
  Envio ao Fornecedor → NE emitida)
- **Acompanhamento do processo licitatório** com planejado × real por etapa
- **Consistência operacional** com DOMS, República e e-Publica por validação de formato e
  importação de CSV
- **Histórico consolidado e imutável** por processo, para prestação de contas
- **Visibilidade para as unidades** do que está em falta, hoje inexistente
- Interface voltada a servidores, sem necessidade de treinamento técnico avançado

## 1.4 Público-Alvo

| Perfil | Responsabilidade |
| :-- | :-- |
| **Gestor de Insumos** | Emissão, aprovação e encerramento de ATAs e NEs; acesso completo |
| **Comprador** | Opera a lista de compras do seu grupo de materiais; abre e acompanha processos |
| **Servidor de Recebimento** | Registra Notas Fiscais e avança etapas no ciclo |
| **Gestor de Unidade** | Emite solicitações dentro das janelas do cronograma; consulta itens em falta |
| **Controle Interno / Auditoria** | Consulta o histórico auditável e gera relatórios de prestação de contas |

Perfil esperado: usuários com conhecimento básico de informática, acostumados com
planilhas e sistemas web corporativos.

## 1.5 Objetivos do Projeto

**Objetivo geral.** Substituir o controle fragmentado por uma plataforma web que (a)
antecipe a decisão de compra a partir da cobertura de estoque e (b) mantenha o histórico
auditável do ciclo administrativo completo.

**Objetivos específicos:**

- Calcular e monitorar a **cobertura de estoque** por insumo, disparando a demanda de
  compra antes da ruptura
- Dar às unidades **visibilidade dos itens em falta**, atualizada diariamente
- Rastrear em tempo real o ciclo: Processo Licitatório → ATA → NE → NF → conclusão
- Consolidar a **visão 360° por insumo**, reunindo estoque, consumo, ATA e processo
- Medir a **taxa de atendimento** (solicitado × atendido) por item, unidade e período
- Estruturar o fluxo de Notas de Empenho com etapas de validação e aprovação
- Gerar histórico auditável e imutável para prestação de contas
- Garantir consistência de nomenclatura com DOMS, República e e-Publica
- Notificar de forma **seletiva** os responsáveis por itens que entram em criticidade
- Centralizar o cadastro e o gerenciamento de usuários da entidade

## 1.6 Métricas de Sucesso (KPIs)

Substituem as metas genéricas da v1.6 por indicadores ancorados na operação real.

| Métrica | Linha de base (ago/2026) | Meta | Como medir |
| :-- | :-- | :-- | :-- |
| Itens em falta | 465 itens (32% do catálogo) | Redução de 30% em 12 meses | Painel de itens em falta |
| Itens sem giro | 143 itens · R$ 83 mil | Redução de 50% em 12 meses | Faixa "sem giro" |
| Itens com cobertura > 12 meses | 258 itens | Redução de 40% em 12 meses | Faixas de cobertura |
| Rupturas com ATA vigente e saldo | não medido hoje | ≤ 5% das faltas | Cruzamento falta × saldo de ATA |
| Taxa de atendimento | ~94% (média do período) | ≥ 97% | Solicitado × atendido |
| Antecedência da demanda de compra | reativa | ≥ 60 dias antes da ruptura | Data do gatilho × data da ruptura projetada |
| Tempo de registro de NE/NF | processo manual | Redução ≥ 50% | Comparação com fluxo atual |
| Tempo de resposta da API | — | < 300 ms (p95) | Monitoramento via APM |
| Disponibilidade | — | ≥ 99,5% mensal | Uptime monitoring |
| Adoção | — | 11 unidades + 100% dos compradores | Logs de acesso |

> As linhas de base vêm do Relatório Geral CAME e da reunião. Números de estoque
> (~R$ 7 mi) e catálogo (~1.400 itens) devem ser reconfirmados na carga inicial.

---

# 2. Engenharia de Requisitos

## 2.1 Personas

**Persona 1 — Eduardo, Gestor e Comprador.** Construiu e mantém o painel atual em Google
Sheets. Conhece as regras de cobertura de cor e é quem decide o que comprar e quando. Sua
dor é que todo o controle depende dele e da manutenção manual das planilhas. Precisa de
uma lista de compras que se atualize sozinha e de uma visão completa por item.

**Persona 2 — Anderson, Gerente do Setor.** Responde pela área e pela prestação de contas.
Precisa saber, semanalmente, se o estoque melhorou ou piorou — *"entraram 10 e saíram 10,
estamos no zero a zero"* — e responder a auditorias sem consolidar planilhas à mão.

**Persona 3 — Servidor de Recebimento.** Registra o recebimento de Notas Fiscais e avança
etapas do fluxo de NE. Tem dificuldade com sistemas complexos e prefere interfaces
diretas. Comete erros de digitação ao transcrever dados entre sistemas.

**Persona 4 — Gestor de Unidade.** Emite as solicitações da sua unidade dentro das janelas
do cronograma. Hoje não tem visibilidade do estoque central e pede itens indisponíveis.

**Persona 5 — Auditor Interno.** Realiza auditorias sobre a aplicação de recursos
públicos. Precisa de histórico detalhado e imutável, com rastreabilidade do ciclo
completo, e de exportações para prestação de contas.

## 2.2 Casos de Uso Principais

| ID | Descrição | Ator principal |
| :-- | :-- | :-- |
| UC01 | Autenticar no sistema via SSO institucional (Entra ID) | Todos |
| UC02 | Gerenciar usuários, perfis e permissões | Gestor |
| UC03 | Cadastrar insumo manualmente ou importar catálogo CSV do DOMS | Comprador, Gestor |
| UC04 | Registrar ATA de Registro de Preços e importar seus itens por CSV | Gestor |
| UC05 | Consultar a **visão 360° de um insumo** | Todos |
| UC06 | Consultar e filtrar **itens em falta** por grupo | Todos |
| UC07 | Registrar a **ação em andamento** sobre um item em falta | Comprador |
| UC08 | Receber e operar a **lista de compras** do seu grupo de materiais | Comprador |
| UC09 | Abrir solicitação de Nota de Empenho vinculada a ATA e insumo | Gestor, Comprador |
| UC10 | Avançar etapa no fluxo de NE | Gestor, Comprador |
| UC11 | Reverter etapa no fluxo de NE mediante justificativa | Gestor |
| UC12 | Registrar Nota Fiscal vinculada a uma NE emitida | Servidor de Recebimento |
| UC13 | Emitir solicitação da unidade dentro da janela do cronograma | Gestor de Unidade |
| UC14 | Acompanhar o andamento dos processos licitatórios (planejado × real) | Gestor, Comprador |
| UC15 | Consultar taxa de atendimento por item, unidade e período | Gestor, Auditor |
| UC16 | Consultar o histórico auditável de movimentações | Auditor, Gestor |
| UC17 | Gerar e exportar relatórios de prestação de contas (PDF/CSV) | Auditor, Gestor |
| UC18 | Renovar ATA registrando aditivo e reajuste | Gestor |

> **Correção da v1.6.** A tabela de casos de uso não tinha coluna de ator, e o diagrama
> apresentado na reunião fazia gestor e servidor executarem os mesmos casos. O diagrama
> deve ser redesenhado a partir desta tabela.

## 2.3 Requisitos Funcionais

### Acesso e cadastro

| ID | Requisito |
| :-- | :-- |
| RF01 | O sistema deve autenticar o servidor via **SSO institucional (Microsoft Entra ID)**, reaproveitando a matrícula e a credencial já provisionadas pela TI da entidade. Autenticação local por e-mail e senha existe apenas como contingência. |
| RF02 | O sistema deve permitir que o gestor cadastre e gerencie usuários, atribuindo perfil e escopo de acesso por grupo de materiais e por unidade. |
| RF03 | O sistema deve permitir o cadastro de insumos com: código (compatível com DOMS), nome, descrição, **grupo e subgrupo**, unidade de medida, classificação de estoque (A/B/C/D/S) e parâmetros de reposição. Cadastro manual ou importação CSV. |

### Cobertura de estoque e compra *(novo na v1.7)*

| ID | Requisito |
| :-- | :-- |
| RF04 | O sistema deve manter, por insumo, a **posição de estoque**: saldo atual, consumo médio mensal e **cobertura projetada** em meses (saldo ÷ consumo médio). |
| RF05 | O sistema deve calcular o **estoque mínimo** de cada insumo como a média de consumo dos últimos 3 meses multiplicada por um **fator configurável** (padrão: 3), permitindo sobrescrita manual por item. |
| RF06 | O sistema deve classificar cada insumo em faixas de cobertura: `< 3 meses`, `3–6`, `6–9`, `9–12`, `> 12 meses`, `por demanda` e `sem giro`, exibindo o total **em número de itens e em valor**, com drill-down para a lista de itens da faixa. |
| RF07 | O sistema deve **disparar automaticamente uma demanda de compra** quando a cobertura de um insumo cair abaixo do limite configurado (padrão: 3 meses), registrando data e gatilho. |
| RF08 | Ao disparar a demanda, o sistema deve avaliar e exibir: se existe **ATA vigente** para o item, se ela tem **saldo**, **quantos dias faltam para o vencimento** da ATA e a **previsão da próxima ATA** derivada do processo licitatório em andamento. |
| RF09 | O sistema deve manter o **painel de itens em falta**, atualizado diariamente, filtrável por grupo e subgrupo, exibindo para cada item a **ação em andamento**: empenho emitido, verificação de empréstimo, permuta com outra entidade, processo licitatório aberto, ou nenhuma. |
| RF10 | O sistema deve apresentar a **visão 360° do insumo** em tela única, reunindo: situação de estoque e cobertura, histórico de consumo dos últimos 12 meses, unidades que mais consumiram, ATA vinculada e saldo disponível para compra, NEs e NFs relacionadas, e o próximo processo licitatório. |
| RF11 | O sistema deve calcular a **taxa de atendimento** (solicitado × atendido) por insumo, unidade e período. |
| RF12 | O sistema deve apresentar o **delta semanal da lista crítica**: itens que entraram e que saíram da criticidade na semana, e o saldo líquido. |

### ATAs, empenhos e notas

| ID | Requisito |
| :-- | :-- |
| RF13 | O sistema deve permitir o registro manual de ATA de Registro de Preços e a **importação dos seus itens via CSV**. |
| RF14 | O sistema deve exibir, por ATA: valor contratado, valor empenhado, saldo remanescente, vigência e **por quanto tempo o saldo cobre o consumo atual** (cobertura da ATA em dias). |
| RF15 | O sistema deve sinalizar **ATAs a renovar** — vigência encerrando em até 90 dias — permitindo registrar aditivo e reajuste, respeitando o teto de aditivo definido em RN10. |
| RF16 | O sistema deve gerenciar o fluxo de Notas de Empenho em cinco etapas sequenciais: Demanda → Validação de Saldo → Pré-empenho → Envio ao Fornecedor → NE emitida, com indicadores de emitidas, em andamento e total. |
| RF17 | O sistema deve permitir o registro de Notas Fiscais vinculadas a uma **Nota de Empenho** (não diretamente à ATA); a NF herda o vínculo com a ATA através da NE. |
| RF18 | O sistema deve validar campos obrigatórios no cadastro de insumos, ATAs, NEs e NFs. |

### Processo licitatório *(novo na v1.7)*

| ID | Requisito |
| :-- | :-- |
| RF19 | O sistema deve registrar processos licitatórios com seus itens, número do processo, data de abertura e status, acompanhando as etapas: Comunicado → ACP → SAP → PGM → LCT → Publicação do Edital → Pregão → Propostas → Homologação. |
| RF20 | O sistema deve comparar **planejado × real** em dias por etapa e projetar a data de homologação. |
| RF21 | O sistema deve indicar, por insumo, o **tempo sem processo vigente** e a previsão de abertura do próximo. |
| RF22 | O sistema deve apoiar o dimensionamento do próximo processo a partir do **histórico de consumo de 12 meses**, com acréscimo percentual configurável (padrão: 20%). |

### Unidades, formulários e notificação

| ID | Requisito |
| :-- | :-- |
| RF23 | O sistema deve manter o **cronograma de solicitação e recebimento por unidade**, com as janelas de pedido e as datas de entrega correspondentes. |
| RF24 | O sistema deve permitir que a unidade emita solicitações dentro da sua janela e consulte os itens em falta antes de pedir. |
| RF25 | O sistema deve disponibilizar **formulários** de: solicitação de equipamento (glicosímetro, incubadora), problema com fornecedor, **divergência de entrega** (falta, sobra, lote incorreto) e **devolução/redistribuição** de item próximo do vencimento. |
| RF26 | O sistema deve notificar de forma **seletiva e agregada** — digest por comprador e por grupo de materiais — apenas eventos de criticidade configurados. Não deve enviar e-mail a cada mudança de status. |
| RF27 | O sistema deve gerar histórico auditável imutável de todas as movimentações de insumos, ATAs, NEs, NFs e processos. |
| RF28 | O sistema deve permitir exportação em PDF/CSV de: ciclo de vida do insumo, execução orçamentária por ATA, posição de cobertura, taxa de atendimento e indicadores de fornecedores. |

### Consistência com sistemas externos

| ID | Requisito |
| :-- | :-- |
| RF29 | O sistema deve validar o **formato** dos códigos de insumo (padrão DOMS) e dos números de processo, orientando o preenchimento. **Não há integração automática via API.** |
| RF30 | A importação CSV deve validar tipo, tamanho e formato de cada coluna antes de persistir, rejeitando o arquivo com relatório de erro por linha e coluna em vez de gravar dados truncados. |

> **RF30** responde à preocupação levantada na reunião sobre divergência de tamanho de
> campo entre a origem e o banco (32 vs. 16/64 caracteres).

## 2.4 Requisitos Não Funcionais

| ID | Requisito |
| :-- | :-- |
| RNF01 | Tempo de resposta das APIs inferior a 300 ms no percentil 95 |
| RNF02 | Disponibilidade de 99,5% mensal, exceto janelas de manutenção programada |
| RNF03 | Autenticação via OAuth2/OIDC contra o Entra ID, com tokens de curta duração (15 min) e refresh token seguro |
| RNF04 | Dados em trânsito criptografados via HTTPS/TLS 1.2+ |
| RNF05 | Suporte a no mínimo 50 usuários simultâneos no MVP |
| RNF06 | Interface responsiva em navegadores modernos (Chrome, Firefox, Edge) |
| RNF07 | Conformidade com a LGPD para dados pessoais de servidores |
| RNF08 | Logs de auditoria imutáveis, retidos por no mínimo 5 anos |
| RNF09 | Containerização via Docker |
| RNF10 | Cobertura mínima de 70% de testes automatizados |
| RNF11 | O recálculo diário de cobertura de todo o catálogo (~1.400 itens) deve concluir em até 10 minutos |

## 2.5 Regras de Negócio

| ID | Regra de Negócio |
| :-- | :-- |
| RN01 | Apenas usuários autenticados e com perfil ativo podem acessar o sistema |
| RN02 | Uma Nota Fiscal só pode ser vinculada a uma NE com status "NE emitida"; o vínculo com a ATA é herdado através da NE |
| RN03 | O status de uma NE só avança no fluxo; a reversão exige justificativa registrada e perfil de gestor |
| RN04 | Apenas gestores podem emitir e encerrar ATAs |
| RN05 | Todo registro de Nota Fiscal deve incluir número, data de emissão, valor e fornecedor |
| RN06 | Alterações em registros auditáveis preservam o histórico original (imutabilidade) |
| RN07 | O acesso é restrito por perfil, grupo de materiais e unidade de competência (RBAC) |
| RN08 | O fluxo de NE é sequencial e obrigatório; etapas não podem ser puladas |
| RN09 | Uma NE deve informar Processo SEI, ATA vinculada, insumo, quantidade e valor estimado antes de ser aberta |
| **RN10** | **O aditivo de uma ATA está limitado a 25% do valor contratado** *(decisão D1, 01/09/2026)* |
| **RN11** | **A cobertura de um insumo é `saldo em estoque ÷ consumo médio mensal`. Cobertura abaixo de 3 meses (configurável) dispara demanda de compra.** |
| **RN12** | **Um insumo é considerado "sem giro" após 6 meses sem nenhuma saída.** |
| **RN13** | **A demanda de compra não é emitida sem antes verificar a vigência e o saldo da ATA. Se a ATA vence antes do consumo da quantidade a comprar, a quantidade é limitada ao consumo projetado até o vencimento.** |
| **RN14** | **O saldo da ATA é validado antes do pré-empenho; NEs que ultrapassem o saldo disponível são bloqueadas.** |
| **RN15** | **Uma unidade só pode emitir solicitação dentro da sua janela do cronograma vigente.** |

> **Sobre RN10.** As transcrições divergem: o áudio de `21.39.27` diz 25% e o de
> `21.39.59` diz 30%. Pelo horário dos arquivos, `21.39.27` precede `21.39.59`; adotou-se
> a primeira menção. A menção a 30% fica registrada aqui como rastro da origem.

## 2.6 Fora do Escopo

- Módulo financeiro ou contábil
- Integração com sistemas de folha de pagamento
- Predição de demanda com Machine Learning *(pós-MVP)*
- Aplicativo mobile nativo
- Integração automática via API com qualquer sistema externo
- Portal público de transparência
- **Controle de fórmulas e suplementos** — 150 a 200 casos de solicitação administrativa
  ou judicial, mantidos em controle paralelo por decisão dos stakeholders
- **Gestão de pessoas** — programação de férias e escalas do setor

---

# 3. Fluxos e Comportamento do Sistema

## 3.1 Fluxo da decisão de compra *(fluxo principal, novo na v1.7)*

1. O sistema recalcula diariamente a cobertura de cada insumo: `saldo ÷ consumo médio mensal`
2. A cobertura de um item cai abaixo do limite configurado (padrão: 3 meses)
3. O sistema gera uma **demanda de compra** e a coloca na lista do comprador responsável
   pelo grupo de materiais do item
4. O sistema anexa à demanda: existe ATA vigente? tem saldo? quantos dias até o
   vencimento? qual a previsão da próxima ATA?
5. O comprador consulta a **visão 360°** do item e decide a quantidade, limitada pelo
   consumo projetado até o vencimento da ATA (RN13)
6. Havendo ATA com saldo, o comprador abre a **NE** e o fluxo de cinco etapas se inicia
7. Não havendo ATA vigente, o item é vinculado a um **processo licitatório** — existente
   ou a abrir — e passa a constar no painel de itens em falta com a ação em andamento
8. A NE emitida gera o pedido ao fornecedor; a NF é registrada no recebimento
9. O estoque é atualizado, a cobertura recalculada e o item sai da lista crítica

## 3.2 Fluxo do ciclo administrativo

1. Servidor autentica via SSO institucional
2. Gestor registra a ATA e importa seus itens por CSV
3. Comprador abre a solicitação de NE informando Processo SEI, ATA, insumo, quantidade e
   valor estimado
4. A NE percorre: Demanda → Validação de Saldo (automática) → Pré-empenho → Envio ao
   Fornecedor → NE emitida
5. Servidor de Recebimento registra a NF vinculada à NE emitida
6. O sistema valida a NF, atualiza o estoque e desconta o saldo da ATA
7. Notificação seletiva é enviada aos responsáveis conforme RF26
8. Auditor consulta o histórico e exporta os relatórios
9. Gestor encerra a ATA após a conclusão do fornecimento

## 3.3 Fluxo da solicitação da unidade

1. O gestor da unidade consulta o painel de **itens em falta** antes de pedir
2. Dentro da sua janela do cronograma, emite a solicitação
3. O setor central atende total ou parcialmente; a diferença alimenta a **taxa de
   atendimento**
4. Divergências no recebimento (falta, sobra, lote incorreto) são registradas pelo
   formulário de divergência e direcionadas ao fornecedor responsável

## 3.4 Fluxos Alternativos

**NE com saldo insuficiente na ATA.** Na etapa de Validação de Saldo, o sistema bloqueia a
NE e orienta o ajuste do valor ou a solicitação de aditivo, respeitando RN10.

**ATA vencendo antes do consumo.** Se a quantidade solicitada não é consumível até o
vencimento da ATA, o sistema propõe a quantidade máxima aproveitável e sinaliza a
dependência do próximo processo licitatório.

**Item em falta sem ATA e sem processo.** O item permanece no painel de faltas com ação
"nenhuma" e é priorizado na abertura do próximo processo.

**Nota Fiscal com dados inválidos.** Mensagem de erro específica por campo, com bloqueio
do envio até a correção.

**Importação CSV malformada.** O arquivo é rejeitado por inteiro com relatório de erro por
linha e coluna; nada é persistido parcialmente (RF30).

**Usuário sem permissão.** HTTP 403 com mensagem amigável e registro no log de auditoria.

**Reversão de etapa da NE.** Exige justificativa registrada e perfil de gestor; a reversão
fica no histórico auditável.

---

# 4. Mockups e Experiência do Usuário (UX)

## 4.1 Fluxo de Navegação

| Módulo | Descrição |
| :-- | :-- |
| **Dashboard** | Situação da cobertura: itens em falta por grupo, delta semanal da lista crítica, itens que entraram na semana, ATAs em saldo crítico |
| **Insumos** | Catálogo com grupo/subgrupo, classificação e cobertura; acesso à **visão 360°** de cada item |
| **Cobertura** | Faixas de cobertura em itens e em valor, com drill-down; itens sem giro |
| **Faltas** | Itens em falta por grupo, com a ação em andamento de cada um |
| **Compras** | Lista de demandas de compra por comprador e grupo de materiais |
| **ATAs** | Cadastro, importação de itens, vigência, saldo, cobertura em dias, aditivo e renovação |
| **Notas de Empenho** | Fluxo de cinco etapas com indicadores |
| **Notas Fiscais** | Registro e conferência de NFs vinculadas a NEs; pendências por fornecedor |
| **Processos** | Andamento dos processos licitatórios, planejado × real |
| **Unidades** | Cadastro, cronograma de solicitação e recebimento, consumo por unidade |
| **Relatórios** | Indicadores e exportações |

> **Correção da v1.6.** O dashboard da v1.6 trazia "ATAs ativas", "Insumos pendentes" e
> "NFs lançadas hoje". Os stakeholders rejeitaram esses KPIs — *"não é o que a gente quer
> ver"*, e sobre NF, *"isso não importa"*. O dashboard passa a ser orientado à cobertura.

## 4.2 Telas

**Tela 1 — Login.** Entrada única por **SSO institucional (Entra ID)**, com identidade
visual da entidade e selos de conformidade. Acesso local por e-mail e senha apenas como
contingência.

**Tela 2 — Dashboard.** Quatro indicadores no topo: *Itens em falta* (nº e % do catálogo),
*Delta da lista crítica na semana* (entraram / saíram / líquido), *Itens em compra*
(demandas abertas) e *ATAs em saldo crítico*. Abaixo, o gráfico de itens em falta por
grupo e a lista dos itens que entraram na criticidade nesta semana.

**Tela 3 — Insumos.** Tabela com código, nome, grupo/subgrupo, classificação (A/B/C/D/S),
saldo, consumo mensal, cobertura em meses e status. Filtros por grupo, faixa de cobertura
e status. Ações: cadastrar insumo, importar CSV do DOMS.

**Tela 4 — Visão 360° do Insumo** *(nova)*. Tela única por item, em quatro blocos:
- **Situação**: saldo, consumo médio, cobertura, estoque mínimo, classificação, status
- **Consumo**: série de 12 meses e ranking das unidades que mais consumiram
- **Suprimento**: ATA vinculada, vigência, saldo disponível para compra, NEs e NFs
- **Processo**: processo licitatório vigente ou previsto, etapa atual, previsão de
  homologação, tempo sem processo vigente

**Tela 5 — Cobertura.** Barras por faixa (`<3`, `3–6`, `6–9`, `9–12`, `>12`, `por
demanda`, `sem giro`), alternáveis entre **nº de itens** e **valor**. Clicar na faixa abre
a lista de itens correspondente.

**Tela 6 — Itens em Falta.** Lista filtrável por grupo e subgrupo, com coluna de **ação em
andamento** e o tempo em que o item está em falta. Atualização diária.

**Tela 7 — Lista de Compras.** Demandas geradas pelo gatilho de cobertura, segmentadas por
comprador e grupo. Cada linha traz o item, a cobertura atual, a quantidade sugerida, a
situação da ATA e a ação recomendada.

**Tela 8 — ATAs.** Total de ATAs, valor contratado, empenhado e saldo. Banner de *ATAs a
renovar* (vigência ≤ 90 dias). Tabela com número, objeto, fornecedor, vigência, saldo,
**cobertura em dias** e ações de aditivo e reajuste. Cadastro manual + importação CSV dos
itens.

**Tela 9 — Notas de Empenho.** Pipeline das cinco etapas, indicadores de emitidas, em
andamento e total, e a tabela de solicitações com botão de avanço.

**Tela 10 — Notas Fiscais.** Registro e conferência, com pendências por fornecedor.

**Tela 11 — Processos Licitatórios** *(nova)*. Tabela de processos com ano, item, objeto,
status, previsão de abertura e vencimento do vigente. Gráfico planejado × real em dias
sobre as nove etapas.

**Tela 12 — Unidades.** Cadastro, cronograma de janelas de solicitação e recebimento,
consumo e taxa de atendimento por unidade.

**Tela 13 — Relatórios.** Exportações em PDF/CSV e indicadores consolidados.

> Os números exibidos nos mockups da v1.6 eram fictícios e destoavam da operação real
> (48 ATAs vs. 7; 9 itens vs. ~1.400). Os mockups devem ser refeitos com ordens de
> grandeza reais.

## 4.3 Ferramentas

Figma (Hi-Fi) para prototipação e Lucidchart para os diagramas de navegação e casos de uso.

---

# 5. Arquitetura do Sistema

## 5.1 Diagrama C4

**Nível 1 — Contexto.** O SIGI é o sistema central. Interage com:

- Servidores, compradores, gestores de unidade e auditores, via navegador
- **Microsoft Entra ID** — autenticação federada institucional
- **DOMS** — origem do catálogo e da posição de estoque, via exportação CSV
- **República** — origem das ATAs, via exportação CSV *(a confirmar se emite CSV)*
- **e-Publica** — referência de números de processo
- **Servidor SMTP** — envio de notificações agregadas

> Nenhuma dessas integrações é automática via API. Todas se dão por importação de arquivo
> e validação de formato.

**Nível 2 — Containers.**

| Container | Tecnologia | Responsabilidade |
| :-- | :-- | :-- |
| Frontend SPA | Next.js (React) | Interface, SSR e roteamento |
| API Backend | Python · FastAPI | Lógica de negócio e endpoints REST |
| Banco de Dados | PostgreSQL | Persistência e histórico auditável imutável |
| **Job de Cobertura** | **Python · APScheduler ou cron** | **Recálculo diário de cobertura e geração de demandas de compra** |
| Cache | Redis *(opcional MVP+)* | Cache de sessão e consultas frequentes |
| Serviço de E-mail | SMTP / Resend | Notificações agregadas |
| Container Runtime | Docker | Empacotamento e portabilidade |

**Nível 3 — Componentes da API.**

- **Auth Middleware** — valida tokens OIDC do Entra ID e aplica RBAC por perfil, grupo e unidade
- **Controllers** — FastAPI Routers
- **Services** — regras de domínio, incluindo o motor de cobertura e o gatilho de compra
- **Repositories** — SQLAlchemy ORM
- **Import Service** — validação e carga de CSV (DOMS, República), com relatório de erros
- **Notification Service** — composição dos digests por comprador e grupo

## 5.2 Modelo de Dados

Entidades em **negrito** são novas na v1.7.

| Entidade | Atributos principais | Relacionamentos |
| :-- | :-- | :-- |
| Usuario | id, nome, email, perfil ENUM (gestor, comprador, servidor, gestor_unidade, auditor), ativo, criado_em | Vinculado a grupos de materiais e unidades |
| **GrupoMaterial** | id, nome, grupo_pai_id (FK, autorreferência) | Hierarquia grupo → subgrupo; classifica Insumo |
| Insumo | id, codigo (UNIQUE, DOMS), descricao, unidade, grupo_id (FK), classificacao ENUM (A,B,C,D,S), fator_estoque_minimo | Compõe ItemATA; tem PosicaoEstoque |
| **Unidade** | id, nome, tipo, populacao, equipes JSONB (ESF, ESB, EMULT, EMAP, EAPP, EMAD) | Emite Solicitacao; tem JanelaCronograma |
| **JanelaCronograma** | id, unidade_id (FK), ordem_no_mes, dia_limite_pedido, dia_previsto_recebimento | Restringe Solicitacao (RN15) |
| **Solicitacao** | id, unidade_id (FK), janela_id (FK), data, status | Contém ItemSolicitacao |
| **ItemSolicitacao** | id, solicitacao_id (FK), insumo_id (FK), qtd_solicitada, qtd_atendida, valor | Base da taxa de atendimento (RF11) |
| **PosicaoEstoque** | id, insumo_id (FK), saldo, consumo_medio_mensal, cobertura_meses, estoque_minimo, faixa ENUM, atualizado_em | Recalculada diariamente; dispara DemandaCompra |
| **DemandaCompra** | id, insumo_id (FK), gerada_em, cobertura_no_gatilho, qtd_sugerida, comprador_id (FK), status | Origem da NotaEmpenho |
| **AcaoEmAndamento** | id, insumo_id (FK), tipo ENUM (empenho, emprestimo, permuta, processo, nenhuma), descricao, responsavel_id, criada_em | Exibida no painel de faltas (RF09) |
| ATA | id, numero (UNIQUE), objeto, fornecedor_id (FK), data_emissao, data_vigencia_inicio, data_vigencia_fim, valor_total, percentual_aditivo, status ENUM (vigente, vencida, prorrogada, saldo_zero, cancelada), responsavel_id (FK) | Contém ItemATA; referenciada por NEs |
| ItemATA | id, ata_id (FK), insumo_id (FK), quantidade, valor_unitario, saldo_quantidade | Intermediária ATA ↔ Insumo |
| **ProcessoLicitatorio** | id, numero_processo (UNIQUE), ano, objeto, data_abertura, previsao_homologacao, status ENUM | Contém ItemProcesso e EtapaProcesso; origina ATA |
| **EtapaProcesso** | id, processo_id (FK), etapa ENUM (comunicado, acp, sap, pgm, lct, publicacao_edital, pregao, propostas, homologacao), dias_planejado, dias_real, concluida_em | Base do gráfico planejado × real |
| **ItemProcesso** | id, processo_id (FK), insumo_id (FK), quantidade_estimada | Liga insumo ao processo (RF21) |
| NotaEmpenho | id, numero (UNIQUE), processo_sei, demanda_id (FK), data_emissao, valor, status ENUM (demanda, validacao_saldo, pre_empenho, envio_fornecedor, ne_emitida), ata_id (FK), item_ata_id (FK), responsavel_id (FK) | Deduz saldo da ATA; gera NotaFiscal |
| NotaFiscal | id, numero, data, valor, nota_empenho_id (FK), fornecedor_id (FK), servidor_id (FK) | Vinculada à NE, não à ATA (RN02) |
| Fornecedor | id, cnpj (UNIQUE), razao_social, email, ativo | Emite Notas Fiscais |
| **Formulario** | id, tipo ENUM (equipamento, fornecedor, divergencia, devolucao), unidade_id (FK), payload JSONB, status, criado_em | Portal de formulários (RF25) |
| HistoricoMovimentacao | id, entidade_tipo, entidade_id, acao, usuario_id (FK), timestamp, dados_anteriores JSONB | Auditoria imutável |

## 5.3 Stack Tecnológica

| Camada | Tecnologia | Justificativa |
| :-- | :-- | :-- |
| Frontend | Next.js (React) | SSR nativo, roteamento simplificado, ecossistema amplo |
| Backend | Python · FastAPI | Alta performance async, tipagem com Pydantic, OpenAPI automática |
| Banco de Dados | PostgreSQL | Relacional robusto, suporte nativo a JSONB e auditoria |
| Autenticação | OAuth2 / OIDC via Entra ID | Reaproveita a identidade institucional já provisionada |
| ORM | SQLAlchemy + Alembic | ORM maduro; migrações versionadas |
| Agendamento | APScheduler | Recálculo diário de cobertura |
| Infraestrutura | Docker + servidor on-premise | Portabilidade e isolamento de ambientes |
| CI/CD | GitHub Actions | Automação de testes e deploy |

---

# 6. Segurança e Privacidade

## 6.1 Proteção contra OWASP Top 10

| # | Risco | Contramedida no SIGI |
| :-- | :-- | :-- |
| A01 | Broken Access Control | RBAC com cinco perfis; escopo por grupo de materiais e unidade; validação server-side em todo endpoint; HTTP 403 registrado em auditoria |
| A02 | Cryptographic Failures | HTTPS/TLS 1.2+ obrigatório; senhas de contingência com bcrypt (fator 12); tokens assinados RS256 |
| A03 | Injection | SQLAlchemy com queries parametrizadas; entradas validadas via Pydantic |
| A04 | Insecure Design | Threat modeling na fase de design; fluxo de NE sequencial; validação de saldo antes do pré-empenho |
| A05 | Security Misconfiguration | Imagens Docker mínimas (python:3.12-slim); segredos via secrets manager; CORS restrito; headers de segurança |
| A06 | Vulnerable Components | Dependabot no CI/CD; atualizações periódicas com testes antes do merge |
| A07 | Auth and Session Failures | Tokens OIDC de 15 min + refresh em httpOnly cookie (7 dias); logout invalida sessão; limite de tentativas no login de contingência |
| A08 | Software and Data Integrity | Verificação de hash de artefatos no CI/CD; **validação estrita de tipo, tamanho e formato nas importações CSV antes de persistir (RF30)** |
| A09 | Logging and Monitoring Failures | Histórico append-only no PostgreSQL; APM para anomalias; retenção ≥ 5 anos |
| A10 | SSRF | **Não aplicável ao MVP: o sistema não faz requisições de saída a sistemas externos.** A troca de dados é por upload de arquivo. |

> **Correção da v1.6.** A v1.6 mantinha, em A10 e na tabela de criptografia, referências a
> "chaves de API (DOMS, e-Pública)" e allowlist de URLs — resíduo da v1.5, incompatível
> com a decisão de não integrar via API.

## 6.2 Autenticação e Autorização

**Autenticação.** Mecanismo primário: **OAuth2/OIDC contra o Microsoft Entra ID**,
reaproveitando a matrícula e a credencial já provisionadas pela TI. Autenticação local
(e-mail institucional + senha com bcrypt) existe apenas como contingência para casos em
que a federação não esteja disponível.

Fluxo: o usuário é redirecionado ao Entra ID; o backend valida o token de identidade e
emite Access Token (15 min) e Refresh Token (7 dias, httpOnly cookie); o Auth Middleware
valida assinatura, expiração e perfil a cada chamada.

**Autorização — RBAC com escopo.** Além do perfil, cada usuário tem escopo por **grupo de
materiais** e por **unidade**.

| Perfil | Permissões |
| :-- | :-- |
| **gestor** | CRUD completo em ATAs, NEs, processos, insumos e usuários; avançar e reverter etapas; encerrar ATAs; acesso total a relatórios |
| **comprador** | Opera a lista de compras do seu grupo; abre e avança NEs; registra ação em andamento; acompanha processos. Sem reversão de etapa |
| **servidor** | Cadastra insumos e registra NFs vinculadas a NEs emitidas; visualiza o ciclo |
| **gestor_unidade** | Emite solicitações da sua unidade dentro da janela; consulta itens em falta e o consumo da própria unidade. **Não acessa o estoque central nem valores de ATA** |
| **auditor** | Somente leitura: histórico auditável, relatórios e exportações |

## 6.3 Criptografia de Dados Sensíveis

| Dado | Em Trânsito | Em Repouso |
| :-- | :-- | :-- |
| Credenciais de contingência | HTTPS/TLS 1.2+ | bcrypt (fator 12) |
| Tokens de sessão | HTTPS/TLS 1.2+ | Assinados RS256; refresh em httpOnly cookie |
| Dados pessoais (nome, e-mail) | HTTPS/TLS 1.2+ | PostgreSQL; colunas sensíveis com AES-256 *(pós-MVP)* |
| Logs de auditoria | HTTPS/TLS 1.2+ | Append-only; backups criptografados |
| Segredo do cliente OIDC | HTTPS/TLS 1.2+ | Variável de ambiente; secrets manager em produção |

## 6.4 Privacidade e LGPD

**Dados coletados** (princípio da minimização, art. 6º, III):

| Categoria | Dados | Base legal |
| :-- | :-- | :-- |
| Identificação do servidor | Nome, e-mail institucional, matrícula, perfil | Execução de contrato / obrigação legal (art. 7º, II e V) |
| Autenticação | Tokens de sessão, IP, user-agent | Legítimo interesse: segurança (art. 7º, IX) |
| Auditoria | ID do usuário, timestamp, ação, dados anteriores | Obrigação legal: transparência pública (art. 7º, II) |
| Operacional | ATAs, NEs, NFs, insumos, estoque | Execução de contrato (art. 7º, V) |

**Armazenamento e retenção.** PostgreSQL hospedado on-premise na entidade. Logs de
auditoria retidos por no mínimo 5 anos. Tokens descartados após expiração ou logout.
Nenhum dado é compartilhado com terceiros.

**Direitos do titular.**

| Direito | Como exercer |
| :-- | :-- |
| Confirmação e acesso | Tela de configurações da conta |
| Correção | Gestor atualiza via gerenciamento de usuários |
| Anonimização/exclusão | Solicitação ao encarregado (DPO) da entidade |
| Portabilidade | Exportação CSV mediante solicitação ao DPO |
| Revogação | Desativação pelo gestor; dados identificáveis anonimizados, preservando auditoria (art. 16, I) |

---

# 7. Planejamento do Projeto

## 7.1 Marcos de Desenvolvimento

Duração estimada: **18 semanas** a partir do kickoff.

| Marco | Descrição | Entregáveis | Prazo |
| :-- | :-- | :-- | :-- |
| **M1** — Setup e PoC | Ambiente, prova de conceito da stack, spike do Entra ID e da carga CSV do DOMS | Repositório, Docker Compose, `/health`, login via Entra ID, importador CSV validando formato | Semanas 1–2 |
| **M2** — Núcleo de Cobertura | Catálogo, grupos, posição de estoque, motor de cobertura e gatilho de compra | Cadastro de insumos, job diário de cobertura, faixas, demandas de compra, testes ≥ 70% | Semanas 3–6 |
| **M3** — ATAs e Empenhos | ATAs com itens, saldo e vigência; fluxo de NE em cinco etapas; NFs | API completa de ATA/NE/NF; histórico auditável | Semanas 7–9 |
| **M4** — Frontend MVP | Telas de Dashboard, Insumos, Visão 360°, Cobertura, Faltas e Compras | SPA integrada com dados reais | Semanas 10–13 |
| **M5** — Processos e Unidades | Processos licitatórios, unidades, cronograma, solicitações, taxa de atendimento, formulários | Módulos completos; notificação agregada; RBAC com escopo | Semanas 14–16 |
| **M6** — Testes e Deploy | UAT com o setor, hardening, conformidade LGPD, deploy | Relatório UAT, checklist OWASP, documentação, produção monitorada | Semanas 17–18 |

## 7.2 Cronograma

O cronograma é o definido em 7.1: seis marcos em 18 semanas, com revisão quinzenal junto
aos stakeholders. As datas absolutas serão fixadas na reunião de kickoff.

> **Correção da v1.6.** A seção 7.2 afirmava "não há cronograma de desenvolvimento" ao
> mesmo tempo em que 7.1 definia cinco marcos em 16 semanas.

## 7.3 Riscos e Mitigações

| Risco | Prob. | Impacto | Mitigação |
| :-- | :-- | :-- | :-- |
| **A carga do estoque depende de exportação manual do DOMS** | Alta | Alto | Definir periodicidade e responsável pela exportação; validar formato na importação; alertar quando a carga estiver desatualizada |
| **O República pode não emitir CSV de ATAs** | Alta | Médio | Cadastro manual da ATA com importação CSV apenas dos itens; confirmar com a TI |
| Inconsistência de tamanho/formato de campo na importação | Alta | Alto | RF30: validação estrita com relatório por linha e coluna, sem persistência parcial |
| Bloqueio de e-mail pela TI por volume | Média | Médio | RF26: digest agregado e seletivo, com limiar configurável |
| Escopo expandido durante o desenvolvimento | Média | Médio | Escopo fixado neste RFC; novas features para o backlog pós-MVP; revisão quinzenal |
| Dependência de uma única pessoa no conhecimento das regras | Média | Alto | Regras documentadas em §2.5; parametrização exposta na interface, não no código |
| Dificuldade de adoção pelas unidades | Média | Médio | Interface simplificada; treinamento; começar pelo painel de faltas, que é ganho imediato para a unidade |
| Performance do recálculo diário | Baixa | Médio | RNF11; índices no PostgreSQL; processamento em lote |

---

# 8. Referências

## 8.1 Documentação Técnica

- FastAPI — https://fastapi.tiangolo.com
- Next.js — https://nextjs.org/docs
- SQLAlchemy / Alembic — https://docs.sqlalchemy.org · https://alembic.sqlalchemy.org
- PostgreSQL — https://www.postgresql.org/docs
- Docker — https://docs.docker.com
- GitHub Actions — https://docs.github.com/actions
- Pydantic — https://docs.pydantic.dev
- Microsoft Entra ID (OIDC) — https://learn.microsoft.com/entra/identity-platform

## 8.2 Segurança e Conformidade

- OWASP Top 10 (2021) — https://owasp.org/www-project-top-ten
- OWASP API Security Top 10 — https://owasp.org/www-project-api-security
- LGPD, Lei 13.709/2018 — https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- ANPD, Guia Orientativo — https://www.gov.br/anpd

## 8.3 Ferramentas de Design

- Figma — https://figma.com
- Lucidchart — https://lucidchart.com
- draw.io — https://app.diagrams.net

## 8.4 Contexto e Benchmark

- Comprasnet / PNCP — https://www.gov.br/compras
- e-Publica, República e DOMS — documentação interna da entidade
- SIAD e SIGMAT — sistemas de referência do setor público

## 8.5 Repositório

- GitHub — https://github.com/isaacgraper/sigi

---

# 9. Apêndices

## 9.1 Fontes desta revisão

| Fonte | Data | Uso |
| :-- | :-- | :-- |
| Reunião com Anderson e Eduardo (2 áudios) | 17/08/2026 | Regras de negócio, correções de escopo e feedback do protótipo |
| Relatório Geral CAME (4 páginas, Looker Studio) | ago/2026 | Modelo de dados, indicadores e linhas de base |
| RFC_SIGI_v1_6.docx | 17/06/2026 | Documento base |
| Análise de lacunas | 01/09/2026 | [`analise-lacunas-rfc-v1.6.md`](./analise-lacunas-rfc-v1.6.md) |

## 9.2 Mapeamento do Relatório CAME para o Modelo de Dados

| Campo no relatório | Campo no SIGI | Entidade |
| :-- | :-- | :-- |
| SKU / Código do item | codigo (UNIQUE, DOMS) | Insumo |
| ITEM / Descrição | descricao | Insumo |
| GRUPO | grupo_id | GrupoMaterial |
| CONSUMO MÊS | consumo_medio_mensal | PosicaoEstoque |
| DIAS EST | cobertura_meses | PosicaoEstoque |
| EST. CLASSIF (A/B/C/D/S) | classificacao | Insumo |
| STATUS EST | faixa | PosicaoEstoque |
| QTD SALDO | saldo | PosicaoEstoque |
| PROCESSO SEI | processo_sei | NotaEmpenho |
| PREGÃO / STATUS DO PREGÃO | numero_processo / status | ProcessoLicitatorio |
| STATUS DA ATA | status | ATA |
| VENCIMENTO | data_vigencia_fim | ATA |
| EMPENHO | — | NotaEmpenho / AcaoEmAndamento |
| SOLICITADO / ATENDIDO | qtd_solicitada / qtd_atendida | ItemSolicitacao |
| UNIDADE / POPULAÇÃO / equipes | nome / populacao / equipes | Unidade |

## 9.3 Decisões Registradas

| # | Decisão | Data | Origem |
| :-- | :-- | :-- | :-- |
| D1 | O teto do aditivo da ATA é **25%** (RN10) | 01/09/2026 | Isaac, a partir das transcrições |

## 9.4 Pontos em Aberto

| # | Questão | Bloqueia |
| :-- | :-- | :-- |
| 1 | O SIGI substitui o painel CAME ou coexiste com ele? | Definição de escopo dos relatórios |
| 2 | O República emite CSV de ATAs? | RF13, M1 |
| 3 | Qual a periodicidade e o responsável pela exportação do estoque no DOMS? | RF04, M1 |
| 4 | "Sincatarina" é uma fonte de compra a integrar? | Escopo de RF10 |
| 5 | Confirmar as linhas de base de §1.6 (catálogo, valor em estoque) | KPIs |

## 9.5 Parecer do Comitê de Avaliação

*(A ser preenchido pelos professores)*

Avaliador 1: ______________________  Status: [ ] Aprovado [ ] Ajustar

Avaliador 2: ______________________  Status: [ ] Aprovado [ ] Ajustar

Avaliador 3: ______________________  Status: [ ] Aprovado [ ] Ajustar

---

# 10. Changelog v1.6 → v1.7

## Mudança estrutural

**Estoque volta a ser capacidade de primeira classe.** A v1.6 rebaixou o estoque a "dado
derivado das NEs" e afirmava, em RF03, que a quantidade de referência servia "apenas para
alertas de processo, não para controle de estoque". A operação real é orientada a
cobertura: o gatilho de compra é a cobertura cair abaixo de 3 meses. A v1.7 reverte essa
decisão e organiza o produto em torno dela.

## Correções (contradições com a reunião)

| Item | v1.6 | v1.7 |
| :-- | :-- | :-- |
| Autenticação | Gov.br OAuth 2.0 | **Entra ID / SSO institucional** (RF01, §6.2) |
| Casos de uso | Sem coluna de ator; diagrama não separava gestor de servidor | Coluna de ator em todos os UCs (§2.2) |
| Perfis | 3 (gestor, servidor, auditor) | 5, com **comprador** e **gestor_unidade** (§6.2) |
| Dashboard | ATAs ativas, insumos pendentes, NFs lançadas hoje | Orientado à cobertura e ao delta semanal da lista crítica (Tela 2) |
| Notificação | E-mail a cada mudança de status | Digest seletivo e agregado (RF26) |
| Importação de ATA | "Importação do e-Publica" como funcionalidade | Cadastro manual + CSV dos itens; origem correta é o **República** (RF13, §9.4) |

## Adições

- **7 entidades**: GrupoMaterial, Unidade, JanelaCronograma, Solicitacao/ItemSolicitacao,
  PosicaoEstoque, DemandaCompra, AcaoEmAndamento, ProcessoLicitatorio/EtapaProcesso/
  ItemProcesso, Formulario
- **RF04–RF12** — cobertura, estoque mínimo, faixas, gatilho de compra, painel de faltas,
  visão 360°, taxa de atendimento, delta semanal
- **RF19–RF22** — processo licitatório com nove etapas e planejado × real
- **RF23–RF25** — cronograma por unidade, solicitações e portal de formulários
- **RF30** — validação estrita de importação CSV
- **RN10–RN15** — aditivo 25%, regra de cobertura, sem giro (6 meses), condicionamento da
  compra à ATA, validação de saldo, janela de solicitação
- **Telas 4, 6, 7, 11 e 12** — visão 360°, faltas, lista de compras, processos e unidades
- **Job de Cobertura** como container próprio (§5.2)

## Remoções e correções internas

- Removidas as referências a chaves de API e allowlist de URLs para DOMS/e-Publica
  (§6.1 A10, §6.3), resíduo da v1.5 incompatível com RF29
- Corrigida a Persona 3, que misturava "Ana, Auditora Interna" com "Ana Carolina Souza —
  Gestora de Insumos"; personas reancoradas nos papéis reais
- Resolvida a contradição do cronograma entre §7.1 e §7.2
- KPIs de §1.6 substituídos por indicadores com linha de base real
- Acrescentados ao "Fora do Escopo": controle de fórmulas e suplementos, e gestão de
  pessoas — ambos excluídos pelos próprios stakeholders
- Números fictícios dos mockups sinalizados para refação
