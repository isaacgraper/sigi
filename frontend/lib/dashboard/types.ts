/** The shapes of the CAME report's tabs and blocks (SPEC-0012). */

export type Filter =
  | { kind: "select"; label: string }
  | { kind: "search"; label: string }
  | { kind: "checklist"; label: string; options: string[] };

export interface StatBlock {
  kind: "stat";
  title: string;
}

export interface TableBlock {
  kind: "table";
  title: string;
  columns: string[];
}

export interface ChartBlock {
  kind: "chart";
  title: string;
  /** Named in the legend, so the chart's meaning is readable before it has data. */
  series: string[];
}

export interface NoteBlock {
  kind: "note";
  title: string;
}

export type Block = StatBlock | TableBlock | ChartBlock | NoteBlock;

/** The answer of GET /api/v1/painel/{section} (SPEC-0012 §7). */
export interface PainelOut {
  section: string;
  blocks: Record<string, { rows: string[][] }>;
}

export interface Section {
  /** The `?aba=` value (AC-0012-03). */
  id: string;
  title: string;
  description: string;
  filters: Filter[];
  /** Every block; the section's own layout decides where each one sits. */
  blocks: Record<string, Block>;
}
