/** What the insumo screens read (SPEC-0014). Shared values live in lib/constants.ts. */
import type {
  ImportColumns,
  ImportTarget,
  InsumoAction,
  InsumoField,
  InsumoKey,
  InsumoValues,
  Situacao,
} from "@/lib/insumos/types";

// ── Situação ────────────────────────────────────────────────────────────────

export const SITUACOES: Situacao[] = ["ativo", "descontinuado", "substituido"];

export const SITUACAO_LABEL: Record<Situacao, string> = {
  ativo: "Ativo",
  descontinuado: "Descontinuado",
  substituido: "Substituído",
};

// ── Catalogue ───────────────────────────────────────────────────────────────

// Mirrors AC-0014-02.
export const INSUMOS_PAGE_SIZE = 25;

// A word typed is one request, not one per letter (AC-0014-02).
export const SEARCH_DELAY_MS = 300;

// How many insumos a dialog's search offers at once (AC-0014-15, -23).
export const PICKER_SIZE = 10;

export const LIST_COLUMNS = ["SKU", "Descrição", "Unidade", "Grupo", "Código DOMS", "Situação"];

/** Between the grupos of a path: "MATERIAL ODONTOLÓGICO › RESTAURADORES". */
export const PATH_SEPARATOR = " › ";

export const INSUMO_NOT_FOUND = "Insumo não encontrado.";

/** An optional field with no value (AC-0014-12). */
export const EMPTY_VALUE = "—";

// ── Registration and edit form ──────────────────────────────────────────────

export const INSUMO_FIELDS: InsumoField[] = [
  { key: "sku", label: "SKU", mono: true },
  { key: "unit", label: "Unidade" },
  { key: "description", label: "Descrição", wide: true },
  { key: "grupo_id", label: "Grupo", wide: true },
  { key: "codigo_doms", label: "Código DOMS (opcional)", optional: true, mono: true },
  { key: "external_code", label: "Código externo (opcional)", optional: true, mono: true },
  { key: "reference_quantity", label: "Quantidade de referência (opcional)", optional: true, quantity: true },
];

/** The order errors are focused in: the order the fields are read in. */
export const INSUMO_ORDER: InsumoKey[] = INSUMO_FIELDS.map((field) => field.key);

export const INSUMO_EMPTY = Object.fromEntries(INSUMO_ORDER.map((key) => [key, ""])) as InsumoValues;

// Optional fields an edit sends as null when emptied, which clears them (AC-0014-10).
export const CLEARABLE: InsumoKey[] = ["codigo_doms", "external_code", "reference_quantity"];

// Refusals that name no field in `fields` but belong to one (SPEC-0003 §3.9).
export const INSUMO_CODE_FIELD: Record<string, InsumoKey> = {
  INVALID_SKU: "sku",
  INVALID_DOMS_CODE: "codigo_doms",
  INSUMO_DUPLICADO: "sku",
};

// ── Gestor actions on an insumo ─────────────────────────────────────────────

/**
 * The actions offered per situação. It mirrors AC-0003-14 to -16 so a gestor
 * is not shown a button that can only fail; the API stays the authority.
 */
export const ACTIONS: Record<Situacao, InsumoAction[]> = {
  ativo: ["descontinuar", "substituir"],
  descontinuado: ["reativar"],
  substituido: ["reativar"],
};

export const ACTION: Record<
  InsumoAction,
  { label: string; title: string; body: string; done: string; destructive: boolean }
> = {
  descontinuar: {
    label: "Descontinuar",
    title: "Descontinuar insumo?",
    body: "O insumo deixa de entrar em itens novos. As ATAs que já o têm continuam com ele.",
    done: "Insumo descontinuado.",
    destructive: true,
  },
  substituir: {
    label: "Substituir",
    title: "Substituir insumo",
    body: "O insumo deixa de entrar em itens novos e passa a apontar para o substituto. As ATAs e notas antigas continuam com ele.",
    done: "Insumo substituído.",
    destructive: false,
  },
  reativar: {
    label: "Reativar",
    title: "Reativar insumo?",
    body: "O insumo volta a ativo e pode entrar em itens novos.",
    done: "Insumo reativado.",
    destructive: false,
  },
};

export const SKU_ORDER = ["sku", "justification"];
export const ACTION_ORDER = ["substitute_id", "justification"];

export const SKU_CODE_FIELD: Record<string, string> = { INVALID_SKU: "sku", INSUMO_DUPLICADO: "sku" };
export const SUBSTITUTE_CODE_FIELD: Record<string, string> = { INVALID_SUBSTITUTE: "substitute_id" };

// ── Grupos ──────────────────────────────────────────────────────────────────

// Mirrors AC-0003-09: Grupo mercadoria, SubGrupo, Classificação.
export const GRUPO_MAX_LEVEL = 3;

export const GRUPO_ORDER = ["name"];
export const GRUPO_CODE_FIELD: Record<string, string> = { DUPLICATE_GROUP: "name" };

// The member dialog names no field of its own (AC-0014-28).
export const GRUPOS_ORDER: string[] = [];

// ── Imports ─────────────────────────────────────────────────────────────────

// The columns of SPEC-0003 AC-0003-06 and -26, in the order the model file has them.
export const IMPORT_COLUMNS: Record<ImportTarget, ImportColumns> = {
  catalogue: {
    filename: "modelo-catalogo.csv",
    required: ["sku", "descricao", "unidade", "grupo"],
    optional: ["subgrupo", "classificacao", "codigo_doms", "codigo_externo", "quantidade_referencia"],
  },
  items: {
    filename: "modelo-itens-ata.csv",
    required: ["sku", "quantidade", "valor_unitario"],
    optional: ["numero_item", "cnpj_fornecedor", "razao_social_fornecedor"],
  },
};

