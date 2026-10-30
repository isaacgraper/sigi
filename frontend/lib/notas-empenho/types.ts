/**
 * The NE as `/api/v1/notas-empenho` returns it (SPEC-0004 §7), and the saldo of
 * an ATA (SPEC-0006 §3.1), as the screens of SPEC-0015 read them.
 */

export type Stage = "demanda" | "validacao_saldo" | "pre_empenho" | "envio_fornecedor" | "ne_emitida";
export type NeStatus = Stage | "cancelada";

export interface NeLine {
  id: string;
  item_ata_id: string;
  insumo_id: string;
  sku: string;
  description: string;
  unit: string;
  quantity: string;
  unit_price: string;
  value: string;
}

export interface NotaEmpenho {
  id: string;
  number: string | null;
  numero_pre_empenho: string | null;
  processo_sei: string;
  status: NeStatus;
  ata_id: string;
  ata_number: string;
  value: string;
  items: NeLine[];
  issued_on: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface NePage {
  items: NotaEmpenho[];
  total: number;
  page: number;
  size: number;
}

export interface Indicators {
  emitidas: number;
  em_andamento: number;
  total: number;
}

export interface SaldoAta {
  valor_contratado: string;
  valor_reservado: string;
  valor_empenhado: string;
  saldo_disponivel: string;
  comprometimento_percentual: string;
  alto_consumo: boolean;
  calculado_em: string;
}

export interface SaldoItem {
  item_ata_id: string;
  insumo_id: string;
  sku: string;
  description: string;
  unit: string;
  quantidade_contratada: string;
  quantidade_reservada: string;
  quantidade_empenhada: string;
  quantidade_disponivel: string;
  esgotado: boolean;
}

export interface SaldoItens {
  items: SaldoItem[];
  calculado_em: string;
}

/** The three moves on an NE page, and what each asks for. */
export type NeAction = "avancar" | "reverter" | "cancelar";
