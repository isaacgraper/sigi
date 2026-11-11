/** What the export dialog reads (SPEC-0009 v1.2 AC-0009-13). Mirrors the API's §2.1. */

export type ListExport = "atas" | "itens-ata" | "insumos" | "notas-empenho" | "notas-fiscais" | "historico";
export type Formato = "csv" | "pdf";

export const FORMATOS: { value: Formato; label: string }[] = [
  { value: "csv", label: "CSV (planilha)" },
  { value: "pdf", label: "PDF" },
];

/** Each list's columns, by the key `colunas` names them with, in the API's order. */
export const EXPORT_COLUMNS: Record<ListExport, { key: string; label: string }[]> = {
  atas: [
    { key: "ata", label: "Número" },
    { key: "objeto", label: "Objeto" },
    { key: "fornecedor", label: "Fornecedor" },
    { key: "vigencia_inicio", label: "Início da vigência" },
    { key: "vigencia_fim", label: "Fim da vigência" },
    { key: "valor_contratado", label: "Valor contratado" },
    { key: "status", label: "Status" },
    { key: "situacao", label: "Situação da vigência" },
  ],
  "itens-ata": [
    { key: "numero_item", label: "Item" },
    { key: "sku", label: "SKU" },
    { key: "descricao", label: "Descrição" },
    { key: "unidade", label: "Unidade" },
    { key: "quantidade", label: "Quantidade" },
    { key: "valor_unitario", label: "Valor unitário" },
    { key: "valor_total", label: "Valor total" },
  ],
  insumos: [
    { key: "sku", label: "SKU" },
    { key: "descricao", label: "Descrição" },
    { key: "unidade", label: "Unidade" },
    { key: "grupo", label: "Grupo" },
    { key: "codigo_doms", label: "Código DOMS" },
    { key: "codigo_externo", label: "Código externo" },
    { key: "situacao", label: "Situação" },
  ],
  "notas-empenho": [
    { key: "processo_sei", label: "Processo SEI" },
    { key: "ata", label: "ATA" },
    { key: "etapa", label: "Etapa" },
    { key: "valor", label: "Valor" },
    { key: "numero_pre_empenho", label: "Pré-empenho" },
    { key: "ne", label: "NE" },
    { key: "aberta_em", label: "Aberta em" },
  ],
  "notas-fiscais": [
    { key: "nf", label: "NF" },
    { key: "ne", label: "NE" },
    { key: "ata", label: "ATA" },
    { key: "data_emissao", label: "Data de emissão" },
    { key: "valor", label: "Valor" },
    { key: "status", label: "Status" },
    { key: "quarentena", label: "Em quarentena" },
  ],
  historico: [
    { key: "quando", label: "Quando" },
    { key: "acao", label: "Ação" },
    { key: "entidade", label: "Entidade" },
    { key: "entidade_id", label: "Identificador da entidade" },
    { key: "quem", label: "Quem" },
    { key: "alteracoes", label: "Alterações" },
    { key: "detalhes", label: "Detalhes" },
  ],
};

// São Paulo keeps UTC−3 all year since 2019; a day chosen there starts and ends at this offset.
export const SAO_PAULO_OFFSET = "-03:00";
export const DAY_START = "T00:00:00";
export const DAY_END = "T23:59:59.999";

export const EXPORT_LABEL = "Exportar";
export const EXPORTING_LABEL = "Exportando...";
export const EXPORT_DONE = "Arquivo exportado.";
export const COLUMNS_NONE = "Escolha ao menos uma coluna.";
export const EXPORT_DESCRIPTION =
  "O arquivo leva os filtros da lista e abre com quem exportou, quando e a data de referência.";
export const REFERENCE_HELP =
  "Cada linha sai como estava no fim deste dia. Hoje, sai como está agora.";
export const START_HELP = "Deixe vazio para tudo até a data de referência.";
/** The name a download takes when the API sends none. */
export const FALLBACK_FILENAME = "sigi-exportacao";
