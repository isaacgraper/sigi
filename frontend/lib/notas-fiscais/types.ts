/** The NF as `/api/v1/notas-fiscais` returns it (SPEC-0005 §7), as the screens of SPEC-0016 read it. */

export type NfStatus = "aguardando" | "em_conferencia" | "aprovada" | "devolvida";

export interface NfLine {
  id: string;
  item_nota_empenho_id: string;
  item_ata_id: string;
  insumo_id: string;
  sku: string;
  description: string;
  unit: string;
  quantidade: string;
}

export interface NotaFiscal {
  id: string;
  numero: string;
  data_emissao: string;
  valor: string;
  nota_empenho_id: string;
  nota_empenho_number: string | null;
  ata_id: string;
  fornecedor_id: string;
  owner_id: string;
  status: NfStatus;
  justificativa_devolucao: string | null;
  quarentena: boolean;
  motivo_quarentena: string | null;
  itens: NfLine[];
  created_at: string;
  updated_at: string;
}

export interface NfPage {
  items: NotaFiscal[];
  total: number;
  page: number;
  size: number;
}

/** The moves on an NF page (AC-0016-07, -08). */
export type NfAction = "enviar" | "aprovar" | "devolver" | "quarentena" | "liberar";
