/** What the history and the cycle of an insumo answer (SPEC-0007 §2.1, AC-0007-10). */

/** How a value is written on screen; closed by SPEC-0007 §2.1. */
export type Tipo = "data" | "dinheiro" | "quantidade" | "texto" | "status" | "referencia" | "itens";

export type Valor = string | boolean | number | null | ItemLine[] | Record<string, unknown>;

export interface ItemLine {
  [key: string]: string;
}

export interface Alteracao {
  campo: string;
  rotulo: string;
  tipo: Tipo;
  antes: Valor;
  depois: Valor;
}

export interface Detalhe {
  campo: string;
  rotulo: string;
  valor: Valor;
}

/** What every event carries, in the history and in the cycle alike. */
export interface Evento {
  entidade_tipo: string;
  entidade_id: string;
  acao: string;
  acao_rotulo: string;
  usuario_id: string | null;
  ocorrido_em: string;
  justificativa: string | null;
  alteracoes: Alteracao[];
  detalhes: Detalhe[];
}

export interface HistoricoRow extends Evento {
  id: string;
  correlation_id: string;
}

export interface HistoricoPage {
  items: HistoricoRow[];
  total: number;
  page: number;
  size: number;
}

export type Etapa = "ata" | "item_ata" | "nota_empenho" | "nota_fiscal";

export interface CicloEvento extends Evento {
  etapa: Etapa;
}

export interface Ciclo {
  insumo_id: string;
  sku: string;
  eventos: CicloEvento[];
}

/** The two shortcuts of the Histórico (AC-0017-11). */
export type Atalho = "valor" | "status";

/** The record whose history a tab reads (AC-0017-01, -02). */
export type Registro = "ata" | "nota_empenho" | "nota_fiscal";
