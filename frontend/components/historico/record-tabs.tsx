"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useId, useRef } from "react";

import { EventList } from "@/components/historico/event-list";
import { ErrorNotice } from "@/components/error-notice";
import { TableSkeleton } from "@/components/skeleton";
import {
  ACOMPANHAMENTO_SIZE,
  TAB_ACOMPANHAMENTO,
  TAB_ACOMPANHAMENTO_LABEL,
  TAB_DADOS_LABEL,
  TAB_PARAM,
} from "@/lib/historico/constants";
import type { HistoricoPage, Registro } from "@/lib/historico/types";
import { useMemberNames } from "@/lib/historico/use-names";
import { canReadHistory } from "@/lib/me";
import type { Perfil } from "@/lib/types";
import { useRead } from "@/lib/use-read";
import { cn } from "@/lib/utils";

/** A record's history, newest first (AC-0017-01, -02). */
function Acompanhamento({ registro, id }: { registro: Registro; id: string }) {
  const query = new URLSearchParams({ entidade_tipo: registro, entidade_id: id, page: "1", size: String(ACOMPANHAMENTO_SIZE) });
  const read = useRead<HistoricoPage>(`/api/v1/historico?${query}`);
  const names = useMemberNames(true);
  if (read.failure && !read.data) return <ErrorNotice error={read.failure} />;
  if (!read.data) return <TableSkeleton />;
  const more = read.data.total > read.data.items.length;
  return (
    <div className="space-y-3">
      <EventList eventos={read.data.items} names={names} />
      {more && (
        <Link
          href={`/historico?entidade=${registro}&id=${id}`}
          className="text-sm text-primary underline-offset-4 [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
        >
          Ver os {read.data.total} eventos no Histórico
        </Link>
      )}
    </div>
  );
}

/**
 * "Dados" and "Acompanhamento" on an ATA, an NE or an NF, the tab kept in the
 * URL. A servidor reads no history (AC-0017-04), so it sees the record alone.
 */
export function RecordTabs({
  registro,
  id,
  perfil,
  children,
}: {
  registro: Registro;
  id: string;
  perfil: Perfil;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const base = useId();
  const dadosTab = useRef<HTMLButtonElement>(null);
  const acompanhamentoTab = useRef<HTMLButtonElement>(null);
  if (!canReadHistory(perfil)) return <>{children}</>;

  const onAcompanhamento = params.get(TAB_PARAM) === TAB_ACOMPANHAMENTO;
  const choose = (acompanhamento: boolean) => {
    const next = new URLSearchParams(params.toString());
    if (acompanhamento) next.set(TAB_PARAM, TAB_ACOMPANHAMENTO);
    else next.delete(TAB_PARAM);
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
  // Arrow keys move between the two tabs (WAI-ARIA tabs pattern).
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    choose(!onAcompanhamento);
    (onAcompanhamento ? dadosTab : acompanhamentoTab).current?.focus();
  };
  const tabClass = (active: boolean) =>
    cn(
      "-mb-px border-b-2 px-3 py-2 text-sm focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      active
        ? "border-primary text-foreground"
        : "border-transparent text-muted-foreground [@media(hover:hover)_and_(pointer:fine)]:hover:text-foreground",
    );

  return (
    <div className="space-y-6">
      <div role="tablist" aria-label="Seções" className="flex gap-2 border-b border-border" onKeyDown={onKeyDown}>
        <button
          ref={dadosTab}
          type="button"
          role="tab"
          id={`${base}-dados`}
          aria-selected={!onAcompanhamento}
          aria-controls={`${base}-dados-panel`}
          tabIndex={onAcompanhamento ? -1 : 0}
          className={tabClass(!onAcompanhamento)}
          onClick={() => choose(false)}
        >
          {TAB_DADOS_LABEL}
        </button>
        <button
          ref={acompanhamentoTab}
          type="button"
          role="tab"
          id={`${base}-acompanhamento`}
          aria-selected={onAcompanhamento}
          aria-controls={`${base}-acompanhamento-panel`}
          tabIndex={onAcompanhamento ? 0 : -1}
          className={tabClass(onAcompanhamento)}
          onClick={() => choose(true)}
        >
          {TAB_ACOMPANHAMENTO_LABEL}
        </button>
      </div>
      {onAcompanhamento ? (
        <div role="tabpanel" id={`${base}-acompanhamento-panel`} aria-labelledby={`${base}-acompanhamento`}>
          <Acompanhamento registro={registro} id={id} />
        </div>
      ) : (
        <div role="tabpanel" id={`${base}-dados-panel`} aria-labelledby={`${base}-dados`} className="space-y-6">
          {children}
        </div>
      )}
    </div>
  );
}
