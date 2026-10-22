"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertSkeletonRows } from "@/components/atas/skeletons";
import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import { cached } from "@/lib/api-cache";
import {
  DUE_KIND_LABEL,
  DUE_LIST_FIRST,
  REAJUSTE_PATH,
  RENOVACAO_PATH,
  SOON_DAYS,
  URGENCY_CLASSES,
} from "@/lib/atas/constants";
import { dueRows, dueText } from "@/lib/atas/due";
import { urgency } from "@/lib/atas/status";
import type { AlertRow, DueRow } from "@/lib/atas/types";
import { ApiError, unavailable } from "@/lib/errors";
import { formatDay } from "@/lib/format";
import { apiJson, warm } from "@/lib/session";
import { cn } from "@/lib/utils";

/** The days as the row's figure: the number large, its unit small. */
function Days({ remaining }: { remaining: number }) {
  const overdue = remaining < 0;
  const n = Math.abs(remaining);
  return (
    <span
      className={cn("flex items-baseline gap-1 whitespace-nowrap tabular-nums", URGENCY_CLASSES[urgency(remaining)].days)}
    >
      <span className="sr-only">{dueText(remaining)}</span>
      <span aria-hidden className="flex items-baseline gap-1">
        {remaining === 0 ? (
          <span className="text-base font-normal">hoje</span>
        ) : (
          <>
            {overdue && <span className="text-xs font-light">há</span>}
            <span className="text-xl font-normal leading-none sm:text-2xl">{n}</span>
            <span className="text-xs font-light">{n === 1 ? "dia" : "dias"}</span>
          </>
        )}
      </span>
    </span>
  );
}

// The first column fits "há 9999 dias": an ATA left vigente years past its end
// is rare but real, and its figure must never run into the kind beside it. On a
// phone the kind wraps instead, so the column can stay narrower.
function Row({ row }: { row: DueRow }) {
  const level = urgency(row.remaining);
  return (
    <li data-testid="due-row" data-kind={row.kind} data-urgency={level}>
      <Link
        href={`/atas/${row.ata.id}`}
        onPointerEnter={() => warm(`/api/v1/atas/${row.ata.id}`)}
        onFocus={() => warm(`/api/v1/atas/${row.ata.id}`)}
        className={cn(
          "grid grid-cols-[6.75rem_minmax(0,1fr)] items-center gap-x-4 sm:gap-x-5 gap-y-0.5 border-l-4 py-3 pl-4 pr-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:grid-cols-[8.5rem_11.5rem_minmax(0,1fr)_auto]",
          URGENCY_CLASSES[level].row,
        )}
      >
        <span className="row-span-2 sm:row-span-1">
          <Days remaining={row.remaining} />
        </span>
        <span
          className={cn("text-xs font-normal uppercase tracking-wide sm:whitespace-nowrap", URGENCY_CLASSES[level].kind)}
        >
          {DUE_KIND_LABEL[row.kind]}
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

/**
 * The answer before any row is read: how many are late, how many are close, in
 * two small cards above the list (AC-0013-02). A zero recedes into muted text.
 */
function Tally({ rows }: { rows: DueRow[] }) {
  const late = rows.filter((row) => urgency(row.remaining) === "overdue").length;
  const soon = rows.filter((row) => urgency(row.remaining) === "soon").length;
  return (
    <div className="grid grid-cols-2 gap-3 sm:flex">
      <TallyCard testId="due-late" label="Em atraso" value={late} tone="danger" />
      <TallyCard testId="due-soon" label={`Em até ${SOON_DAYS} dias`} value={soon} tone="attention" />
    </div>
  );
}

function TallyCard({
  testId,
  label,
  value,
  tone,
}: {
  testId: string;
  label: string;
  value: number;
  tone: "danger" | "attention";
}) {
  const active = value > 0;
  return (
    <div data-testid={testId} className="rounded-lg border border-border/70 bg-card px-4 py-3 shadow-sm sm:min-w-40">
      <p className="flex items-center gap-1.5 text-xs font-light text-muted-foreground">
        {active && (
          <span aria-hidden className={cn("size-1.5 rounded-full", tone === "danger" ? "bg-danger" : "bg-attention")} />
        )}
        {label}
      </p>
      <p
        className={cn(
          "text-2xl font-normal leading-tight tabular-nums",
          active ? (tone === "danger" ? "text-danger" : "text-attention") : "text-muted-foreground",
        )}
      >
        {value}
      </p>
    </div>
  );
}

/**
 * "Vencimentos e reajustes" (AC-0013-02): both alerts as one list, the most
 * urgent first. Which ATA belongs in an alert is SPEC-0002's rule, never this
 * screen's.
 */
export function Upcoming() {
  const { handleSessionError } = useSession();
  // Both alerts seen before draw at once while the new answers come.
  const [rows, setRows] = useState<DueRow[] | null>(() => {
    const renovacao = cached<AlertRow[]>(RENOVACAO_PATH);
    const reajuste = cached<AlertRow[]>(REAJUSTE_PATH);
    return renovacao && reajuste ? dueRows(renovacao, reajuste) : null;
  });
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [all, setAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiJson<AlertRow[]>(RENOVACAO_PATH),
      apiJson<AlertRow[]>(REAJUSTE_PATH),
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
    <div className="space-y-3">
      {rows && <Tally rows={rows} />}
      <section
        aria-labelledby="due-title"
        data-testid="due-list"
        className="overflow-hidden rounded-lg border border-border/70 bg-card shadow-sm"
      >
      <div className="border-b px-5 py-3">
        <h2 id="due-title" className="text-base font-normal">
          Vencimentos e reajustes
        </h2>
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
          {(all ? rows : rows.slice(0, DUE_LIST_FIRST)).map((row) => (
            <Row key={`${row.kind}-${row.ata.id}`} row={row} />
          ))}
        </ul>
      )}
      {rows && rows.length > DUE_LIST_FIRST && (
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
    </div>
  );
}
