/** What the ATA screens read (SPEC-0013). Shared values live in lib/constants.ts. */
import type { DueKind, FormKey, FormSection, FormValues, Move, Situacao, Status, Urgency } from "@/lib/atas/types";

// ── Status and situação ─────────────────────────────────────────────────────

export const STATUSES: Status[] = ["rascunho", "vigente", "suspensa", "encerrada", "cancelada"];
export const SITUACOES: Situacao[] = ["vigente", "a_vencer", "vencida"];

export const STATUS_LABEL: Record<Status, string> = {
  rascunho: "Rascunho",
  vigente: "Vigente",
  suspensa: "Suspensa",
  encerrada: "Encerrada",
  cancelada: "Cancelada",
};

export const SITUACAO_LABEL: Record<Situacao, string> = {
  vigente: "Vigente",
  a_vencer: "A vencer",
  vencida: "Vencida",
};

// ── List ────────────────────────────────────────────────────────────────────

// Mirrors AC-0013-03.
export const ATAS_PAGE_SIZE = 25;

/** The filter value that means "no filter"; never a status or a situação. */
export const FILTER_ALL = "todos";

export const LIST_COLUMNS = ["Número", "Objeto", "Fornecedor", "Vigência", "Valor contratado", "Status", "Reajuste em"];

// ── Vencimentos e reajustes ─────────────────────────────────────────────────

// 30 days is the product owner's "really close" (OQ-47, decided 2026-10-13).
export const SOON_DAYS = 30;

// The block sits above the ATA list; past a handful it would push the list off
// the screen, and the rest are by definition less urgent.
export const DUE_LIST_FIRST = 5;

export const DUE_KIND_LABEL: Record<DueKind, string> = {
  vencimento: "Vencimento",
  reajuste: "Reajuste",
};

// Colour answers "do I act now?" before anything is read: red once past, amber
// when close, nothing when there is time. A bar on the left edge carries it for
// a scanning eye, and the words carry it for anyone who cannot see the colour.
export const URGENCY_CLASSES: Record<Urgency, { row: string; days: string; kind: string }> = {
  overdue: {
    row: "border-l-danger bg-danger/[0.06] [@media(hover:hover)_and_(pointer:fine)]:hover:bg-danger/10",
    days: "text-danger",
    kind: "text-danger",
  },
  soon: {
    row: "border-l-attention [@media(hover:hover)_and_(pointer:fine)]:hover:bg-muted/50",
    days: "text-attention",
    kind: "text-muted-foreground",
  },
  later: {
    row: "border-l-transparent [@media(hover:hover)_and_(pointer:fine)]:hover:bg-muted/50",
    days: "text-foreground",
    kind: "text-muted-foreground",
  },
};

// ── Moves ───────────────────────────────────────────────────────────────────

/**
 * The moves offered per status. It mirrors AC-0002-22 so a gestor is not shown
 * a button that can only fail; the API stays the authority (AC-0013-12).
 */
export const MOVES: Record<Status, Move[]> = {
  rascunho: ["ativar", "cancelar"],
  vigente: ["suspender", "encerrar", "cancelar"],
  suspensa: ["retomar", "encerrar", "cancelar"],
  encerrada: [],
  cancelada: [],
};

export const MOVE: Record<
  Move,
  { label: string; title: string; body: string; done: string; destructive: boolean }
> = {
  ativar: {
    label: "Ativar",
    title: "Ativar ATA?",
    body: "A ATA passa a vigente. Depois disso, valores e prazos só mudam por aditivo.",
    done: "ATA ativada.",
    destructive: false,
  },
  suspender: {
    label: "Suspender",
    title: "Suspender ATA?",
    body: "A ATA fica suspensa até ser retomada.",
    done: "ATA suspensa.",
    destructive: false,
  },
  retomar: {
    label: "Retomar",
    title: "Retomar ATA?",
    body: "A ATA volta a vigente.",
    done: "ATA retomada.",
    destructive: false,
  },
  encerrar: {
    label: "Encerrar",
    title: "Encerrar ATA?",
    body: "A ATA é encerrada e esta ação não pode ser desfeita.",
    done: "ATA encerrada.",
    destructive: true,
  },
  cancelar: {
    label: "Cancelar",
    title: "Cancelar ATA?",
    body: "A ATA é cancelada e esta ação não pode ser desfeita. Registre o motivo.",
    done: "ATA cancelada.",
    destructive: true,
  },
};

// ── Registration and edit form ──────────────────────────────────────────────

// The ATA page's own grouping, so the form looks like the page it produces (AC-0013-07).
export const FORM_SECTIONS: FormSection[] = [
  {
    title: "Identificação",
    hint: "O número é único entre as ATAs.",
    fields: [
      { key: "number", label: "Número", locks: true },
      { key: "organ", label: "Órgão" },
      { key: "subject", label: "Objeto", wide: true },
    ],
  },
  {
    title: "Fornecedor",
    hint: "Se o CNPJ já estiver cadastrado, a razão social dele é mantida.",
    fields: [
      { key: "fornecedor.cnpj", label: "CNPJ do fornecedor", locks: true },
      { key: "fornecedor.legal_name", label: "Razão social", locks: true },
    ],
  },
  {
    title: "Vigência",
    hint: "O fim precisa ser depois do início.",
    fields: [
      { key: "vigencia_inicio", label: "Início da vigência", type: "date", locks: true },
      { key: "vigencia_fim", label: "Fim da vigência", type: "date", locks: true },
      { key: "issued_on", label: "Data de emissão (opcional)", type: "date", optional: true, locks: true },
    ],
  },
  {
    title: "Valores",
    hint: "O reajuste vence um ano depois do orçamento planilhado.",
    fields: [
      { key: "total_value", label: "Valor total (R$)", type: "money", locks: true },
      { key: "budget_date", label: "Data do orçamento planilhado", type: "date", locks: true },
    ],
  },
];

export const FORM_FIELDS = FORM_SECTIONS.flatMap((section) => section.fields);

/** The order errors are focused in: the order the fields are read in. */
export const FORM_ORDER = FORM_FIELDS.map((field) => field.key);

export const FORM_EMPTY = Object.fromEntries(FORM_ORDER.map((key) => [key, ""])) as FormValues;

// Refusals that name no field in `fields` but belong to one (SPEC-0002 §3.7).
export const FORM_CODE_FIELD: Record<string, FormKey> = { ATA_DUPLICADA: "number" };

// ── Aditivo and reajuste dialogs ────────────────────────────────────────────

export const ADITIVO_ORDER = ["kind", "valor_acrescimo", "nova_vigencia_fim", "justification"];
export const ADITIVO_CODES: Record<string, string> = { ADITIVO_ACIMA_DO_LIMITE: "valor_acrescimo" };

export const REAJUSTE_ORDER = ["processo_sei", "requested_on"];
export const REAJUSTE_CODES: Record<string, string> = { PROCESSO_SEI_INVALIDO: "processo_sei" };
