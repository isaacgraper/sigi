"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ChartView, FilterPanel, TableView, TileView } from "@/components/dashboard/blocks";
import { panelId, SectionTabs, tabId } from "@/components/dashboard/section-tabs";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import {
  ATENDIMENTO,
  type Block,
  CONSUMO,
  ITENS_EM_FALTA,
  PROCESSOS,
  type Section,
  SECTIONS,
  sectionFor,
} from "@/lib/dashboard";
import { PERFIL_LABEL } from "@/lib/me";

// The stakeholders' RELATÓRIO GERAL CAME report, one tab per page and in its
// order (SPEC-0012). Every block reads "Sem dados" until SIGI holds its data.
export function Dashboard() {
  const { me } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const selected = sectionFor(useSearchParams().get("aba"));

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
          <SectionBody section={selected} />
        </div>
      </div>
    </div>
  );
}

function BlockView({ block, className }: { block: Block; className?: string }) {
  switch (block.kind) {
    case "stat":
    case "note":
      return <TileView block={block} />;
    case "table":
      return <TableView block={block} />;
    case "chart":
      return <ChartView block={block} className={className} />;
  }
}

// Each section keeps the report's arrangement at desktop width and collapses to
// one column on a phone (AC-0012-10).
function SectionBody({ section }: { section: Section }) {
  const b = section.blocks;
  switch (section.id) {
    case ATENDIMENTO.id:
      return (
        <>
          <FilterPanel filters={section.filters} />
          <div className="grid gap-6 xl:grid-cols-2">
            <BlockView block={b.mercadorias} />
            <BlockView block={b.unidades} />
          </div>
          <BlockView block={b.grafico} className="min-h-80" />
        </>
      );
    case CONSUMO.id:
      return (
        <>
          <div className="grid gap-6 lg:grid-cols-[1fr_14rem]">
            <FilterPanel filters={section.filters} />
            <BlockView block={b.estoque} />
          </div>
          <BlockView block={b.grafico} className="min-h-96" />
        </>
      );
    case PROCESSOS.id:
      return (
        <>
          <FilterPanel filters={section.filters} />
          <div className="grid gap-4 sm:grid-cols-3">
            {[b.abertura, b.novoProcesso, b.previsao, b.status, b.novaData, b.progresso, b.vigente, b.vencimento, b.semProcesso].map(
              (block) => (
                <BlockView key={block.title} block={block} />
              ),
            )}
          </div>
          <BlockView block={b.etapas} />
          <BlockView block={b.itens} />
        </>
      );
    case ITENS_EM_FALTA.id:
      return (
        <>
          <FilterPanel filters={section.filters} />
          <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-5">
            <BlockView block={b.sku} />
            <BlockView block={b.estoque} />
            <BlockView block={b.consumoMes} />
            <BlockView block={b.informacoes} />
            <BlockView block={b.sugestoes} />
          </div>
          <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <BlockView block={b.grupos} />
            <BlockView block={b.curvaAbc} />
            <BlockView block={b.disponibilidade} />
          </div>
          <BlockView block={b.materiais} />
        </>
      );
    default:
      return null;
  }
}
