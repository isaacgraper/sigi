import { ChevronDown } from "lucide-react";
import { useId } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ChartBlock, Filter, NoteBlock, StatBlock, TableBlock } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

/**
 * Every block of the dashboard reads this until its source exists (AC-0012-04).
 * The words are the stakeholders': an empty block is not an error.
 */
export function NoData({ className }: { className?: string }) {
  return (
    <p data-testid="sem-dados" className={cn("text-sm font-light text-muted-foreground", className)}>
      Sem dados
    </p>
  );
}

/** A single figure, or a short text block, labelled above (DESIGN.md "Stat tile"). */
export function TileView({ block }: { block: StatBlock | NoteBlock }) {
  return (
    <Card data-testid="dashboard-block" className="flex min-w-0 flex-col gap-1.5 px-4 py-3">
      <h2 className="text-xs font-normal tracking-wide text-muted-foreground uppercase">{block.title}</h2>
      <NoData />
    </Card>
  );
}

export function TableView({ block }: { block: TableBlock }) {
  return (
    <section data-testid="dashboard-block" className="min-w-0 space-y-2">
      <h2 className="text-base font-normal">{block.title}</h2>
      <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
        {/* Only the header row scrolls sideways, and it can be scrolled from the
            keyboard; "Sem dados" sits below it, so it stays in view on a phone. */}
        <div
          role="region"
          aria-label={`Tabela ${block.title}`}
          tabIndex={0}
          className="overflow-x-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
        >
          <table className="w-full text-sm">
            <TableHeader>
              <TableRow className="border-b-0 hover:bg-transparent">
                {block.columns.map((column) => (
                  <TableHead key={column} className="whitespace-nowrap">
                    {column}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
          </table>
        </div>
        <div className="border-t px-4 py-10 text-center">
          <NoData />
        </div>
      </div>
    </section>
  );
}

export function ChartView({ block, className }: { block: ChartBlock; className?: string }) {
  return (
    <Card data-testid="dashboard-block" className={cn("flex min-w-0 flex-col", className)}>
      <CardHeader className="gap-3 pb-3">
        <CardTitle>{block.title}</CardTitle>
        {/* The legend is text, so the chart says what it will show before it has data. */}
        <ul aria-label="Legenda" className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {block.series.map((name) => (
            <li key={name} className="flex items-center gap-1.5">
              <span aria-hidden className="size-2 rounded-full bg-muted-foreground/40" />
              {name}
            </li>
          ))}
        </ul>
      </CardHeader>
      <CardContent className="flex flex-1">
        <div className="flex min-h-48 flex-1 items-center justify-center rounded-md border border-dashed bg-muted/30">
          <NoData />
        </div>
      </CardContent>
    </Card>
  );
}

function FilterControl({ filter }: { filter: Filter }) {
  const id = useId();
  if (filter.kind === "checklist") {
    return (
      <fieldset className="min-w-0 space-y-1.5">
        <legend className="mb-1.5 text-sm font-normal">{filter.label}</legend>
        {filter.options.map((option) => (
          <label key={option} className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="size-4 accent-primary" />
              {option}
            </span>
            <span className="tabular-nums">
              <span className="sr-only">Quantidade: </span>—
            </span>
          </label>
        ))}
      </fieldset>
    );
  }
  return (
    <div className="min-w-0 space-y-1.5">
      <label htmlFor={id} className="text-sm font-normal">
        {filter.label}
      </label>
      {filter.kind === "search" ? (
        <Input id={id} type="search" placeholder="Insira um valor" />
      ) : (
        // A select with nothing to choose from yet, styled as the select it will be.
        <button
          id={id}
          type="button"
          className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-card px-3 text-sm text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
        >
          Todos
          <ChevronDown aria-hidden className="size-4 opacity-60" />
        </button>
      )}
    </div>
  );
}

/**
 * The report's filters, in its order. They stay disabled while the section has
 * no data (AC-0012-04): a filter over nothing would only suggest a broken page.
 */
export function FilterPanel({ filters, className }: { filters: Filter[]; className?: string }) {
  return (
    <Card data-testid="dashboard-filters" className={cn("p-4", className)}>
      <fieldset disabled className="space-y-4">
        <legend className="sr-only">Filtros</legend>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(10rem,1fr))]">
          {filters.map((filter) => (
            <FilterControl key={filter.label} filter={filter} />
          ))}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-light text-muted-foreground">
            Os filtros ficam disponíveis quando houver dados.
          </p>
          <Button type="button" variant="outline" size="sm">
            Limpar filtros
          </Button>
        </div>
      </fieldset>
    </Card>
  );
}
