"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ChartView, FilterPanel, type Rows, TableView, TileView } from "@/components/dashboard/blocks";
import { panelId, SectionTabs, tabId } from "@/components/dashboard/section-tabs";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import {
  ATENDIMENTO,
  type Block,
  CONSUMO,
  ITENS_EM_FALTA,
  type PainelOut,
  PROCESSOS,
  type Section,
  SECTIONS,
  sectionFor,
} from "@/lib/dashboard";
import { ApiError, unavailable } from "@/lib/errors";
import { PERFIL_LABEL } from "@/lib/me";
import { apiJson } from "@/lib/session";

// The stakeholders' RELATÓRIO GERAL CAME report, one tab per page and in its
// order (SPEC-0012). Each tab asks the backend for its blocks (§7): a skeleton
// while it waits, "Sem dados" for a block that comes back empty.
export function Dashboard() {
  const { me, handleSessionError } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const selected = sectionFor(useSearchParams().get("aba"));
  const [answer, setAnswer] = useState<PainelOut | null>(null);
  const [failure, setFailure] = useState<{ section: string; error: ApiError } | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiJson<PainelOut>(`/api/v1/painel/${selected.id}`)
      .then((value) => {
        if (cancelled) return;
        setAnswer(value);
        setFailure(null);
      })
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setFailure({ section: selected.id, error: err instanceof ApiError ? err : unavailable() });
      });
    return () => {
      cancelled = true;
    };
  }, [selected.id, handleSessionError]);

  // An answer or a failure for another tab is stale: this tab is still loading.
  const current = answer?.section === selected.id ? answer : null;
  const error = failure?.section === selected.id ? failure.error : null;
  const rowsOf = (block: string): Rows => current?.blocks[block]?.rows;

  function select(section: Section) {
    // The tab lives in the URL so a reload or a shared link keeps it (AC-0012-03).
    const query = section.id === SECTIONS[0].id ? "" : `?aba=${section.id}`;
    router.replace(`${pathname}${query}`, { scroll: false });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Painel"
        description={
          // Who is signed in (AC-0010-28).
          <>
            {me.name && (
              <>
                <span data-testid="me-name">{me.name}</span>
                {" · "}
              </>
            )}
            <span data-testid="me-email" className="break-all">
              {me.email ?? "—"}
            </span>
            {" · "}
            <span data-testid="me-perfil">{PERFIL_LABEL[me.perfil]}</span>
          </>
        }
      />

      <div className="space-y-6">
        <SectionTabs sections={SECTIONS} selected={selected} onSelect={select} />
        <div
          id={panelId(selected)}
          role="tabpanel"
          aria-labelledby={tabId(selected)}
          tabIndex={0}
          data-testid="dashboard-panel"
          className="space-y-6 focus-visible:outline-none"
        >
          <p className="text-sm font-light text-muted-foreground">{selected.description}</p>
          {error ? (
            // A failed request never passes for an empty one (AC-0012-05).
            <div data-testid="dashboard-error" className="rounded-lg border bg-card p-6 shadow-sm">
              <ErrorNotice error={error} />
            </div>
          ) : (
            <>
              {!current && (
                <p role="status" className="sr-only">
                  Carregando...
                </p>
              )}
              <SectionBody section={selected} rowsOf={rowsOf} demo={current?.demo ?? false} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function BlockView({ block, rows, className }: { block: Block; rows: Rows; className?: string }) {
  switch (block.kind) {
    case "stat":
    case "note":
      return <TileView block={block} rows={rows} />;
    case "table":
      return <TableView block={block} rows={rows} />;
    case "chart":
      return <ChartView block={block} rows={rows} className={className} />;
  }
}

// Each section keeps the report's arrangement at desktop width and collapses to
// one column on a phone (AC-0012-10).
function SectionBody({
  section,
  rowsOf,
  demo,
}: {
  section: Section;
  rowsOf: (block: string) => Rows;
  demo: boolean;
}) {
  const filters = (
    <FilterPanel
      filters={section.filters}
      note={demo ? "Filtros indisponíveis na demonstração." : undefined}
    />
  );
  // One block by its id: its declaration, and the rows the backend sent for it.
  const at = (id: string, className?: string) => (
    <BlockView key={id} block={section.blocks[id]} rows={rowsOf(id)} className={className} />
  );
  switch (section.id) {
    case ATENDIMENTO.id:
      return (
        <>
          {filters}
          <div className="grid gap-6 xl:grid-cols-2">
            {at("mercadorias")}
            {at("unidades")}
          </div>
          {at("grafico", "min-h-80")}
        </>
      );
    case CONSUMO.id:
      return (
        <>
          <div className="grid gap-6 lg:grid-cols-[1fr_14rem]">
            {filters}
            {at("estoque")}
          </div>
          {at("grafico", "min-h-96")}
        </>
      );
    case PROCESSOS.id:
      return (
        <>
          {filters}
          <div className="data-stagger grid gap-4 sm:grid-cols-3">
            {["abertura", "novo_processo", "previsao", "status", "nova_data", "progresso", "vigente", "vencimento", "sem_processo"].map(
              (id) => at(id),
            )}
          </div>
          {at("etapas")}
          {at("itens")}
        </>
      );
    case ITENS_EM_FALTA.id:
      return (
        <>
          {filters}
          <div className="data-stagger grid gap-4 sm:grid-cols-3 xl:grid-cols-5">
            {at("sku")}
            {at("estoque")}
            {at("consumo_mes")}
            {at("informacoes")}
            {at("sugestoes")}
          </div>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
            {at("grupos")}
            {at("curva_abc")}
            {at("disponibilidade")}
          </div>
          {at("materiais")}
        </>
      );
    default:
      return null;
  }
}
