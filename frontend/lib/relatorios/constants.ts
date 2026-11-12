/** What the export dialog and the Relatórios screen read (SPEC-0009 v1.2, SPEC-0018). Mirrors the API's §2.1. */

export type ListExport = "atas" | "itens-ata" | "insumos" | "notas-empenho" | "notas-fiscais" | "historico";
export type Report = "execucao-orcamentaria" | "posicao-saldo" | "notas-fiscais-em-conferencia" | "indicadores-fornecedores";
export type ExportKey = ListExport | Report;
export type Formato = "csv" | "pdf";

export const FORMATOS: { value: Formato; label: string }[] = [
  { value: "csv", label: "CSV (planilha)" },
  { value: "pdf", label: "PDF" },
];

/** Each list's columns, by the key `colunas` names them with, in the API's order. */
export const EXPORT_COLUMNS: Record<ExportKey, { key: string; label: string }[]> = {
  "execucao-orcamentaria": [
    { key: "ata", label: "ATA" },
    { key: "fornecedor", label: "Fornecedor" },
    { key: "processo_sei", label: "Processo SEI" },
    { key: "numero_pre_empenho", label: "Pré-empenho" },
    { key: "ne", label: "NE" },
    { key: "stage", label: "Etapa" },
    { key: "value", label: "Valor" },
    { key: "issued_on", label: "Data de emissão" },
  ],
  "posicao-saldo": [
    { key: "ata", label: "ATA" },
    { key: "fornecedor", label: "Fornecedor" },
    { key: "status", label: "Situação" },
    { key: "vigencia_fim", label: "Fim da vigência" },
    { key: "valor_contratado", label: "Valor contratado" },
    { key: "valor_reservado", label: "Valor reservado" },
    { key: "valor_empenhado", label: "Valor empenhado" },
    { key: "saldo_disponivel", label: "Saldo disponível" },
    { key: "comprometimento_percentual", label: "Comprometimento (%)" },
    { key: "alto_consumo", label: "Alto consumo" },
  ],
  "notas-fiscais-em-conferencia": [
    { key: "nf", label: "NF" },
    { key: "fornecedor", label: "Fornecedor" },
    { key: "ne", label: "NE" },
    { key: "ata", label: "ATA" },
    { key: "issued_on", label: "Data de emissão" },
    { key: "value", label: "Valor" },
  ],
  "indicadores-fornecedores": [
    { key: "fornecedor", label: "Fornecedor" },
    { key: "cnpj", label: "CNPJ" },
    { key: "atas", label: "ATAs" },
    { key: "valor_contratado", label: "Valor contratado" },
    { key: "valor_empenhado", label: "Valor empenhado" },
    { key: "nfs_lancadas", label: "NFs lançadas" },
    { key: "nfs_aprovadas", label: "NFs aprovadas" },
    { key: "nfs_devolvidas", label: "NFs devolvidas" },
    { key: "valor_aprovado", label: "Valor aprovado" },
  ],
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

// ── The Relatórios screen (SPEC-0018) ──────────────────────────────────────

/** The four reports of RF12, in the API's order (AC-0018-01). */
export const REPORTS: { key: Report; name: string; description: string; period: boolean }[] = [
  {
    key: "execucao-orcamentaria",
    name: "Execução orçamentária por ATA",
    description: "Cada NE de cada ATA: Processo SEI, etapa, valor e números.",
    period: true,
  },
  {
    key: "posicao-saldo",
    name: "Posição de saldo consolidada",
    description: "O saldo de cada ATA: contratado, reservado, empenhado e o que resta.",
    // AC-0009-09: a saldo over part of the NEs would read as the ATA's.
    period: false,
  },
  {
    key: "notas-fiscais-em-conferencia",
    name: "Notas fiscais em conferência",
    description: "As NFs que esperam conferência, com a NE e a ATA de cada uma.",
    period: true,
  },
  {
    key: "indicadores-fornecedores",
    name: "Indicadores de fornecedores",
    description: "Por fornecedor: ATAs, valor contratado e empenhado, NFs aprovadas e devolvidas.",
    period: true,
  },
];

export const ALL_ATAS = "todas";
// The API serves at most this many ATAs a page; the choice lists the newest.
export const ATAS_TO_CHOOSE = 100;
export const RELATORIOS_DENIED = "Os relatórios são lidos pelo gestor e pelo auditor.";
