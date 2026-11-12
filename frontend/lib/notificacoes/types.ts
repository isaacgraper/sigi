/** What `/api/v1/notificacoes` answers (SPEC-0008 §5). */

export type Motivo = "vai_vencer" | "venceu" | "saldo_80" | "saldo_esgotado" | "reajuste";

export interface Aviso {
  id: string;
  ata_id: string;
  ata_number: string;
  motivo: Motivo;
  motivo_rotulo: string;
  dados: Record<string, string>;
  criada_em: string;
  lida: boolean;
}

export interface AvisoPage {
  items: Aviso[];
  total: number;
  page: number;
  size: number;
  nao_lidas: number;
}
