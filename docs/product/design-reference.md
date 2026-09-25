<!--
Design reference: Lovable prototype

This is third-party input. It is the DESIGN.md of the Lovable prototype of SIGI,
kept unchanged below the marker line so it can be quoted and diffed. Use it as a
style reference: tokens, shadcn/ui components, layout, and feedback and empty
states. It is not a source of requirements. Under ADR-0009 it ranks below this
repository's specs and ADRs, so wherever the two disagree, the spec is right.

The prototype was built without SIGI's domain rules, and it contradicts them in
the places listed here. SPEC-0010 settles each one. Nothing gets resolved by
editing the text below.

| This document says | SIGI says |
| --- | --- |
| ATA = "Autorizações de Tramitação de Aquisição" | Ata de Registro de Preços (`glossary.md`) |
| `/estoque` shows "saldo por ATA" | saldo and estoque are separate, and never shown as one figure (invariant 5) |
| saldo = `valorTotal − Σ NEs emitidas` | `contratado − reservado − empenhado`, taken from the NE ledger (ADR-0003, ADR-0007) |
| "Cadastrar insumo" records stock and minimum quantities | estoque comes only from the DOMS import, and no endpoint writes it (ADR-0008) |
| `/signup` for self-registration, collecting SIAPE | membership is by invitation only (SPEC-0001), and SIGI does not collect SIAPE |
| Login via Gov.br, with "lembrar sessão" | institutional OIDC (ADR-0010), refresh fixed at 7 days |
| `/admin` behind its own credential gate, with a switch per module | fixed perfis, enforced on the server for every route (invariant 8) |
| TanStack Router, Vite, in-memory store, a roadmap to Supabase with RLS | Next.js App Router, consuming the FastAPI API |

"Importar do e-Publica" is a local CSV parser, and the document itself says so.
That fits ADR-0002.
-->

# SIGI — Design System & Especificação de Interface

Sistema Integrado de Gestão de Insumos para órgãos públicos.

---

## 1. Visão Geral do Produto

O SIGI é uma plataforma web governamental para rastreamento ponta a ponta de insumos, ATAs (Autorizações de Tramitação de Aquisição / Registro de Preços), notas fiscais e notas de empenho. O objetivo é dar visibilidade operacional e financeira à gestão de contratos e estoques, reduzindo entrada manual de dados e evitando vencimentos, saldos esgotados e perdas de reajuste.

### Princípios de design

- **Clareza institucional**: interface sóbria, hierarquia tipográfica evidente, sem distrações visuais.
- **Ação rápida**: cadastros, importações e avanços de fluxo acessíveis em até dois cliques.
- **Confiança por transparência**: saldos, vigências e status sempre visíveis com indicadores de risco.
- **Acessibilidade primeiro**: contraste adequado, foco visível, rótulos claros e navegação por teclado.

---

## 2. Identidade Visual

### Paleta

A cor primária é um **verde escuro institucional**, usado para ações principais, marca e elementos de sucesso. Cores de status usam semântica neutra para não conflitar com o verde de "Em estoque / Aprovada / Vigente".

| Token | Uso |
|-------|-----|
| `primary` | Botões primários, ícones de destaque, marca, links |
| `accent` | Sucesso, "Recebido", "NE emitida", "Vigente", "Aprovada" |
| `amber-500` | Atenção, "Baixo estoque", "A vencer", "Pré-empenho", "Pendente" |
| `destructive` | Erro, "Esgotado", "Vencida", "Bloqueado", "Devolvida" |
| `slate-500` | Estados intermediários neutros: "Em análise", "Em conferência", "Demanda" |
| `muted` | Fundos secundários, hover de linha, estados inativos |

> **Regra de ouro**: nenhum filtro, badge de etapa ou status intermediário usa verde. Verde é reservado para conclusão/saúde. Cinza neutro (`slate`) representa "em andamento / aguardando".

### Tipografia

