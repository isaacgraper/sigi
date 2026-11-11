/** What the history screens read (SPEC-0017). Shared values live in lib/constants.ts. */
import { STATUS_LABEL as ATA_STATUS_LABEL } from "@/lib/atas/constants";
import type { Atalho, Etapa, Tipo } from "@/lib/historico/types";
import { STAGE_LABEL } from "@/lib/notas-empenho/constants";
import { NF_STATUS_LABEL } from "@/lib/notas-fiscais/constants";

// Mirrors api-conventions.md and AC-0017-08.
export const HISTORICO_PAGE_SIZE = 25;
// Every member, to name who did what; the API serves at most this many a page.
export const MEMBERS_FOR_NAMES = 100;
// A record's tab reads its newest events up to this; the rest are in the Histórico.
export const ACOMPANHAMENTO_SIZE = 100;

/** Every entidade_tipo a row is written with (SPEC-0007 `ENTIDADE_TIPOS`), in pt-BR. */
export const ENTIDADE_LABEL: Record<string, string> = {
  ata: "ATA",
  insumo: "Insumo",
  grupo_material: "Grupo de materiais",
  nota_empenho: "NE",
  nota_fiscal: "NF",
  fornecedor: "Fornecedor",
  usuario: "Membro",
  relatorio: "Relatório",
  rota: "Acesso",
};

export const ENTIDADE_TIPOS = Object.keys(ENTIDADE_LABEL);

/** The page an entity opens on, when it has one (AC-0017-08). */
export const ENTIDADE_ROUTE: Record<string, string> = {
  ata: "/atas",
  insumo: "/insumos",
  nota_empenho: "/notas-empenho",
  nota_fiscal: "/notas-fiscais",
};

/** The tab that holds the history of a record, in its URL (SPEC-0017 §6). */
export const TAB_PARAM = "aba";
export const TAB_ACOMPANHAMENTO = "acompanhamento";
export const TAB_DADOS_LABEL = "Dados";
export const TAB_ACOMPANHAMENTO_LABEL = "Acompanhamento";

// ── Changes ─────────────────────────────────────────────────────────────────

/** The tipos each shortcut keeps (AC-0017-11). */
export const ATALHO_TIPOS: Record<Atalho, Tipo[]> = {
  valor: ["dinheiro", "quantidade"],
  status: ["status"],
};

export const ATALHO_LABEL: Record<Atalho, string> = {
  valor: "Só mudanças de valor",
  status: "Só mudanças de status",
};

export const ATALHO_PARAM = "so";

/** Every status a row may record, by its name on screen; the field's own wins. */
export const STATUS_VALUE_LABEL: Record<string, string> = {
  ...ATA_STATUS_LABEL,
  ...STAGE_LABEL,
  ...NF_STATUS_LABEL,
  ativo: "Ativo",
  pendente: "Pendente",
  bloqueado: "Bloqueado",
  desativado: "Desativado",
};

export const YES = "Sim";
export const NO = "Não";
export const NOTHING = "—";
// AC-0017-03: a creation lists its first values, a removal the ones it had.
export const CREATED_WITH = "Criado com";
export const REMOVED = "Removido";

// ── Rastreio ────────────────────────────────────────────────────────────────

export const ETAPA_LABEL: Record<Etapa, string> = {
  ata: "ATA",
  item_ata: "Item da ATA",
  nota_empenho: "Nota de empenho",
  nota_fiscal: "Nota fiscal",
};

export const RASTREIO_EMPTY = "O rastreio deste insumo ainda não começou: ele não é item de nenhuma ATA.";
export const SHOW_EVENTS = "Ver acompanhamento";
export const HIDE_EVENTS = "Ocultar acompanhamento";
export const NO_EVENTS = "Nenhum evento registrado.";
export const MISSING_PREFIX = "Faltam";
export const CURRENT_ETAPA = "etapa atual";

// ── Histórico ───────────────────────────────────────────────────────────────

export const HISTORICO_COLUMNS = ["Quando", "Ação", "Entidade", "Quem"];
export const HISTORICO_DENIED = "O histórico completo é lido pelo gestor e pelo auditor. Acompanhe um insumo pelo rastreio, na página dele.";
export const HISTORICO_EMPTY = "Nenhum evento neste filtro.";
export const ATALHO_EMPTY = "Nenhum evento desta página tem esse tipo de mudança.";
export const NO_ONE = "Sistema";

/** The keys the Histórico keeps in its URL, in pt-BR as the other lists do (AC-0017-08). */
export const HISTORICO_FILTER_KEYS = ["entidade", "id", "usuario", "de", "ate", ATALHO_PARAM] as const;

/** A calendar date as the API writes it, told apart from an instant. */
export const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

export const LINK_CLASS =
  "text-primary underline-offset-4 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:hover)_and_(pointer:fine)]:hover:underline";
