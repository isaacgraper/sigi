"use client";

import Link from "next/link";
import { useState } from "react";

import { AtaStatus } from "@/components/atas/status";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { EventList } from "@/components/historico/event-list";
import { NeStage } from "@/components/notas-empenho/stage";
import { NfStatusBadge } from "@/components/notas-fiscais/status";
import { TableSkeleton } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import { formatQuantity, formatUnitPrice } from "@/lib/format";
import {
  CURRENT_ETAPA,
  ETAPA_LABEL,
  HIDE_EVENTS,
  LINK_CLASS,
  MISSING_PREFIX,
  RASTREIO_EMPTY,
  SHOW_EVENTS,
} from "@/lib/historico/constants";
import type { Ciclo, CicloEvento, Etapa } from "@/lib/historico/types";
import { useMemberNames } from "@/lib/historico/use-names";
import { useReads } from "@/lib/historico/use-reads";
import type { InsumoDetail } from "@/lib/insumos/types";
import { canReadHistory } from "@/lib/me";
import { STAGE_LABEL, STAGES } from "@/lib/notas-empenho/constants";
import type { NotaEmpenho } from "@/lib/notas-empenho/types";
import type { NotaFiscal } from "@/lib/notas-fiscais/types";
import type { Perfil } from "@/lib/types";
import { useRead } from "@/lib/use-read";

/** One step of the timeline: what it is, where it opens, and its events on demand (AC-0017-05, -06). */
function Step({
  etapa,
  title,
  href,
  status,
  eventos,
  names,
  children,
}: {
  etapa: Etapa;
  title: string;
  href?: string;
  status?: React.ReactNode;
  eventos: CicloEvento[];
  names: Record<string, string>;
  children?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <li data-testid="rastreio-etapa" data-etapa={etapa} className="relative pb-6 pl-6 last:pb-0">
      <span aria-hidden className="absolute -left-[5px] top-1.5 size-2.5 rounded-full border-2 border-primary bg-card" />
      <p className="text-xs font-light text-muted-foreground">{ETAPA_LABEL[etapa]}</p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {href ? (
          <Link href={href} className={LINK_CLASS}>
            {title}
          </Link>
        ) : (
          <span>{title}</span>
        )}
        {status}
      </div>
      {children}
      <Button variant="link" size="sm" className="h-auto px-0 py-1" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? HIDE_EVENTS : SHOW_EVENTS} ({eventos.length})
      </Button>
      {open && (
        <div className="mt-2">
          <EventList eventos={eventos} names={names} />
        </div>
      )}
    </li>
  );
}

/** The five etapas of an NE, the current one marked and the missing ones listed (AC-0017-05). */
function Etapas({ ne }: { ne: NotaEmpenho }) {
  if (ne.status === "cancelada") return null;
  const current = STAGES.indexOf(ne.status);
  const missing = STAGES.slice(current + 1);
  return (
    <div className="mt-2 space-y-1">
      <ol aria-label="Etapas da NE" className="flex flex-wrap gap-x-2 gap-y-1 text-xs">
        {STAGES.map((stage, index) => (
          <li
            key={stage}
            data-testid="ne-etapa"
            data-estado={index < current ? "feita" : index === current ? "atual" : "faltando"}
            aria-current={index === current ? "step" : undefined}
            className={
              index === current
                ? "rounded-md border border-primary px-2 py-0.5 text-foreground"
                : index < current
                  ? "px-2 py-0.5 text-foreground"
                  : "px-2 py-0.5 font-light text-muted-foreground"
            }
          >
            {STAGE_LABEL[stage]}
            {index === current && <span className="sr-only"> ({CURRENT_ETAPA})</span>}
          </li>
        ))}
      </ol>
      {missing.length > 0 && (
        <p data-testid="ne-faltam" className="text-xs font-light text-muted-foreground">
          {MISSING_PREFIX}: {missing.map((stage) => STAGE_LABEL[stage]).join(", ")}
        </p>
      )}
    </div>
  );
}