- Fonte padrão do sistema (`sans`), sem serifas.
- Títulos de página: `text-2xl font-semibold tracking-tight`.
- Títulos de card: `text-base font-semibold`.
- Corpo: `text-sm` para dados, `text-xs` para metadados e legendas.
- Monospace para códigos, SEI, NFs e NEs: `font-mono text-xs`.

### Espaçamento e Layout

- Container máximo das páginas: `max-w-7xl`.
- Grid de cards resumo: `grid gap-4 md:grid-cols-3` (ou 4 no admin).
- Espaçamento vertical entre seções: `gap-6`.
- Padding interno de cards: padrão do shadcn `Card`.
- Modais de cadastro: `max-w-xl` ou `max-w-2xl`.
- Tabelas envoltas em `overflow-hidden rounded-md border border-border`.

### Componentes Base (shadcn/ui)

- `Button`, `Input`, `Label`, `Select`, `Dialog`, `DropdownMenu`, `Popover`, `Tabs`, `Checkbox`, `Switch`, `Slider`, `Progress`, `Badge`, `Avatar`, `Separator`, `ScrollArea`, `Table`, `Card`, `Textarea`, `AlertDialog`.
- Ícones: `lucide-react`.
- Toasts: `sonner` (`<Toaster richColors position="top-right" />`).

---

## 3. Arquitetura de Navegação

### Shell autenticado

```
┌─────────────────────────────────────┐
│  AppHeader (sticky, z-30)           │
├──────────┬──────────────────────────┤
│          │                          │
│ Sidebar  │  <main className="p-6">   │
│          │  {children}              │
│          │                          │
└──────────┴──────────────────────────┘
```

- `Sidebar` colapsável, itens ativos por rota.
- `AppHeader` contém: trigger da sidebar, título do sistema, sino de notificações com contador, avatar com dropdown (Perfil, Configurações, Sair).

### Rotas

| Rota | Descrição | Shell |
|------|-----------|-------|
| `/` | Dashboard com cards navegáveis e insumos recentes | Sim |
| `/atas` | Gestão de ATAs, importação e-Publica, reajuste, aditivo | Sim |
| `/insumos` | Catálogo, estoque, importação CSV DOMS | Sim |
| `/estoque` | Saldo por ATA com dedução automática por NE | Sim |
| `/notas-empenho` | Fluxo SEI de solicitação de NE | Sim |
| `/notas-fiscais` | Lançamento e conferência de NFs | Sim |
| `/relatorios` | Gráficos e perfil de cobertura | Sim |
| `/login` | Entrar / aba cadastrar redireciona | Não |
| `/signup` | Solicitação de cadastro institucional | Não |
| `/admin` | Painel administrativo com gate próprio | Não |

---

## 4. Páginas e Fluxos

### 4.1 Dashboard (`/`)

- Três cards de resumo clicáveis:
  - **ATAs ativas** → `/atas`
  - **Insumos pendentes** → `/insumos`
  - **NFs lançadas hoje** → `/notas-fiscais`
- Cada card exibe: valor principal, delta com ícone de tendência, hint e seta no hover.
- Tabela "Insumos recentes" com colunas: Nome, ATA, Status, Última atualização.

### 4.2 ATAs (`/atas`)

**Cards de resumo:**
- Total de ATAs / vigentes
- Valor total contratado
- Valor empenhado + barra de progresso

**Card de alerta:** "ATAs a renovar" (vencem em ≤90 dias e sem aditivo).

**Ações principais:**
- "Importar do e-Publica": modal com upload de CSV e pré-visualização.
- "Cadastrar ATA": modal com campos obrigatórios, incluindo `dataOrcamentoPlanilhado`.

**Tabela:**
- Colunas: Número, Objeto, Fornecedor, Órgão, Vigência, Valor total, Empenhado, %, Status, Reajuste, Ações.
- Badges de vigência: "Vigente", "Vence em Xd", "Vencida".
- Badge de reajuste: "Disponível · Xd", "Solicitado em DD/MM", "Expirado".
- Ações por linha: "Registrar reajuste" e "Solicitar aditivo".

