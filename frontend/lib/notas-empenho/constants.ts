/** What the NE screens read (SPEC-0015). Shared values live in lib/constants.ts. */
import type { NeAction, NeStatus, Stage } from "@/lib/notas-empenho/types";
import type { StatusTone } from "@/lib/types";

// The five stages in their order (RN08), and the one exit.
export const STAGES: Stage[] = ["demanda", "validacao_saldo", "pre_empenho", "envio_fornecedor", "ne_emitida"];
export const NE_STATUSES: NeStatus[] = [...STAGES, "cancelada"];

export const STAGE_LABEL: Record<NeStatus, string> = {
  demanda: "Demanda",
  validacao_saldo: "Validação de saldo",
  pre_empenho: "Pré-empenho",
  envio_fornecedor: "Envio ao fornecedor",
  ne_emitida: "NE emitida",
  cancelada: "Cancelada",
};

// Colour is rare: amber while saldo is held in reserve, grey once finished.
export const STAGE_TONE: Record<NeStatus, StatusTone> = {
  demanda: "neutral",
  validacao_saldo: "neutral",
  pre_empenho: "attention",
  envio_fornecedor: "attention",
  ne_emitida: "muted",
  cancelada: "muted",
};

// The stage whose entry asks for a número issued outside SIGI (SPEC-0004 §9).
export const NUMERO_FIELD: Partial<Record<Stage, { key: "numero_pre_empenho" | "number"; label: string; help: string }>> = {
  pre_empenho: {
    key: "numero_pre_empenho",
    label: "Número da nota de pré-empenho",
    help: "O número da nota de pré-empenho emitida pelo setor financeiro, como consta no documento.",
  },
  ne_emitida: {
    key: "number",
    label: "Número da NE",
    help: "O número da nota de empenho emitida pelo sistema financeiro, como consta no documento.",
  },
};

export const ACTION_LABEL: Record<NeAction, string> = {
  avancar: "Avançar",
  reverter: "Reverter etapa",
  cancelar: "Cancelar NE",
};

export const ACTION_DONE: Record<NeAction, string> = {
  avancar: "Etapa avançada.",
  reverter: "Etapa revertida.",
  cancelar: "NE cancelada.",
};

// Mirrors api-conventions.md and AC-0015-01.
export const NE_PAGE_SIZE = 25;

export const LIST_COLUMNS = ["Processo SEI", "ATA", "Etapa", "Valor", "Pré-empenho", "NE", "Aberta em"];

// Codes the API sends without `fields`, and the field each one belongs to.
export const ADVANCE_CODE_FIELD: Record<string, string> = {
  NE_DUPLICADA: "number",
  PRE_EMPENHO_DUPLICADO: "numero_pre_empenho",
};

export const OPEN_ORDER = ["ata_id", "processo_sei", "items"];
export const OPEN_CODE_FIELD: Record<string, string> = {
  PROCESSO_SEI_INVALIDO: "processo_sei",
  ATA_NAO_ELEGIVEL: "ata_id",
};

export const PROCESSO_SEI_HINT = "Formato NNNNN.NNNNNN/AAAA-DD.";
