"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { AlertSkeletonRows } from "@/components/atas/skeletons";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type AlertRow, daysText } from "@/lib/atas";
import { ApiError, unavailable } from "@/lib/errors";
import { apiJson } from "@/lib/session";

const ALERTS = {
  renovacao: { title: "ATAs a renovar", path: "/api/v1/atas/alertas/renovacao" },
  reajuste: { title: "Reajuste a solicitar", path: "/api/v1/atas/alertas/reajuste" },
} as const;

/**
 * One alert as the API answers it (AC-0013-02): its rows in the API's order.
 * Which ATA belongs in it is SPEC-0002's rule, never this screen's.
 */
function AlertCard({ kind }: { kind: keyof typeof ALERTS }) {
  const { handleSessionError } = useSession();
  const [rows, setRows] = useState<AlertRow[] | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const { title, path } = ALERTS[kind];

  useEffect(() => {
    let cancelled = false;
    apiJson<AlertRow[]>(path)
      .then((value) => !cancelled && setRows(value))
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setFailure(err instanceof ApiError ? err : unavailable());
      });
    return () => {
      cancelled = true;
    };
  }, [path, handleSessionError]);

  return (
    <Card data-testid={`alerta-${kind}`} className="min-w-0">
      <CardHeader className="pb-3">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {failure && <ErrorNotice error={failure} />}
        {!rows && !failure && (
          <div role="status" className="space-y-3">
            <span className="sr-only">Carregando...</span>
            <AlertSkeletonRows />
          </div>
        )}
        {rows && rows.length === 0 && (
          <p className="text-sm font-light text-muted-foreground">Nenhuma ATA neste alerta.</p>
        )}
        {rows && rows.length > 0 && (
          <ul className="divide-y">
            {rows.map(({ ata, days_remaining }) => (
              <li key={ata.id} data-testid="alerta-row">
                <Link
                  href={`/atas/${ata.id}`}
                  className="flex items-baseline justify-between gap-4 py-2.5 text-sm focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:hover)_and_(pointer:fine)]:hover:text-primary"
                >
                  <span className="min-w-0 truncate">
                    <span className="font-normal">{ata.number}</span>
                    <span className="font-light text-muted-foreground"> · {ata.subject}</span>
                  </span>
                  <span
                    className={
                      days_remaining < 0 ? "shrink-0 tabular-nums text-danger" : "shrink-0 tabular-nums text-attention"
                    }
                  >
                    {daysText(kind, days_remaining)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function AtaAlerts() {
  return (
    <section aria-label="Alertas" className="grid gap-6 md:grid-cols-2">
      <AlertCard kind="renovacao" />
      <AlertCard kind="reajuste" />
    </section>
  );
}