**Modal de aditivo:**
- Slider 0–25%.
- Preview do novo quantitativo/valor.
- Confirmação com toast.

### 4.3 Insumos (`/insumos`)

**Cards de resumo:**
- Itens cadastrados
- Alertas de estoque (baixo/esgotado)
- Categoria com mais itens

**Ações:**
- "Importar CSV (DOMS)": upload, preview, importação com merge por código.
- "Cadastrar insumo": modal com código, nome, categoria, unidade, estoque, mínimo, ATA.

**Tabela:**
- Colunas: Código, Nome, Categoria, ATA, Estoque (com mini progresso), Status.
- Status: "Em estoque" (verde), "Baixo estoque" (âmbar), "Pendente" (cinza), "Esgotado" (vermelho).

### 4.4 Estoque (`/estoque`)

**Cards de resumo:**
- Saldo total disponível
- ATAs em saldo crítico (≥80% consumido)
- NEs emitidas

**Tabela:**
- Agrupada por ATA: fornecedor, itens vinculados, NEs emitidas/pendentes, valor total, saldo atual, barra de % consumido.
- Saldo é derivado: `valorTotal - soma(NEs emitidas)`.

### 4.5 Notas de Empenho (`/notas-empenho`)

**Pipeline de etapas:**
1. Demanda
2. Validação saldo
3. Pré-empenho
4. Envio fornecedor
5. NE emitida

**Ações:**
- "Nova solicitação": modal valida saldo da ATA antes de abrir.
- "Avançar etapa" por linha.

**Tabela:**
- Colunas: Número, Processo SEI, ATA, Insumo, Qtd, Valor, Etapa, Ação.
- Etapas iniciais em cinza, intermediárias em âmbar, final em verde.

### 4.6 Notas Fiscais (`/notas-fiscais`)

**Cards:** Lançadas hoje, Total aprovado, Pendentes.

**Ações:**
- "Lançar NF": modal com número, fornecedor, ATA e valor.

**Tabela:**
- Colunas: Número, Fornecedor, ATA, Emissão, Valor, Status.
- Status: "Aprovada" (verde), "Em conferência" (cinza), "Aguardando" (âmbar), "Devolvida" (vermelho).

### 4.7 Relatórios (`/relatorios`)

- Gráfico de linha: Execução orçamentária (empenhado vs pago).
- Gráfico de pizza: Insumos por categoria.
- Gráfico de barras: NFs lançadas na semana.
- Card "Perfil de cobertura de insumos":
  - Lista "Sem demanda há N meses" (slider 1–12).
  - Lista "Cobertura crítica < N dias sem processo ativo" (slider 7–180).
- Card "Relatórios disponíveis" com botões de exportação (mock).

> Gráficos usam `recharts` dentro de um `ChartBox` que só renderiza após mount, evitando problemas de SSR com `ResponsiveContainer`.

### 4.8 Login / Cadastro

- Layout split-screen: painel de marca (verde primário) + formulário.
- Login: e-mail institucional, senha com mostrar/ocultar, lembrar sessão, Gov.br.
- Aba "Cadastrar" redireciona para `/signup`.
- Signup: dados pessoais, vínculo institucional, SIAPE, força de senha, termos LGPD.

### 4.9 Admin (`/admin`)

- Gate próprio de credenciais (fora do shell autenticado).
- Cards: total, ativos, pendentes, administradores.
- Tabela de membros com filtros por perfil e status.
- Ações: convidar, editar permissões, redefinir senha, bloquear/desbloquear, remover.
- Modal de permissões usa `Switch` por módulo.

---

## 5. Estados e Feedback

### Toasts

- Sucesso: ação concluída (cadastro, importação, avanço de etapa).
- Erro: validação de formulário, saldo insuficiente, credenciais inválidas.
- Info: funcionalidade em desenvolvimento.

### Empty states

- Tabelas sem resultado: linha única centralizada "Nenhum(a) X encontrado(a).".
- Listas de cobertura: mensagem informativa quando vazia.

### Loading

