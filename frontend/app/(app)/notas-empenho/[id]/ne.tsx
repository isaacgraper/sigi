"use client";

import { ArrowLeft, Check } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { NeActions } from "@/components/notas-empenho/ne-actions";
import { NeStage } from "@/components/notas-empenho/stage";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBRL, formatDate, formatDay, formatQuantity, formatUnitPrice } from "@/lib/format";
import { ACTION_DONE, STAGE_LABEL, STAGES } from "@/lib/notas-empenho/constants";
import type { NotaEmpenho, Stage } from "@/lib/notas-empenho/types";
import { cn } from "@/lib/utils";
import { useRead } from "@/lib/use-read";

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs font-light text-muted-foreground">{label}</dt>
      <dd className="break-words text-sm">{children}</dd>
    </div>
  );
}

/** The five stages, the ones passed checked and the current one marked (AC-0015-05). */
function Steps({ ne }: { ne: NotaEmpenho }) {
  const reached = ne.status === "cancelada" ? -1 : STAGES.indexOf(ne.status as Stage);
  return (
    <ol aria-label="Etapas da NE" data-testid="ne-steps" className="grid gap-2 sm:grid-cols-5">
      {STAGES.map((stage, index) => {
        const done = index < reached || ne.status === "ne_emitida";
        const current = index === reached && ne.status !== "ne_emitida";
        return (
          <li
            key={stage}
            aria-current={current ? "step" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
              current && "border-primary text-foreground",
              !current && !done && "text-muted-foreground",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-full border text-xs tabular-nums",
                done && "border-primary bg-primary text-primary-foreground",
                current && "border-primary text-primary",
              )}
            >
              {done ? <Check className="size-3" /> : index + 1}
            </span>
            {STAGE_LABEL[stage]}
          </li>
        );
      })}
    </ol>
  );
}

/** /notas-empenho/{id}: the NE, its stages, its itens and the moves (AC-0015-05 to -09). */
export function NeView() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const read = useRead<NotaEmpenho>(`/api/v1/notas-empenho/${id}`);
  const [announcement, setAnnouncement] = useState("");
  const ne = read.data;
  // Hiding a move is cosmetic; the API refuses what a perfil may not do (invariant 8).
  const moves = me.perfil === "gestor" || me.perfil === "servidor";

  if (read.failure && !ne) {
    const missing = read.failure.status === 404 || read.failure.status === 422;
    return (
      <div className="space-y-6">
        <PageHeader title={missing ? "NE não encontrada" : "Nota de empenho"} description="Não foi possível abrir a NE." />
        {missing ? (
          <EmptyState
            message="NE não encontrada."
            action={
              <Link href="/notas-empenho" className={buttonVariants({ variant: "outline" })}>
                <ArrowLeft aria-hidden />
                Voltar para notas de empenho
              </Link>
            }
          />
        ) : (
          <ErrorNotice error={read.failure} />
        )}
      </div>
    );
  }
  if (!ne) return <TableSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={ne.number ? `NE ${ne.number}` : `NE do processo ${ne.processo_sei}`}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <NeStage status={ne.status} />
            <span aria-hidden className="h-4 w-px bg-border" />
            <span>ATA {ne.ata_number}</span>
          </span>
        }
        action={
          moves ? (
            <NeActions
              ne={ne}
              gestor={me.perfil === "gestor"}
              onDone={(next, action) => {
                read.replace(next);
                setAnnouncement(ACTION_DONE[action]);
              }}
              onStale={read.reload}
            />
          ) : undefined
        }
      />

      <p role="status" className="sr-only">
        {announcement}
      </p>

      {ne.status === "cancelada" ? (
        <p data-testid="ne-cancelada" className="text-sm text-muted-foreground">
          Esta NE foi cancelada. O saldo que ela reservava foi liberado.
        </p>
      ) : (
        <Steps ne={ne} />
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Dados da NE</CardTitle>
        </CardHeader>
        <CardContent>
          <dl data-testid="ne-dados" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Item label="ATA">
              <Link href={`/atas/${ne.ata_id}`} className="text-primary underline-offset-4 [@media(hover:hover)_and_(pointer:fine)]:hover:underline">
                {ne.ata_number}
              </Link>
            </Item>
            <Item label="Processo SEI">
              <span className="tabular-nums">{ne.processo_sei}</span>
            </Item>
            <Item label="Valor">
              <span data-testid="ne-valor" className="tabular-nums">
                {formatBRL(ne.value)}
              </span>
            </Item>
            <Item label="Nota de pré-empenho">
              <span data-testid="ne-pre-empenho" className="tabular-nums">
                {ne.numero_pre_empenho ?? "—"}
              </span>
            </Item>
            <Item label="Número da NE">
              <span data-testid="ne-numero" className="tabular-nums">
                {ne.number ?? "—"}
              </span>
            </Item>
            <Item label="Emitida em">{ne.issued_on ? formatDay(ne.issued_on) : "—"}</Item>
            <Item label="Aberta em">{formatDate(ne.created_at)}</Item>
          </dl>
        </CardContent>
      </Card>

      <section aria-label="Itens" className="space-y-3">
        <h2 className="text-base font-normal">Itens</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Insumo</TableHead>
              <TableHead className="whitespace-nowrap text-right">Quantidade</TableHead>
              <TableHead className="whitespace-nowrap text-right">Valor unitário</TableHead>
              <TableHead className="whitespace-nowrap text-right">Valor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ne.items.map((line) => (
              <TableRow key={line.id} data-testid="ne-item">
                <TableCell className="min-w-56">
                  {line.description}
                  <span className="block text-xs font-light text-muted-foreground">
                    {line.sku} · {line.unit}
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatQuantity(line.quantity)}</TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatUnitPrice(line.unit_price)}</TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatBRL(line.value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
    </div>
  );
}
