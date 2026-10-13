/**
 * The ATA as `/api/v1/atas` returns it (SPEC-0002 §3), and the words the screens
 * use for it (SPEC-0013). Every value here comes from the API; nothing is derived.
 */

export type Status = "rascunho" | "vigente" | "suspensa" | "encerrada" | "cancelada";
export type Situacao = "vigente" | "a_vencer" | "vencida";

export interface Fornecedor {
  id: string;
  cnpj: string;
  legal_name: string;
}

export interface Ata {
  id: string;
  number: string;
  subject: string;
  organ: string;
  fornecedor: Fornecedor;
  issued_on: string | null;
  vigencia_inicio: string;
  vigencia_fim: string;
  total_value: string;
  valor_contratado: string;
  budget_date: string;
  status: Status;
  situacao_vigencia: Situacao;
  data_reajuste: string;
  owner_id: string;
  created_at: string;
}

export interface Aditivo {
  id: string;
  kind: "valor" | "prazo";
  valor_acrescimo: string | null;
  nova_vigencia_fim: string | null;
  justification: string;
  created_at: string;
}

export interface Reajuste {
  id: string;
  processo_sei: string;
  requested_on: string;
  created_at: string;
}

export interface AtaDetail extends Ata {
  aditivos: Aditivo[];
  reajustes: Reajuste[];
}

export interface AtaPage {
  items: Ata[];
  total: number;
  page: number;
  size: number;
}

export interface AlertRow {
  ata: Ata;
  days_remaining: number;
}

export const STATUSES: Status[] = ["rascunho", "vigente", "suspensa", "encerrada", "cancelada"];
export const SITUACOES: Situacao[] = ["vigente", "a_vencer", "vencida"];

export const STATUS_LABEL: Record<Status, string> = {
  rascunho: "Rascunho",
  vigente: "Vigente",
  suspensa: "Suspensa",
  encerrada: "Encerrada",
  cancelada: "Cancelada",
};

// Green only for health; waiting is slate, attention amber (DESIGN.md §2).
export const STATUS_TONE = {
  rascunho: "neutral",
  vigente: "success",
  suspensa: "attention",
  encerrada: "muted",
  cancelada: "danger",
} as const;

export const SITUACAO_LABEL: Record<Situacao, string> = {
  vigente: "Vigente",
  a_vencer: "A vencer",
  vencida: "Vencida",
};

export const SITUACAO_TONE = {
  vigente: "success",
  a_vencer: "attention",
  vencida: "danger",
} as const;

export type Move = "ativar" | "suspender" | "retomar" | "encerrar" | "cancelar";

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

/** One row of "Vencimentos e reajustes": either alert, with the date it falls due. */
export interface DueRow {
  kind: "vencimento" | "reajuste";
  ata: Ata;
  date: string;
  remaining: number;
}

/**
 * Both alerts as one list ordered by urgency (AC-0013-02). Which ATAs are in
 * each alert is the API's; this only puts its two answers side by side.
 */
export function dueRows(renovacao: AlertRow[], reajuste: AlertRow[]): DueRow[] {
  return [
    ...renovacao.map((row) => ({
      kind: "vencimento" as const,
      ata: row.ata,
      date: row.ata.vigencia_fim,
      remaining: row.days_remaining,
    })),
    ...reajuste.map((row) => ({
      kind: "reajuste" as const,
      ata: row.ata,
      date: row.ata.data_reajuste,
      remaining: row.days_remaining,
    })),
  ].sort((a, b) => a.remaining - b.remaining || a.ata.number.localeCompare(b.ata.number));
}

/** The API's days remaining, in words: "45 dias", "1 dia", "hoje", "há 3 dias". */
export function dueText(remaining: number): string {
  if (remaining === 0) return "hoje";
  const n = Math.abs(remaining);
  const days = n === 1 ? "1 dia" : `${n} dias`;
  return remaining > 0 ? days : `há ${days}`;
}