/** The insumo from ATA to NF, for every perfil inside RN07 (AC-0017-05 to -07). */
export function Rastreio({ insumo, perfil }: { insumo: InsumoDetail; perfil: Perfil }) {
  const read = useRead<Ciclo>(insumo.atas.length > 0 ? `/api/v1/insumos/${insumo.id}/ciclo` : null);
  const names = useMemberNames(canReadHistory(perfil));
  const eventos = read.data?.eventos ?? [];
  const ids = (etapa: Etapa) => [...new Set(eventos.filter((e) => e.etapa === etapa).map((e) => e.entidade_id))];
  const nes = useReads<NotaEmpenho>(ids("nota_empenho").map((id) => `/api/v1/notas-empenho/${id}`));
  const nfs = useReads<NotaFiscal>(ids("nota_fiscal").map((id) => `/api/v1/notas-fiscais/${id}`));
  const of = (etapa: Etapa, id: string) => eventos.filter((e) => e.etapa === etapa && e.entidade_id === id);

  return (
    <section aria-label="Rastreio" className="space-y-3">
      <div>
        <h2 className="text-base font-normal">Rastreio</h2>
        <p className="text-sm font-light text-muted-foreground">Da ATA à nota fiscal, o caminho deste insumo.</p>
      </div>
      {insumo.atas.length === 0 && <EmptyState message={RASTREIO_EMPTY} />}
      {insumo.atas.length > 0 && read.failure && !read.data && <ErrorNotice error={read.failure} />}
      {insumo.atas.length > 0 && !read.data && !read.failure && <TableSkeleton rows={3} />}
      {read.data && (
        <div className="space-y-4">
          {insumo.atas.map((ata) => {
            const itsNes = Object.values(nes).filter((ne) => ne.ata_id === ata.ata_id);
            return (
              <ol
                key={ata.item_id}
                data-testid="rastreio"
                className="ml-1.5 rounded-none border-l border-border"
              >
                <Step
                  etapa="ata"
                  title={`ATA ${ata.ata_number}`}
                  href={`/atas/${ata.ata_id}`}
                  status={<AtaStatus ata={{ status: ata.ata_status, situacao_vigencia: "vigente" }} />}
                  eventos={of("ata", ata.ata_id)}
                  names={names}
                />
                <Step
                  etapa="item_ata"
                  title={`${formatQuantity(ata.quantity)} ${insumo.unit} a ${formatUnitPrice(ata.unit_price)}`}
                  eventos={of("item_ata", ata.ata_id)}
                  names={names}
                />
                {itsNes.map((ne) => (
                  <NeSteps key={ne.id} ne={ne} nfs={Object.values(nfs)} of={of} names={names} />
                ))}
              </ol>
            );
          })}
        </div>
      )}
    </section>
  );
}

function NeSteps({
  ne,
  nfs,
  of,
  names,
}: {
  ne: NotaEmpenho;
  nfs: NotaFiscal[];
  of: (etapa: Etapa, id: string) => CicloEvento[];
  names: Record<string, string>;
}) {
  return (
    <>
      <Step
        etapa="nota_empenho"
        title={`NE ${ne.number ?? "sem número"} · Processo SEI ${ne.processo_sei}`}
        href={`/notas-empenho/${ne.id}`}
        status={<NeStage status={ne.status} />}
        eventos={of("nota_empenho", ne.id)}
        names={names}
      >
        <Etapas ne={ne} />
      </Step>
      {nfs
        .filter((nf) => nf.nota_empenho_id === ne.id)
        .map((nf) => (
          <Step
            key={nf.id}
            etapa="nota_fiscal"
            title={`NF ${nf.numero}`}
            href={`/notas-fiscais/${nf.id}`}
            status={<NfStatusBadge status={nf.status} quarentena={nf.quarentena} />}
            eventos={of("nota_fiscal", nf.id)}
            names={names}
          />
        ))}
    </>
  );
}
