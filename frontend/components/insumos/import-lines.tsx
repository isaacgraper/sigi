import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatQuantity, formatUnitPrice } from "@/lib/format";
import {
  CATALOGUE_LINE_COLUMNS,
  EMPTY_VALUE,
  ITEMS_LINE_COLUMNS,
  LINE_ACTION_LABEL,
  PREVIEW_LINES,
} from "@/lib/insumos/constants";
import { pathText } from "@/lib/insumos/grupos";
import type { CatalogueReport, ItemsReport } from "@/lib/insumos/types";
import { cn } from "@/lib/utils";

/**
 * The lines of a file as the API read them and will write them (AC-0014-19,
 * -20, SPEC-0003 AC-0003-33): the screen shows the API's reading, it never
 * parses the file itself. The first PREVIEW_LINES only, with how many more.
 */
export function ImportLines({ report }: { report: CatalogueReport | ItemsReport }) {
  const catalogue = "created" in report;
  const columns = catalogue ? CATALOGUE_LINE_COLUMNS : ITEMS_LINE_COLUMNS;
  const shown = report.lines.slice(0, PREVIEW_LINES);
  const more = report.lines.length - shown.length;
  return (
    <div className="space-y-2" data-testid="import-lines">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((name) => (
              <TableHead key={name} className="whitespace-nowrap">
                {name}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {"created" in report
            ? report.lines.slice(0, PREVIEW_LINES).map((line) => (
                <TableRow key={line.line} data-testid="import-line">
                  <TableCell className="tabular-nums text-muted-foreground">{line.line}</TableCell>
                  <TableCell className="whitespace-nowrap font-mono text-xs">{line.sku}</TableCell>
                  <TableCell className="min-w-56">
                    {line.description}
                    {line.corrected_description && (
                      <span className="block text-xs font-light text-muted-foreground">código DOMS retirado da descrição</span>
                    )}
                  </TableCell>
                  <TableCell>{line.unit}</TableCell>
                  <TableCell className="min-w-40 text-muted-foreground">{pathText(line.grupo_path)}</TableCell>
                  <TableCell className="whitespace-nowrap font-mono text-xs">{line.codigo_doms ?? EMPTY_VALUE}</TableCell>
                  <ActionCell action={line.action} />
                </TableRow>
              ))
            : report.lines.slice(0, PREVIEW_LINES).map((line) => (
                <TableRow key={line.line} data-testid="import-line">
                  <TableCell className="tabular-nums text-muted-foreground">{line.line}</TableCell>
                  <TableCell className="whitespace-nowrap font-mono text-xs">{line.sku}</TableCell>
                  <TableCell className="min-w-56">{line.description}</TableCell>
                  <TableCell className="whitespace-nowrap text-right tabular-nums">{formatQuantity(line.quantity)}</TableCell>
                  <TableCell className="whitespace-nowrap text-right tabular-nums">{formatUnitPrice(line.unit_price)}</TableCell>
                  <TableCell className="tabular-nums">{line.item_number ?? ""}</TableCell>
                  <TableCell className="min-w-40">{line.fornecedor ?? ""}</TableCell>
                  <ActionCell action={line.action} />
                </TableRow>
              ))}
        </TableBody>
      </Table>
      {more > 0 && (
        <p className="text-sm font-light text-muted-foreground">
          Mostrando {shown.length} de {report.lines.length} linhas.
        </p>
      )}
    </div>
  );
}

function ActionCell({ action }: { action: string }) {
  return (
    <TableCell className={cn("whitespace-nowrap", action === "unchanged" && "text-muted-foreground")}>
      {LINE_ACTION_LABEL[action] ?? action}
    </TableCell>
  );
}
