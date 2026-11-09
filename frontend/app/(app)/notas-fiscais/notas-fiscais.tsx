"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { NfStatusBadge } from "@/components/notas-fiscais/status";
import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FILTER_ALL } from "@/lib/constants";
import { formatBRL, formatDay } from "@/lib/format";
import {
  FILTER_QUARENTENA,
  NF_LIST_COLUMNS,
  NF_PAGE_SIZE,
  NF_STATUS_LABEL,
  NF_STATUSES,
  QUARENTENA_LABEL,
} from "@/lib/notas-fiscais/constants";
import type { NfPage, NfStatus } from "@/lib/notas-fiscais/types";
import { warm } from "@/lib/session";
import { useRead } from "@/lib/use-read";

type Filter = NfStatus | typeof FILTER_QUARENTENA;

function hrefFor(filter: Filter | null, page: number): string {
  const params = new URLSearchParams();
  if (filter) params.set("status", filter);
  if (page > 1) params.set("pagina", String(page));
  const query = params.toString();
  return query ? `/notas-fiscais?${query}` : "/notas-fiscais";
}

/** /notas-fiscais: the NFs, filtered by status or by the quarantine (AC-0016-01, -02). */
export function NotasFiscais() {
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("status");
  const filter: Filter | null =
    raw === FILTER_QUARENTENA || NF_STATUSES.includes(raw as NfStatus) ? (raw as Filter) : null;
  const page = Math.max(1, Number.parseInt(params.get("pagina") ?? "1", 10) || 1);

  const query = new URLSearchParams({ page: String(page), size: String(NF_PAGE_SIZE) });
  if (filter === FILTER_QUARENTENA) query.set("quarentena", "true");
  else if (filter) query.set("status", filter);
  const list = useRead<NfPage>(`/api/v1/notas-fiscais?${query}`);
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notas fiscais"
        description="O que cada NE recebeu, da conferência à aprovação. Registre uma NF a partir da página da NE emitida."
      />

      <section aria-label="Lista de NFs" className="space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-full space-y-2 sm:w-56">
            <Label htmlFor="filtro-status">Status</Label>
            <Select
              value={filter ?? FILTER_ALL}
              onValueChange={(value) => router.push(hrefFor(value === FILTER_ALL ? null : (value as Filter), 1))}
            >
              <SelectTrigger id="filtro-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={FILTER_ALL}>Todas</SelectItem>
                {NF_STATUSES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {NF_STATUS_LABEL[value]}
                  </SelectItem>
                ))}
                <SelectItem value={FILTER_QUARENTENA}>{QUARENTENA_LABEL}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {list.failure && !data && <ErrorNotice error={list.failure} />}
        {!data && !list.failure && (
          <div role="status">
            <span className="sr-only">Carregando...</span>
            <TableSkeleton />
          </div>
        )}

        {data && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  {NF_LIST_COLUMNS.map((name) => (
                    <TableHead key={name} className={name === "Valor" ? "whitespace-nowrap text-right" : "whitespace-nowrap"}>
                      {name}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={NF_LIST_COLUMNS.length}>
                      <EmptyState message={filter ? "Nenhuma NF neste filtro." : "Nenhuma NF registrada."} />
                    </TableCell>
                  </TableRow>
                )}
                {data.items.map((nf) => (
                  <TableRow key={nf.id} data-testid="nf-row" data-nf-id={nf.id}>
                    <TableCell className="whitespace-nowrap">
                      <Link
                        href={`/notas-fiscais/${nf.id}`}
                        onPointerEnter={() => warm(`/api/v1/notas-fiscais/${nf.id}`)}
                        onFocus={() => warm(`/api/v1/notas-fiscais/${nf.id}`)}
                        className="text-primary underline-offset-4 tabular-nums focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                      >
                        {nf.numero}
                      </Link>
                    </TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{nf.nota_empenho_number ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{formatDay(nf.data_emissao)}</TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">{formatBRL(nf.valor)}</TableCell>
                    <TableCell>
                      <NfStatusBadge status={nf.status} quarentena={nf.quarentena} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">
                Página {page} de {lastPage} · {data.total} {data.total === 1 ? "NF" : "NFs"}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => router.push(hrefFor(filter, page - 1))}>
                  <ChevronLeft aria-hidden />
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= lastPage}
                  onClick={() => router.push(hrefFor(filter, page + 1))}
                >
                  Próxima
                  <ChevronRight aria-hidden />
                </Button>
              </div>
            </nav>
          </>
        )}
      </section>
    </div>
  );
}
