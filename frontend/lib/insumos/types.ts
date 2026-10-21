/**
 * The catalogue, its grupos and an ATA's items as SPEC-0003's endpoints return
 * them, and the shapes the screens build around them (SPEC-0014).
 */
import type { Fornecedor, Status as AtaStatus } from "@/lib/atas/types";

export type Situacao = "ativo" | "descontinuado" | "substituido";

export interface GrupoRef {
  id: string;
  name: string;
  level: number;
}

export interface GrupoNode extends GrupoRef {
  parent_id: string | null;
  children: GrupoNode[];
}

/** A grupo of the tree laid flat, in the API's order, with its path from the root. */
export interface GrupoEntry {
  grupo: GrupoNode;
  path: GrupoRef[];
}

export interface Substitute {
  id: string;
  sku: string;
  description: string;
}

export interface Insumo {
  id: string;
  sku: string;
  codigo_doms: string | null;
  external_code: string | null;
  description: string;
  unit: string;
  grupo_id: string;
  grupo_path: GrupoRef[];
  reference_quantity: string | null;
  status: Situacao;
  discontinued_on: string | null;
  substitute: Substitute | null;
  created_at: string;
}

export interface InsumoAta {
  ata_id: string;
  ata_number: string;
  ata_status: AtaStatus;
  item_id: string;
  quantity: string;
  unit_price: string;
}

export interface InsumoDetail extends Insumo {
  atas: InsumoAta[];
}

export interface InsumoPage {
  items: Insumo[];
  total: number;
  page: number;
  size: number;
}

export type InsumoAction = "descontinuar" | "substituir" | "reativar";

// Keys are the API's payload fields, so a refusal's `fields` lands as it comes.
export type InsumoKey =
  | "sku"
  | "description"
  | "unit"
  | "grupo_id"
  | "codigo_doms"
  | "external_code"
  | "reference_quantity";

export interface InsumoField {
  key: InsumoKey;
  label: string;
  optional?: boolean;
  quantity?: boolean;
  mono?: boolean;
  wide?: boolean;
}

export type InsumoValues = Record<InsumoKey, string>;

// ── Items of an ATA ─────────────────────────────────────────────────────────

export interface ItemInsumo {
  id: string;
  sku: string;
  description: string;
  unit: string;
  status: Situacao;
}

export interface Item {
  id: string;
  insumo: ItemInsumo;
  item_number: string | null;
  quantity: string;
  contracted_quantity: string;
  unit_price: string;
  total_value: string;
  fornecedor: Fornecedor;
  own_fornecedor: boolean;
}

export interface Items {
  items: Item[];
  items_value: string;
  total_value: string;
  items_value_differs: boolean;
}

// ── Imports ─────────────────────────────────────────────────────────────────

export interface CatalogueReport {
  created: number;
  updated: number;
  unchanged: number;
  corrected_descriptions: number;
  ignored_columns: string[];
  notes: string[];
  dry_run: boolean;
}

export interface ItemsReport {
  added: number;
  corrected: number;
  unchanged: number;
  ignored_columns: string[];
  dry_run: boolean;
}

export type ImportTarget = "catalogue" | "items";

export interface ImportColumns {
  filename: string;
  required: readonly string[];
  optional: readonly string[];
}

export interface UserGrupos {
  user_id: string;
  grupo_ids: string[];
}
