"use client";

import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { EventBody } from "@/components/historico/event-list";
import { PageHeader } from "@/components/page-header";
import { ExportDialog } from "@/components/relatorios/export-dialog";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FILTER_ALL } from "@/lib/constants";
import {
  ATALHO_EMPTY,
  ATALHO_LABEL,
  ATALHO_PARAM,
  ENTIDADE_LABEL,
  ENTIDADE_ROUTE,
  ENTIDADE_TIPOS,
  HISTORICO_COLUMNS,
  HISTORICO_DENIED,
  HISTORICO_EMPTY,
  HISTORICO_FILTER_KEYS,
  HISTORICO_PAGE_SIZE,
  LINK_CLASS,
  NO_ONE,
} from "@/lib/historico/constants";
import { formatMoment, matches } from "@/lib/historico/format";
import type { Atalho, HistoricoPage, HistoricoRow } from "@/lib/historico/types";
import { useMemberNames } from "@/lib/historico/use-names";
import { canReadHistory } from "@/lib/me";
import { useRead } from "@/lib/use-read";

type Key = (typeof HISTORICO_FILTER_KEYS)[number];
type Filters = Partial<Record<Key, string>>;

function hrefFor(filters: Filters, page: number): string {
  const params = new URLSearchParams();
  for (const key of HISTORICO_FILTER_KEYS) if (filters[key]) params.set(key, filters[key] as string);
  if (page > 1) params.set("pagina", String(page));
  const query = params.toString();
  return query ? `/historico?${query}` : "/historico";
}

function Entidade({ row }: { row: HistoricoRow }) {
  const label = ENTIDADE_LABEL[row.entidade_tipo] ?? row.entidade_tipo;
  const route = ENTIDADE_ROUTE[row.entidade_tipo];
  return route ? (
    <Link href={`${route}/${row.entidade_id}`} className={LINK_CLASS}>
      {label}
    </Link>
  ) : (
    <span>{label}</span>
  );
}