- Login/cadastro: botão desabilitado com texto "Entrando..." / "Enviando...".
- Gráficos: skeleton pulse até mount do cliente.

### Validação de formulários

- Campos obrigatórios verificados antes de submit.
- Mensagens diretas via `toast.error`.
- NE: validação de saldo da ATA antes de abrir solicitação.

---

## 6. Design Tokens no Código

Definidos em `src/styles.css` usando `oklch` e registrados no `@theme inline`.

Principais tokens usados nos componentes:

- `--background`, `--foreground`, `--card`, `--card-foreground`
- `--primary`, `--primary-foreground`
- `--secondary`, `--muted`, `--accent`, `--destructive`
- `--border`, `--input`, `--ring`
- `--sidebar-*` para a navegação lateral

Classes utilitárias comuns:

```
bg-background text-foreground
bg-card border-border/70 shadow-sm
bg-primary text-primary-foreground
bg-primary/10 text-primary
bg-accent/15 text-accent border-accent/30
bg-amber-500/15 text-amber-700 border-amber-500/30
bg-destructive/15 text-destructive border-destructive/30
bg-muted text-muted-foreground border-border
hover:bg-muted/40 hover:bg-muted/50
```

---

## 7. Acessibilidade

- Foco visível: `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`.
- Botões e inputs possuem `aria-label` quando são ícones.
- Modais usam `Dialog` do shadcn (foco trap, ESC para fechar).
- Cores de status não dependem apenas da cor (texto do badge é legível).
- Contraste verificado: verde escuro sobre fundo claro atende WCAG AA.

---

## 8. Responsividade

- Layout mobile: sidebar colapsa para ícones, header mantém ações essenciais.
- Grids de cards: 1 coluna em mobile, 3 em desktop.
- Filtros de tabela: empilham em mobile (`flex-col`), lado a lado em desktop (`sm:flex-row`).
- Modais: largura máxima fixa, padding interno adaptável.
- Tabelas: scroll horizontal quando necessário (`overflow-auto`).

---

## 9. Padrões de Implementação

### Estado global

- `src/lib/store.tsx` exporta `StoreProvider` e `useStore`.
- Dados mockados em memória; ações atualizam o estado React e refletem em todas as páginas.
- Helpers puros: `parseBRDate`, `formatBRDate`, `diasEntre`, `calcularSaldoAta`, `temProcessoAtivo`, `brl`.

### Rotas

- TanStack Router com `createFileRoute`.
- Cada rota define `head()` com `title` e `description`.
- `__root.tsx` decide se renderiza com ou sem shell baseado na rota atual.

### Componentes

- Preferência por componentes controlados.
- Formulários usam objetos de estado (`form`) e atualizam campo a campo.
- Importações agrupadas: shadcn primeiro, depois ícones, depois lógica local.

### Cores e badges

- Sempre usar variantes semânticas; nunca hardcodear hex em componentes.
- Badges de status usam `variant="outline"` + classe de cor de fundo/texto/borda.

---

## 10. Roadmap e Notas Técnicas

### Próximos passos sugeridos

1. **Persistência**: ativar Lovable Cloud e migrar `store.tsx` para Supabase com RLS.
2. **Autenticação real**: substituir mock de login/cadastro por auth integrada.
3. **Importações**: parsers CSV robustos com validação de schema (Zod) e relatório de erros.
4. **Exportações**: gerar PDF/CSV reais a partir dos dados em memória.
5. **Notificações**: backend de eventos para alertas de estoque e vencimento.
6. **Admin**: roles reais em tabela separada (`user_roles`) e políticas RLS.

### Decisões conscientes

- O painel `/admin` não aparece na sidebar do cliente e possui gate próprio para simular uma área restrita sem depender de autenticação real.
- A importação do e-Publica é um parser de CSV local, sem integração externa, conforme solicitado.
- Todos os cálculos de saldo e cobertura são derivados do estado compartilhado, garantindo consistência entre Estoque, NEs e Relatórios.

---

*Documento vivo — atualizar sempre que novos padrões visuais ou fluxos forem introduzidos.*
