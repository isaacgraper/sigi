"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { NfActions } from "@/components/notas-fiscais/nf-actions";
import { NfStatusBadge } from "@/components/notas-fiscais/status";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBRL, formatDate, formatDay, formatQuantity } from "@/lib/format";
import { NF_ACTION_DONE } from "@/lib/notas-fiscais/constants";
import type { NotaFiscal } from "@/lib/notas-fiscais/types";
import { useRead } from "@/lib/use-read";

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs font-light text-muted-foreground">{label}</dt>
      <dd className="break-words text-sm">{children}</dd>
    </div>
  );
}

/** /notas-fiscais/{id}: the NF, its itens and the moves on it (AC-0016-06 to -08). */
export function NfView() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const read = useRead<NotaFiscal>(`/api/v1/notas-fiscais/${id}`);
  const [announcement, setAnnouncement] = useState("");
  const nf = read.data;

  if (read.failure && !nf) {
    const missing = read.failure.status === 404 || read.failure.status === 422;
    return (
      <div className="space-y-6">
        <PageHeader title={missing ? "NF não encontrada" : "Nota fiscal"} description="Não foi possível abrir a NF." />
        {missing ? (
          <EmptyState
            message="NF não encontrada."
            action={
              <Link href="/notas-fiscais" className={buttonVariants({ variant: "outline" })}>
                <ArrowLeft aria-hidden />
                Voltar para notas fiscais
              </Link>
            }
          />
        ) : (
          <ErrorNotice error={read.failure} />
        )}
      </div>
    );
  }
  if (!nf) return <TableSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`NF ${nf.numero}`}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <NfStatusBadge status={nf.status} quarentena={nf.quarentena} />
            <span aria-hidden className="h-4 w-px bg-border" />
            <span>NE {nf.nota_empenho_number ?? "sem número"}</span>
          </span>
        }
        action={
          <NfActions
            nf={nf}
            perfil={me.perfil}
            onDone={(next, action) => {
              read.replace(next);
              setAnnouncement(NF_ACTION_DONE[action]);
            }}
            onStale={read.reload}
          />
        }
      />

      <p role="status" className="sr-only">
        {announcement}
      </p>

      {nf.status === "devolvida" && nf.justificativa_devolucao && (
        <p data-testid="nf-justificativa" className="rounded-md border border-border/70 bg-card px-4 py-3 text-sm">
          <span className="block text-xs font-light text-muted-foreground">Devolvida para correção</span>
          {nf.justificativa_devolucao}
        </p>
      )}
      {nf.quarentena && nf.motivo_quarentena && (
        <p data-testid="nf-motivo" className="rounded-md border border-border/70 bg-card px-4 py-3 text-sm">
          <span className="block text-xs font-light text-muted-foreground">Motivo da quarentena</span>
          {nf.motivo_quarentena}
        </p>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Dados da NF</CardTitle>
        </CardHeader>
        <CardContent>
          <dl data-testid="nf-dados" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Item label="Número da NF">
              <span data-testid="nf-numero" className="tabular-nums">
                {nf.numero}
              </span>
            </Item>
            <Item label="Nota de empenho">
              <Link
                href={`/notas-empenho/${nf.nota_empenho_id}`}
                className="text-primary underline-offset-4 [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
              >
                {nf.nota_empenho_number ?? "sem número"}
              </Link>
            </Item>
            <Item label="Data de emissão">{formatDay(nf.data_emissao)}</Item>
            <Item label="Valor">
              <span data-testid="nf-valor" className="tabular-nums">
                {formatBRL(nf.valor)}
              </span>
            </Item>
            <Item label="Registrada em">{formatDate(nf.created_at)}</Item>
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {nf.itens.map((line) => (
              <TableRow key={line.id} data-testid="nf-item">
                <TableCell className="min-w-56">
                  {line.description}
                  <span className="block text-xs font-light text-muted-foreground">
                    {line.sku} · {line.unit}
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatQuantity(line.quantidade)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
    </div>
  );
}
