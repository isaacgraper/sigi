"use client";

import { ChevronLeft, ChevronRight, FolderTree, Plus, Search, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { GrupoSelect } from "@/components/insumos/grupo-select";
import { InsumoSituacao } from "@/components/insumos/situacao";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FILTER_ALL } from "@/lib/constants";
import {
  EMPTY_VALUE,
  INSUMOS_PAGE_SIZE,
  LIST_COLUMNS,
  SEARCH_DELAY_MS,
  SITUACAO_LABEL,
  SITUACOES,
} from "@/lib/insumos/constants";
import { pathText } from "@/lib/insumos/grupos";
import type { GrupoNode, InsumoPage, Situacao } from "@/lib/insumos/types";
import { warm } from "@/lib/session";
import { useRead } from "@/lib/use-read";

interface Filters {
  q: string;
  grupo: string | null;
  situacao: Situacao | null;
  page: number;
}

/** The catalogue, searched and filtered, a page at a time (AC-0014-02 to -07). */
export function Insumos() {
  const { me } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const filters: Filters = {
    q: params.get("q")?.trim() ?? "",
    grupo: params.get("grupo") || null,
    situacao: SITUACOES.includes(params.get("situacao") as Situacao) ? (params.get("situacao") as Situacao) : null,
    page: pageFrom(params.get("pagina")),
  };
  const filtered = filters.q !== "" || filters.grupo !== null || filters.situacao !== null;
  const [typed, setTyped] = useState(filters.q);

  const grupos = useRead<GrupoNode[]>("/api/v1/grupos-materiais");
  const query = new URLSearchParams({ page: String(filters.page), size: String(INSUMOS_PAGE_SIZE) });
  if (filters.q) query.set("q", filters.q);
  if (filters.grupo) query.set("grupo_id", filters.grupo);
  if (filters.situacao) query.set("status", filters.situacao);
  const list = useRead<InsumoPage>(`/api/v1/insumos?${query}`);

  // Hiding the writes is cosmetic; the API refuses them (AC-0014-08, invariant 8).
  const registers = me.perfil === "gestor" || me.perfil === "servidor";
  const manages = me.perfil === "gestor";
  const tree = grupos.data;
  // A servidor is scoped by its grupos; with none, the tree comes back empty (AC-0014-05).
  const noGrupos = me.perfil === "servidor" && tree !== null && tree.length === 0;

  // The search waits for a pause in typing, then lives in the URL like the filters.
  useEffect(() => {
    if (typed.trim() === filters.q) return;
    const timer = window.setTimeout(() => router.replace(hrefFor({ ...filters, q: typed.trim(), page: 1 })), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  });

  const data = list.data;
  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const description =
    me.perfil === "servidor" && tree && tree.length > 0
      ? `Insumos dos seus grupos de materiais: ${tree.map((grupo) => grupo.name).join(", ")}`
      : "O catálogo de insumos, com os códigos do CAME e do DOMS.";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Insumos"
        description={description}
        action={
          <div className="flex flex-wrap gap-2">
            <Link href="/insumos/grupos" className={buttonVariants({ variant: "outline" })}>
              <FolderTree aria-hidden />
              Grupos de materiais
            </Link>
            {manages && <ImportLink />}
            {registers && !noGrupos && <RegisterLink />}
          </div>
        }
      />

      <section aria-label="Lista de insumos" className="space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-full space-y-2 sm:w-80">
            <Label htmlFor="busca">Buscar por SKU, código DOMS ou descrição</Label>
            <div className="relative">
              <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input id="busca" type="search" className="pl-9" value={typed} onChange={(e) => setTyped(e.target.value)} />
            </div>
          </div>
          <div className="w-full space-y-2 sm:w-72">
            <Label htmlFor="filtro-grupo">Grupo</Label>
            <GrupoSelect
              id="filtro-grupo"
              tree={tree ?? []}
              all
              value={filters.grupo ?? ""}
              onChange={(value) => router.push(hrefFor({ ...filters, grupo: value === FILTER_ALL ? null : value, page: 1 }))}
            />
          </div>
          <div className="w-full space-y-2 sm:w-48">
            <Label htmlFor="filtro-situacao">Situação</Label>
            <Select
              value={filters.situacao ?? FILTER_ALL}
              onValueChange={(value) =>
                router.push(hrefFor({ ...filters, situacao: value === FILTER_ALL ? null : (value as Situacao), page: 1 }))
              }
            >
              <SelectTrigger id="filtro-situacao">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={FILTER_ALL}>Todas</SelectItem>
                {SITUACOES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {SITUACAO_LABEL[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {filtered && <ClearButton onClear={() => (setTyped(""), router.push("/insumos"))} variant="ghost" />}
        </div>

        {list.failure && <ErrorNotice error={list.failure} />}

        {!data && !list.failure && (
          <div role="status">
            <span className="sr-only">Carregando...</span>
            <TableSkeleton />
          </div>
        )}

        {data && !list.failure && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  {LIST_COLUMNS.map((name) => (
                    <TableHead key={name} className="whitespace-nowrap">
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
                        message={
                          noGrupos
                            ? "Você ainda não tem grupos de materiais. Peça a um gestor para definir os seus."
                            : filtered
                              ? "Nenhum insumo com esses filtros."
                              : data.total > 0
                                ? "Nenhum insumo nesta página."
                                : "Nenhum insumo cadastrado."
                        }
                        action={
                          noGrupos ? undefined : filtered ? (
                            <ClearButton onClear={() => (setTyped(""), router.push("/insumos"))} variant="outline" />
                          ) : data.total > 0 ? (
                            <Button variant="outline" onClick={() => router.push("/insumos")}>
                              Voltar à primeira página
                            </Button>
                          ) : registers ? (
                            <div className="flex flex-wrap justify-center gap-2">
                              <RegisterLink variant="outline" />
                              {manages && <ImportLink />}
                            </div>
                          ) : undefined
                        }
                      />
                    </TableCell>
                  </TableRow>
                )}
                {data.items.map((insumo) => (
                  <TableRow key={insumo.id} data-testid="insumo-row" data-insumo-id={insumo.id}>
                    <TableCell className="whitespace-nowrap">
                      <Link
                        href={`/insumos/${insumo.id}`}
                        onPointerEnter={() => warm(`/api/v1/insumos/${insumo.id}`)}
                        onFocus={() => warm(`/api/v1/insumos/${insumo.id}`)}
                        className="font-mono text-xs text-primary underline-offset-4 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                      >
                        {insumo.sku}
                      </Link>
                    </TableCell>
                    <TableCell className="min-w-64">{insumo.description}</TableCell>
                    <TableCell className="whitespace-nowrap">{insumo.unit}</TableCell>
                    <TableCell className="min-w-48 text-muted-foreground">{pathText(insumo.grupo_path)}</TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs">{insumo.codigo_doms ?? EMPTY_VALUE}</TableCell>
                    <TableCell>
                      <InsumoSituacao insumo={insumo} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <nav aria-label="Paginação" className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-muted-foreground">
                Página {filters.page} de {lastPage} · {data.total} {data.total === 1 ? "insumo" : "insumos"}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={filters.page <= 1}
                  onClick={() => router.push(hrefFor({ ...filters, page: filters.page - 1 }))}
                >
                  <ChevronLeft aria-hidden />
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={filters.page >= lastPage}
                  onClick={() => router.push(hrefFor({ ...filters, page: filters.page + 1 }))}
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

function RegisterLink({ variant = "default" }: { variant?: "default" | "outline" }) {
  return (
    <Link href="/insumos/novo" className={buttonVariants({ variant })}>
      <Plus aria-hidden />
      Cadastrar insumo
    </Link>
  );
}

function ImportLink() {
  return (
    <Link href="/insumos/importar" className={buttonVariants({ variant: "outline" })}>
      <Upload aria-hidden />
      Importar catálogo
    </Link>
  );
}

function ClearButton({ onClear, variant }: { onClear: () => void; variant: "ghost" | "outline" }) {
  return (
    <Button variant={variant} onClick={onClear}>
      Limpar filtros
    </Button>
  );
}

function pageFrom(raw: string | null): number {
  const value = Number.parseInt(raw ?? "1", 10);
  return Number.isFinite(value) && value > 0 ? value : 1;
}

/** The list's state lives in the URL, so a reload or a shared link keeps it (AC-0014-03). */
function hrefFor(filters: Filters): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.grupo) params.set("grupo", filters.grupo);
  if (filters.situacao) params.set("situacao", filters.situacao);
  if (filters.page > 1) params.set("pagina", String(filters.page));
  const query = params.toString();
  return query ? `/insumos?${query}` : "/insumos";
}