/** /historico: every event, filtered, newest first, for the gestor and the auditor (AC-0017-08 to -12). */
export function Historico() {
  const { me } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const allowed = canReadHistory(me.perfil);
  const filters: Filters = Object.fromEntries(HISTORICO_FILTER_KEYS.map((key) => [key, params.get(key) ?? undefined]));
  const atalho = filters.so === "valor" || filters.so === "status" ? (filters.so as Atalho) : null;
  const page = Math.max(1, Number.parseInt(params.get("pagina") ?? "1", 10) || 1);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const query = new URLSearchParams({ page: String(page), size: String(HISTORICO_PAGE_SIZE) });
  if (filters.entidade) query.set("entidade_tipo", filters.entidade);
  if (filters.id) query.set("entidade_id", filters.id);
  if (filters.usuario) query.set("usuario_id", filters.usuario);
  if (filters.de) query.set("de", filters.de);
  if (filters.ate) query.set("ate", filters.ate);
  const list = useRead<HistoricoPage>(allowed ? `/api/v1/historico?${query}` : null);
  const names = useMemberNames(allowed);
  // A refused filter keeps the last list on screen, its message under the field (AC-0017-09).
  const [kept, setKept] = useState<HistoricoPage | null>(null);
  if (list.data && list.data !== kept) setKept(list.data);
  const data = list.data ?? (list.failure?.status === 422 ? kept : null);
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const refused = list.failure?.status === 422 ? list.failure.fields : {};
  const shown = data ? data.items.filter((row) => matches(row, atalho)) : [];

  // Read the URL as it is now: two filters changed in a row must not undo each other.
  const set = (key: Key, value: string | undefined) => {
    const now = new URLSearchParams(window.location.search);
    const current: Filters = Object.fromEntries(HISTORICO_FILTER_KEYS.map((k) => [k, now.get(k) ?? undefined]));
    router.push(hrefFor({ ...current, [key]: value || undefined }, 1));
  };

  if (!allowed) {
    return (
      <div className="space-y-6">
        <PageHeader title="Histórico" description="O que aconteceu em cada ATA, NE, NF e insumo." />
        <p data-testid="historico-negado" role="status" className="rounded-md border border-border/70 bg-card px-4 py-3 text-sm">
          {HISTORICO_DENIED}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Histórico"
        description="O que aconteceu em cada ATA, NE, NF e insumo, com o que mudou."
        action={
          <ExportDialog
            relatorio="historico"
            title="o histórico"
            filtros={{
              entidade_tipo: filters.entidade,
              entidade_id: filters.id,
              usuario_id: filters.usuario,
              de: filters.de,
              ate: filters.ate,
            }}
          />
        }
      />

      <section aria-label="Lista de eventos" className="space-y-4">
        <div className="flex flex-wrap items-start gap-4">
          <div className="w-full space-y-2 sm:w-52">
            <Label htmlFor="filtro-entidade">Entidade</Label>
            <Select
              value={filters.entidade ?? FILTER_ALL}
              onValueChange={(value) =>
                router.push(hrefFor({ ...filters, entidade: value === FILTER_ALL ? undefined : value, id: undefined }, 1))
              }
            >
              <SelectTrigger id="filtro-entidade">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={FILTER_ALL}>Todas</SelectItem>
                {ENTIDADE_TIPOS.map((tipo) => (
                  <SelectItem key={tipo} value={tipo}>
                    {ENTIDADE_LABEL[tipo]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {refused.entidade_tipo && (
              <p data-testid="field-error" className="text-sm text-destructive">
                {refused.entidade_tipo}
              </p>
            )}
          </div>
          <div className="w-full space-y-2 sm:w-60">
            <Label htmlFor="filtro-usuario">Membro</Label>
            <Select
              value={filters.usuario ?? FILTER_ALL}
              onValueChange={(value) => set("usuario", value === FILTER_ALL ? undefined : value)}
            >
              <SelectTrigger id="filtro-usuario">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={FILTER_ALL}>Todos</SelectItem>
                {Object.entries(names).map(([id, name]) => (
                  <SelectItem key={id} value={id}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-full sm:w-44">
            <Field id="filtro-de" label="De" error={refused.de}>
              {(props) => (
                <Input {...props} type="date" value={filters.de ?? ""} onChange={(e) => set("de", e.target.value)} />
              )}
            </Field>
          </div>
          <div className="w-full sm:w-44">
            <Field id="filtro-ate" label="Até" error={refused.ate}>
              {(props) => (
                <Input {...props} type="date" value={filters.ate ?? ""} onChange={(e) => set("ate", e.target.value)} />
              )}
            </Field>
          </div>
        </div>

        <div className="flex flex-wrap gap-2" role="group" aria-label="Atalhos">
          {(["valor", "status"] as Atalho[]).map((value) => (
            <Button
              key={value}
              variant={atalho === value ? "default" : "outline"}
              size="sm"
              aria-pressed={atalho === value}
              onClick={() => set(ATALHO_PARAM, atalho === value ? undefined : value)}
            >
              {ATALHO_LABEL[value]}
            </Button>
          ))}
        </div>

        {list.failure && list.failure.status !== 422 && !data && <ErrorNotice error={list.failure} />}
        {!data && !list.failure && (
          <div role="status">
            <span className="sr-only">Carregando...</span>
            <TableSkeleton />
          </div>
        )}

        {data && (
          <>
            {atalho && (
              <p data-testid="atalho-nota" className="text-xs font-light text-muted-foreground">
                {shown.length} de {data.items.length} eventos desta página.
              </p>
            )}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <span className="sr-only">Abrir</span>
                  </TableHead>
                  {HISTORICO_COLUMNS.map((name) => (
                    <TableHead key={name} className="whitespace-nowrap">
                      {name}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={HISTORICO_COLUMNS.length + 1}>
                      <EmptyState message={atalho && data.items.length > 0 ? ATALHO_EMPTY : HISTORICO_EMPTY} />
                    </TableCell>
                  </TableRow>
                )}
                {shown.map((row) => (
                  <Fragment key={row.id}>
                    <TableRow data-testid="historico-row" data-acao={row.acao}>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="size-8 p-0"
                          aria-expanded={Boolean(open[row.id])}
                          aria-label={`Detalhes de ${row.acao_rotulo}`}
                          onClick={() => setOpen({ ...open, [row.id]: !open[row.id] })}
                        >
                          <ChevronDown aria-hidden className={open[row.id] ? "rotate-180" : undefined} />
                        </Button>
                      </TableCell>
                      <TableCell className="whitespace-nowrap tabular-nums">{formatMoment(row.ocorrido_em)}</TableCell>
                      <TableCell>{row.acao_rotulo}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        <Entidade row={row} />
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {row.usuario_id ? (names[row.usuario_id] ?? "—") : NO_ONE}
                      </TableCell>
                    </TableRow>
                    {open[row.id] && (
                      <TableRow data-testid="historico-detalhe">
                        <TableCell />
                        <TableCell colSpan={HISTORICO_COLUMNS.length}>
                          <EventBody evento={row} names={names} />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>

            <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">
                Página {page} de {lastPage} · {data.total} {data.total === 1 ? "evento" : "eventos"}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => router.push(hrefFor(filters, page - 1))}>
                  <ChevronLeft aria-hidden />
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= lastPage}
                  onClick={() => router.push(hrefFor(filters, page + 1))}
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
