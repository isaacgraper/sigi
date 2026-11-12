import { IMPORT_COLUMNS, REPORT_LABEL, TEMPLATE_SEPARATOR } from "@/lib/insumos/constants";
import type { CatalogueReport, ImportTarget, ItemsReport } from "@/lib/insumos/types";

/** The model file's content: the header line, required columns first (AC-0014-18, -20). */
export function templateCsv(target: ImportTarget): string {
  const { required, optional } = IMPORT_COLUMNS[target];
  return `${[...required, ...optional].join(TEMPLATE_SEPARATOR)}\r\n`;
}

/** The counts a report states, labelled for a check or for the import done (AC-0014-19, -20). */
export function reportCounts(report: CatalogueReport | ItemsReport): { label: string; value: number }[] {
  const keys =
    "created" in report
      ? (["created", "updated", "unchanged", "corrected_descriptions"] as const)
      : (["added", "corrected", "unchanged"] as const);
  const when = report.dry_run ? "check" : "done";
  return keys.map((key) => ({
    label: REPORT_LABEL[key][when],
    value: (report as unknown as Record<string, number>)[key],
  }));
}
