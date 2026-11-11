import { ArrowRight } from "lucide-react";

import { CREATED_WITH, NO_EVENTS, REMOVED } from "@/lib/historico/constants";
import { formatDetalhe, formatMoment, formatValor, kindOf } from "@/lib/historico/format";
import type { Alteracao, Detalhe, Evento } from "@/lib/historico/types";

/** One change: its label, the value before and the value after (AC-0017-01). */
function Change({
  alteracao,
  kind,
  names,
}: {
  alteracao: Alteracao;
  kind: ReturnType<typeof kindOf>;
  names: Record<string, string>;
}) {
  const antes = formatValor(alteracao.tipo, alteracao.antes, names);
  const depois = formatValor(alteracao.tipo, alteracao.depois, names);
  return (
    <div data-testid="alteracao" data-campo={alteracao.campo} className="grid gap-x-3 sm:grid-cols-[12rem_1fr]">
      <dt className="text-xs font-light text-muted-foreground sm:text-sm">{alteracao.rotulo}</dt>
      <dd className="flex min-w-0 flex-wrap items-center gap-x-2 text-sm tabular-nums">
        {kind === "created" && <span data-testid="depois">{depois}</span>}
        {kind === "removed" && <span data-testid="antes">{antes}</span>}
        {kind === "changed" && (
          <>
            <span data-testid="antes" className="text-muted-foreground line-through decoration-border">
              {antes}
            </span>
            <ArrowRight aria-hidden className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="sr-only">para</span>
            <span data-testid="depois">{depois}</span>
          </>
        )}
      </dd>
    </div>
  );
}

function Detail({ detalhe, names }: { detalhe: Detalhe; names: Record<string, string> }) {
  return (
    <div data-testid="detalhe" className="grid gap-x-3 sm:grid-cols-[12rem_1fr]">
      <dt className="text-xs font-light text-muted-foreground sm:text-sm">{detalhe.rotulo}</dt>
      <dd className="break-words text-sm">{formatDetalhe(detalhe.valor, names)}</dd>
    </div>
  );
}

/** What one event changed and recorded, below its title (AC-0017-01 to -03, -10). */
export function EventBody({ evento, names }: { evento: Evento; names: Record<string, string> }) {
  const kind = kindOf(evento.alteracoes);
  return (
    <div className="space-y-2">
      {kind !== "changed" && (
        <p className="text-xs font-light text-muted-foreground">{kind === "created" ? CREATED_WITH : REMOVED}</p>
      )}
      {evento.alteracoes.length > 0 && (
        <dl className="space-y-1.5">
          {evento.alteracoes.map((alteracao) => (
            <Change key={alteracao.campo} alteracao={alteracao} kind={kind} names={names} />
          ))}
        </dl>
      )}
      {(evento.detalhes.length > 0 || evento.justificativa) && (
        <dl className="space-y-1.5 border-t border-border/60 pt-2">
          {evento.detalhes.map((detalhe) => (
            <Detail key={detalhe.campo} detalhe={detalhe} names={names} />
          ))}
          {evento.justificativa && (
            <Detail detalhe={{ campo: "justificativa", rotulo: "Justificativa", valor: evento.justificativa }} names={names} />
          )}
        </dl>
      )}
    </div>
  );
}

/** Events in the order given, each with its label, when, who and what it changed. */
export function EventList({ eventos, names }: { eventos: Evento[]; names: Record<string, string> }) {
  if (eventos.length === 0) return <p className="text-sm font-light text-muted-foreground">{NO_EVENTS}</p>;
  return (
    <ol className="space-y-3">
      {eventos.map((evento, index) => (
        <li
          key={`${evento.ocorrido_em}-${evento.acao}-${index}`}
          data-testid="evento"
          data-acao={evento.acao}
          className="rounded-md border border-border/70 bg-card px-4 py-3"
        >
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="text-sm">{evento.acao_rotulo}</p>
            <p className="text-xs font-light text-muted-foreground tabular-nums">
              <time dateTime={evento.ocorrido_em}>{formatMoment(evento.ocorrido_em)}</time>
              {evento.usuario_id && names[evento.usuario_id] ? ` · ${names[evento.usuario_id]}` : ""}
            </p>
          </div>
          <EventBody evento={evento} names={names} />
        </li>
      ))}
    </ol>
  );
}
