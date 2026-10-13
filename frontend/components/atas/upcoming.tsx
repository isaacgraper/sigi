"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertSkeletonRows } from "@/components/atas/skeletons";
import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import { type AlertRow, type DueRow, dueRows, dueText, SOON_DAYS, type Urgency, urgency } from "@/lib/atas";
import { ApiError, unavailable } from "@/lib/errors";
import { formatDay } from "@/lib/format";
import { apiJson } from "@/lib/session";
import { cn } from "@/lib/utils";

const KIND = { vencimento: "Vencimento", reajuste: "Reajuste" } as const;

// Colour answers "do I act now?" before anything is read: red once past, amber
// when close, nothing when there is time. A bar on the left edge carries it for
// a scanning eye, and the words carry it for anyone who cannot see the colour.
const LOUDNESS: Record<Urgency, { row: string; days: string; kind: string }> = {
  overdue: {
    row: "border-l-danger bg-danger/[0.06] [@media(hover:hover)_and_(pointer:fine)]:hover:bg-danger/10",
    days: "text-danger",
    kind: "text-danger",
  },
  soon: {
    row: "border-l-attention [@media(hover:hover)_and_(pointer:fine)]:hover:bg-muted/50",
    days: "text-attention",
    kind: "text-muted-foreground",
  },
  later: {
    row: "border-l-transparent [@media(hover:hover)_and_(pointer:fine)]:hover:bg-muted/50",
    days: "text-foreground",
    kind: "text-muted-foreground",
  },
};

// The block sits above the ATA list; past a handful it would push the list off
// the screen, and the rest are by definition less urgent.
const FIRST = 5;

/** The days as the row's figure: the number large, its unit small. */
function Days({ remaining }: { remaining: number }) {
  const overdue = remaining < 0;
  const n = Math.abs(remaining);
  return (
    <span className={cn("flex items-baseline gap-1 tabular-nums", LOUDNESS[urgency(remaining)].days)}>
      <span className="sr-only">{dueText(remaining)}</span>
      <span aria-hidden className="flex items-baseline gap-1">
        {remaining === 0 ? (
          <span className="text-base font-normal">hoje</span>
        ) : (
          <>
            {overdue && <span className="text-xs font-light">há</span>}
            <span className="text-2xl font-normal leading-none">{n}</span>
            <span className="text-xs font-light">{n === 1 ? "dia" : "dias"}</span>
          </>
        )}
      </span>
    </span>
  );
}

function Row({ row }: { row: DueRow }) {
  const level = urgency(row.remaining);
  return (
    <li data-testid="due-row" data-kind={row.kind} data-urgency={level}>
      <Link
        href={`/atas/${row.ata.id}`}
        className={cn(
          "grid grid-cols-[5.5rem_minmax(0,1fr)] items-center gap-x-4 gap-y-0.5 border-l-4 py-3 pl-4 pr-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:grid-cols-[5.5rem_11.5rem_minmax(0,1fr)_auto]",
          LOUDNESS[level].row,
        )}
      >
        <span className="row-span-2 sm:row-span-1">
          <Days remaining={row.remaining} />
        </span>
        <span className={cn("whitespace-nowrap text-xs font-normal uppercase tracking-wide", LOUDNESS[level].kind)}>
          {KIND[row.kind]}
          {level === "overdue" && " · em atraso"}
        </span>
        <span className="min-w-0 truncate text-sm">
          <span className="font-normal">{row.ata.number}</span>
          <span className="font-light text-muted-foreground"> · {row.ata.subject}</span>
        </span>
        <span className="hidden text-sm tabular-nums text-muted-foreground sm:block">{formatDay(row.date)}</span>
      </Link>
    </li>
  );
}

/** The answer before any row is read: how many are late, how many are close. */
function Tally({ rows }: { rows: DueRow[] }) {
  const late = rows.filter((row) => urgency(row.remaining) === "overdue").length;
  const soon = rows.filter((row) => urgency(row.remaining) === "soon").length;
  if (late === 0 && soon === 0) return null;
  return (
    <p data-testid="due-tally" className="flex flex-wrap gap-x-4 text-sm">
      {late > 0 && (
        <span className="inline-flex items-center gap-1.5 text-danger">
          <span aria-hidden className="size-1.5 rounded-full bg-danger" />
          {late} em atraso
        </span>
      )}
      {soon > 0 && (
        <span className="inline-flex items-center gap-1.5 text-attention">
          <span aria-hidden className="size-1.5 rounded-full bg-attention" />
          {soon} em até {SOON_DAYS} dias
        </span>
      )}
    </p>
  );
}

/**
 * "Vencimentos e reajustes" (AC-0013-02): both alerts as one list, the most
 * urgent first. Which ATA belongs in an alert is SPEC-0002's rule, never this
 * screen's.
 */
export function Upcoming() {
  const { handleSessionError } = useSession();
  const [rows, setRows] = useState<DueRow[] | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiJson<AlertRow[]>("/api/v1/atas/alertas/renovacao"),
      apiJson<AlertRow[]>("/api/v1/atas/alertas/reajuste"),
    ])
      .then(([renovacao, reajuste]) => !cancelled && setRows(dueRows(renovacao, reajuste)))
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setFailure(err instanceof ApiError ? err : unavailable());
      });
    return () => {
      cancelled = true;
    };
  }, [handleSessionError]);

  // Nothing due is good news, said in one quiet line rather than an empty card.
  if (rows && rows.length === 0) {
    return (
      <p data-testid="due-list" className="text-sm font-light text-muted-foreground">
        Nenhum vencimento ou reajuste próximo.
      </p>
    );
  }

  return (
    <section
      aria-labelledby="due-title"
      data-testid="due-list"
      className="overflow-hidden rounded-lg border border-border/70 bg-card shadow-sm"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b px-5 py-3">
        <h2 id="due-title" className="text-base font-normal">
          Vencimentos e reajustes
        </h2>
        {rows && <Tally rows={rows} />}
      </div>
      {failure && (
        <div className="p-5">
          <ErrorNotice error={failure} />
        </div>
      )}
      {!rows && !failure && (
        <div role="status" className="space-y-3 p-5">
          <span className="sr-only">Carregando...</span>
          <AlertSkeletonRows />
        </div>
      )}
      {rows && (
        <ul id="due-rows" className="divide-y">
          {(all ? rows : rows.slice(0, FIRST)).map((row) => (
            <Row key={`${row.kind}-${row.ata.id}`} row={row} />
          ))}
        </ul>
      )}
      {rows && rows.length > FIRST && (
        <div className="border-t px-5 py-2.5">
          <Button
            variant="link"
            size="sm"
            className="h-auto px-0"
            aria-expanded={all}
            aria-controls="due-rows"
            onClick={() => setAll((value) => !value)}
          >
            {all ? "Mostrar menos" : `Mostrar todos (${rows.length})`}
          </Button>
        </div>
      )}
    </section>
  );
}
