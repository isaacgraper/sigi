/**
 * The ATA as `/api/v1/atas` returns it (SPEC-0002 §3), and the shapes the
 * screens build around it (SPEC-0013).
 */

export type Status = "vigente" | "suspensa" | "encerrada" | "cancelada";
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

export type Move = "suspender" | "retomar" | "encerrar" | "cancelar";

export type DueKind = "vencimento" | "reajuste";

/** One row of "Vencimentos e reajustes": either alert, with the date it falls due. */
export interface DueRow {
  kind: DueKind;
  ata: Ata;
  date: string;
  remaining: number;
}

export type Urgency = "overdue" | "soon" | "later";

// Keys are the API's payload paths, so a refusal's `fields` lands as it comes.
export type FormKey =
  | "number"
  | "subject"
  | "organ"
  | "fornecedor.cnpj"
  | "fornecedor.legal_name"
  | "issued_on"
  | "vigencia_inicio"
  | "vigencia_fim"
  | "total_value"
  | "budget_date";

export interface FormField {
  key: FormKey;
  label: string;
  type?: "date" | "money";
  optional?: boolean;
  /** What the "i" beside the label says (AC-0013-19). */
  help: string;
  wide?: boolean;
}

export interface FormSection {
  title: string;
  hint: string;
  fields: FormField[];
}

export type FormValues = Record<FormKey, string>;