// The separator of a pt-BR spreadsheet, so the model opens in columns in Excel (AC-0003-18).
export const TEMPLATE_SEPARATOR = ";";

export const IMPORT_ACCEPT = ".csv,text/csv";

// Mirrors AC-0003-18: a file the API would refuse is not sent (AC-0014-18).
export const IMPORT_MAX_BYTES = 5 * 1024 * 1024;
export const IMPORT_TOO_LARGE = "O arquivo passa de 5 MB.";
export const IMPORT_NOT_CSV = "Escolha um arquivo .csv.";

// The table shows this many lines and says how many more there are, so a
// 10.000 line file does not weigh down the page (AC-0014-19).
export const PREVIEW_LINES = 100;

export const LINE_ACTION_LABEL: Record<string, string> = {
  created: "Novo",
  added: "Novo",
  updated: "Atualizado",
  corrected: "Corrigido",
  unchanged: "Sem alteração",
};

export const CATALOGUE_LINE_COLUMNS = ["Linha", "SKU", "Descrição", "Unidade", "Grupo", "Código DOMS", "Ação"];
export const ITEMS_LINE_COLUMNS = [
  "Linha",
  "SKU",
  "Descrição",
  "Quantidade",
  "Valor unitário",
  "Nº",
  "Fornecedor",
  "Ação",
];

/** Each count of a report, as the check (`dry_run`) and the import word it (AC-0014-19, -20). */
export const REPORT_LABEL = {
  created: { check: "Serão criados", done: "Criados" },
  updated: { check: "Serão atualizados", done: "Atualizados" },
  added: { check: "Serão adicionados", done: "Adicionados" },
  corrected: { check: "Serão corrigidos", done: "Corrigidos" },
  unchanged: { check: "Sem alteração", done: "Sem alteração" },
  corrected_descriptions: { check: "Descrições a corrigir", done: "Descrições corrigidas" },
} as const;

// ── Items of an ATA ─────────────────────────────────────────────────────────

export const ITEM_COLUMNS = [
  "Nº",
  "SKU",
  "Descrição",
  "Unidade",
  "Quantidade",
  "Valor unitário",
  "Valor total",
  "Fornecedor",
];

/** Right-aligned, because they are figures. */
export const ITEM_FIGURES = new Set(["Quantidade", "Valor unitário", "Valor total"]);

export const ITEM_ORDER = [
  "insumo_id",
  "quantity",
  "unit_price",
  "item_number",
  "fornecedor.cnpj",
  "fornecedor.legal_name",
];

export const ITEM_CODE_FIELD: Record<string, string> = {
  ITEM_ATA_DUPLICADO: "insumo_id",
  INSUMO_DESCONTINUADO: "insumo_id",
  ADITIVO_ACIMA_DO_LIMITE: "quantity",
};

// A removal names no field; the order is empty so nothing is focused.
export const REMOVE_ORDER: string[] = [];
export const QUANTITY_ADITIVO_ORDER = ["quantity", "justification"];
export const QUANTITY_ADITIVO_CODE_FIELD: Record<string, string> = { ADITIVO_ACIMA_DO_LIMITE: "quantity" };

// ── Field help (AC-0014-29) ─────────────────────────────────────────────────

export const HELP = {
  sku: "Código do item no CAME, letras e números com ao menos uma letra, sem espaços nem pontos, ex. CLORDEG21. Não pode repetir outro insumo.",
  description: "Nome do item como deve aparecer nas ATAs e nas notas. Sem o código DOMS na frente.",
  unit: "Unidade de dispensação, ex. UN, CX, L.",
  grupo_id: "Grupo de materiais do DOMS. Um servidor só vê os insumos dos seus grupos.",
  codigo_doms: "Código do item no DOMS, só números, ex. 26829. Não pode repetir outro insumo.",
  external_code: "Identificador interno do DOMS (mercadoriaId), usado para cruzar arquivos.",
  reference_quantity: "Quantidade usada como referência para alertas. Não é estoque.",
  new_sku:
    "Novo código do item. As ATAs e notas que usam o insumo continuam ligadas a ele, e o SKU anterior fica no histórico.",
  substitute: "Insumo ativo que passa a ser usado no lugar deste. As ATAs e notas antigas continuam com este.",
  justification: "Por que a mudança foi feita. Fica no histórico.",
  grupo_name: "Nome do grupo, como no DOMS. Não pode repetir outro grupo no mesmo nível.",
  insumo: "Insumo do catálogo. Um insumo descontinuado não entra em itens novos.",
  quantity: "Quantidade registrada na ATA para o item, até 3 casas decimais.",
  unit_price:
    "Preço por unidade como consta na ATA, até 5 casas decimais, ex. 0,00599. O valor do item é arredondado ao centavo.",
  item_number: "Número do item no pregão.",
  cnpj: "Fornecedor deste item, quando não é o da ATA. 14 caracteres, com ou sem pontuação.",
  legal_name: "Nome jurídico do fornecedor deste item.",
  added_quantity:
    "Quanto o aditivo soma à quantidade do item. Todos os aditivos do item juntos não passam de 25% da quantidade original.",
  file: 'Arquivo em CSV, separado por ";" ou ",", em UTF-8 ou Windows-1252, até 5 MB e 10.000 linhas.',
} as const satisfies Record<string, string> & Partial<Record<InsumoKey, string>>;
