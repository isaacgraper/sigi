/** What the NF screens read (SPEC-0016). Shared values live in lib/constants.ts. */
import type { NfAction, NfStatus } from "@/lib/notas-fiscais/types";
import type { StatusTone } from "@/lib/types";

export const NF_STATUSES: NfStatus[] = ["aguardando", "em_conferencia", "aprovada", "devolvida"];

export const NF_STATUS_LABEL: Record<NfStatus, string> = {
  aguardando: "Aguardando",
  em_conferencia: "Em conferência",
  aprovada: "Aprovada",
  devolvida: "Devolvida",
};

// Colour is rare: amber while the NF waits on someone, grey once approved.
export const NF_STATUS_TONE: Record<NfStatus, StatusTone> = {
  aguardando: "neutral",
  em_conferencia: "attention",
  aprovada: "muted",
  devolvida: "attention",
};

export const QUARENTENA_LABEL = "Em quarentena";

/** The list filter's value for the quarantine flag, beside the four statuses (AC-0016-02). */
export const FILTER_QUARENTENA = "quarentena";

// The statuses an NF may still be corrected in (AC-0005-14).
export const EDITABLE: NfStatus[] = ["aguardando", "devolvida"];

export const NF_ACTION_LABEL: Record<NfAction, string> = {
  enviar: "Enviar para conferência",
  aprovar: "Aprovar",
  devolver: "Devolver",
  quarentena: "Quarentena",
  liberar: "Liberar",
};

export const NF_ACTION_DONE: Record<NfAction, string> = {
  enviar: "NF enviada para conferência.",
  aprovar: "NF aprovada.",
  devolver: "NF devolvida.",
  quarentena: "NF em quarentena.",
  liberar: "NF liberada da quarentena.",
};

// Mirrors api-conventions.md.
export const NF_PAGE_SIZE = 25;

export const NF_LIST_COLUMNS = ["Número", "NE", "Data de emissão", "Valor", "Status"];

export const NF_ORDER = ["numero", "data_emissao", "valor", "fornecedor_cnpj", "itens"];

// Codes the API sends without `fields`, and the field each one belongs to.
export const NF_CODE_FIELD: Record<string, string> = {
  NF_DUPLICADA: "numero",
  FORNECEDOR_DIVERGENTE: "fornecedor_cnpj",
  VALOR_ACIMA_DO_EMPENHO: "valor",
  QUANTIDADE_ACIMA_DO_EMPENHO: "itens",
};

/** The refusal that a confirmation turns into a registration (AC-0005-05). */
export const DATA_ANTERIOR = "DATA_ANTERIOR_AO_EMPENHO";

export const NF_ACTION_ORDER = ["justificativa", "motivo"];

// The statuses an NF may be held in (AC-0005-13).
export const QUARANTINABLE: NfStatus[] = ["aguardando", "em_conferencia"];

/** The text a move asks for, and the key the API reads it under. */
export const NF_ACTION_ASKS: Partial<Record<NfAction, { key: string; label: string }>> = {
  devolver: { key: "justificativa", label: "Justificativa" },
  quarentena: { key: "motivo", label: "Motivo" },
};

export const NF_ACTION_DESCRIPTION: Record<NfAction, string> = {
  enviar: "A NF passa para a conferência do gestor.",
  aprovar: "A NF fica aprovada e não muda mais depois disso.",
  devolver: "A NF volta para correção e deixa de contar na NE. A justificativa fica registrada no histórico.",
  quarentena: "Os itens desta NF ficam em quarentena até serem liberados, e a NF não pode ser aprovada.",
  liberar: "Os itens desta NF voltam a contar como recebidos.",
};
