"use client";

import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Figure, NeStage } from "@/components/notas-empenho/stage";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FILTER_ALL } from "@/lib/constants";
import { formatBRL, formatDate } from "@/lib/format";
import { LIST_COLUMNS, NE_PAGE_SIZE, NE_STATUSES, STAGE_LABEL } from "@/lib/notas-empenho/constants";
import type { Indicators, NePage, NeStatus } from "@/lib/notas-empenho/types";
import { warm } from "@/lib/session";
import { useRead } from "@/lib/use-read";

function OpenLink({ variant = "default" }: { variant?: "default" | "outline" }) {
  return (
    <Link href="/notas-empenho/nova" className={buttonVariants({ variant })}>
      <Plus aria-hidden />
      Abrir NE
    </Link>
  );
}

function hrefFor(etapa: NeStatus | null, page: number): string {
  const params = new URLSearchParams();
  if (etapa) params.set("etapa", etapa);
  if (page > 1) params.set("pagina", String(page));
  const query = params.toString();
  return query ? `/notas-empenho?${query}` : "/notas-empenho";
}

/** /notas-empenho: the counters, the filter by etapa and the list (AC-0015-01, -02). */
export function NotasEmpenho() {
  const { me } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("etapa");
  const etapa = NE_STATUSES.includes(raw as NeStatus) ? (raw as NeStatus) : null;
  const page = Math.max(1, Number.parseInt(params.get("pagina") ?? "1", 10) || 1);
  // Hiding the write is cosmetic; the API refuses it (invariant 8).
  const opens = me.perfil === "gestor";

  const query = new URLSearchParams({ page: String(page), size: String(NE_PAGE_SIZE) });
  if (etapa) query.set("etapa", etapa);
  const list = useRead<NePage>(`/api/v1/notas-empenho?${query}`);
  const counters = useRead<Indicators>("/api/v1/notas-empenho/indicadores");
  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notas de empenho"
        description="Da demanda à NE emitida, uma etapa por vez, com o saldo da ATA reservado no pré-empenho."
        action={opens ? <OpenLink /> : undefined}
      />

      <div className="grid grid-cols-3 gap-3 sm:flex">
        <Figure testId="ne-emitidas" label="Emitidas" value={counters.data?.emitidas ?? "—"} />
        <Figure testId="ne-em-andamento" label="Em andamento" value={counters.data?.em_andamento ?? "—"} />
        <Figure testId="ne-total" label="Total" value={counters.data?.total ?? "—"} />
      </div>

      <section aria-label="Lista de NEs" className="space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-full space-y-2 sm:w-56">
            <Label htmlFor="filtro-etapa">Etapa</Label>
            <Select
              value={etapa ?? FILTER_ALL}
              onValueChange={(value) => router.push(hrefFor(value === FILTER_ALL ? null : (value as NeStatus), 1))}
            >
              <SelectTrigger id="filtro-etapa">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={FILTER_ALL}>Todas</SelectItem>
                {NE_STATUSES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {STAGE_LABEL[value]}
                  </SelectItem>
                ))}
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
                  {LIST_COLUMNS.map((name) => (
                    <TableHead key={name} className={name === "Valor" ? "whitespace-nowrap text-right" : "whitespace-nowrap"}>
                      {name}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={LIST_COLUMNS.length}>
                      <EmptyState
                        message={etapa ? "Nenhuma NE nesta etapa." : "Nenhuma NE aberta."}
                        action={!etapa && opens ? <OpenLink variant="outline" /> : undefined}
                      />
                    </TableCell>
                  </TableRow>
                )}
                {data.items.map((ne) => (
                  <TableRow key={ne.id} data-testid="ne-row" data-ne-id={ne.id}>
                    <TableCell className="whitespace-nowrap">
                      <Link
                        href={`/notas-empenho/${ne.id}`}
                        onPointerEnter={() => warm(`/api/v1/notas-empenho/${ne.id}`)}
                        onFocus={() => warm(`/api/v1/notas-empenho/${ne.id}`)}
                        className="text-primary underline-offset-4 tabular-nums focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                      >
                        {ne.processo_sei}
                      </Link>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{ne.ata_number}</TableCell>
                    <TableCell>
                      <NeStage status={ne.status} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">{formatBRL(ne.value)}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{ne.numero_pre_empenho ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{ne.number ?? "—"}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{formatDate(ne.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">
                Página {page} de {lastPage} · {data.total} {data.total === 1 ? "NE" : "NEs"}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => router.push(hrefFor(etapa, page - 1))}>
                  <ChevronLeft aria-hidden />
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= lastPage}
                  onClick={() => router.push(hrefFor(etapa, page + 1))}
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
