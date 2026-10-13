"use client";

import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { SituacaoBadge, StatusBadge } from "@/components/atas/badges";
import { Upcoming } from "@/components/atas/upcoming";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  type AtaPage,
  SITUACAO_LABEL,
  SITUACOES,
  type Situacao,
  STATUS_LABEL,
  STATUSES,
  type Status,
} from "@/lib/atas";
import { ApiError, unavailable } from "@/lib/errors";
import { formatBRL, formatDay } from "@/lib/format";
import { apiJson } from "@/lib/session";

const SIZE = 25;

function RegisterLink({ variant = "default" }: { variant?: "default" | "outline" }) {
  return (
    <Link href="/atas/nova" className={buttonVariants({ variant })}>
      <Plus aria-hidden />
      Cadastrar ATA
    </Link>
  );
}
const ALL = "todos";
const COLUMNS = ["Número", "Objeto", "Fornecedor", "Vigência", "Valor contratado", "Status", "Situação", "Reajuste em"];

function pageFrom(raw: string | null): number {
  const value = Number.parseInt(raw ?? "1", 10);
  return Number.isFinite(value) && value > 0 ? value : 1;
}

function pick<T extends string>(raw: string | null, allowed: readonly T[]): T | null {
  return allowed.includes(raw as T) ? (raw as T) : null;
}

/** The list's state lives in the URL, so a reload or a shared link keeps it (AC-0013-04). */
function hrefFor(status: Status | null, situacao: Situacao | null, page: number): string {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (situacao) params.set("situacao", situacao);
  if (page > 1) params.set("pagina", String(page));
  const query = params.toString();
  return query ? `/atas?${query}` : "/atas";
}

export function Atas() {
  const { me, handleSessionError } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const status = pick(params.get("status"), STATUSES);
  const situacao = pick(params.get("situacao"), SITUACOES);
  const page = pageFrom(params.get("pagina"));
  const filtered = status !== null || situacao !== null;

  const query = new URLSearchParams({ page: String(page), size: String(SIZE) });
  if (status) query.set("status", status);
  if (situacao) query.set("situacao_vigencia", situacao);
  const path = `/api/v1/atas?${query}`;

  // The answer is kept with the request it answers, so a new filter shows the
  // skeleton until its own answer lands, never the previous filter's rows.
  const [answer, setAnswer] = useState<{ path: string; data?: AtaPage; refusal?: ApiError } | null>(null);
  const current = answer?.path === path ? answer : null;
  const data = current?.data ?? null;
  const refusal = current?.refusal ?? null;
  // Hiding the writes is cosmetic; the API refuses them (AC-0013-07, invariant 8).
  const writes = me.perfil === "gestor";

  useEffect(() => {
    let cancelled = false;
    apiJson<AtaPage>(path)
      .then((value) => !cancelled && setAnswer({ path, data: value }))
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setAnswer({ path, refusal: err instanceof ApiError ? err : unavailable() });
      });
    return () => {
      cancelled = true;
    };
  }, [path, handleSessionError]);

  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="ATAs"
        description="As Atas de Registro de Preços, o que vence e o reajuste a pedir."
        action={writes ? <RegisterLink /> : undefined}
      />

      <Upcoming />

      <section aria-label="Lista de ATAs" className="space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-full space-y-2 sm:w-48">
            <Label htmlFor="filtro-status">Status</Label>
            <Select
              value={status ?? ALL}
              onValueChange={(value) => router.push(hrefFor(value === ALL ? null : (value as Status), situacao, 1))}
            >
              <SelectTrigger id="filtro-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Todos</SelectItem>
                {STATUSES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {STATUS_LABEL[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-full space-y-2 sm:w-48">
            <Label htmlFor="filtro-situacao">Situação</Label>
            <Select
              value={situacao ?? ALL}
              onValueChange={(value) => router.push(hrefFor(status, value === ALL ? null : (value as Situacao), 1))}
            >
              <SelectTrigger id="filtro-situacao">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Todas</SelectItem>
                {SITUACOES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {SITUACAO_LABEL[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {filtered && (
            <Button variant="ghost" onClick={() => router.push("/atas")}>
              Limpar filtros
            </Button>
          )}
        </div>

        {refusal && <ErrorNotice error={refusal} />}

        {!data && !refusal && (
          <div role="status">
            <span className="sr-only">Carregando...</span>
            <TableSkeleton />
          </div>
        )}

        {data && !refusal && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  {COLUMNS.map((name) => (
                    <TableHead key={name} className={name === "Valor contratado" ? "whitespace-nowrap text-right" : "whitespace-nowrap"}>
                      {name}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLUMNS.length}>
                      <EmptyState
                        message={
                          filtered
                            ? "Nenhuma ATA com esses filtros."
                            : data.total > 0
                              ? "Nenhuma ATA nesta página."
                              : "Nenhuma ATA cadastrada."
                        }
                        action={
                          filtered ? (
                            <Button variant="outline" onClick={() => router.push("/atas")}>
                              Limpar filtros
                            </Button>
                          ) : data.total > 0 ? (
                            <Button variant="outline" onClick={() => router.push("/atas")}>
                              Voltar à primeira página
                            </Button>
                          ) : writes ? (
                            <RegisterLink variant="outline" />
                          ) : undefined
                        }
                      />
                    </TableCell>
                  </TableRow>
                )}
                {data.items.map((ata) => (
                  <TableRow key={ata.id} data-testid="ata-row" data-ata-id={ata.id}>
                    <TableCell className="whitespace-nowrap font-normal">
                      <Link
                        href={`/atas/${ata.id}`}
                        className="text-primary underline-offset-4 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                      >
                        {ata.number}
                      </Link>
                    </TableCell>
                    <TableCell className="min-w-56">{ata.subject}</TableCell>
                    <TableCell className="min-w-48">{ata.fornecedor.legal_name}</TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">
                      {formatDay(ata.vigencia_inicio)} a {formatDay(ata.vigencia_fim)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">
                      {formatBRL(ata.valor_contratado)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={ata.status} />
                    </TableCell>
                    <TableCell>
                      <SituacaoBadge situacao={ata.situacao_vigencia} />
                    </TableCell>
                    <TableCell className="whitespace-nowrap tabular-nums">{formatDay(ata.data_reajuste)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">
                Página {page} de {lastPage} · {data.total} {data.total === 1 ? "ATA" : "ATAs"}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => router.push(hrefFor(status, situacao, page - 1))}
                >
                  <ChevronLeft aria-hidden />
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= lastPage}
                  onClick={() => router.push(hrefFor(status, situacao, page + 1))}
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
