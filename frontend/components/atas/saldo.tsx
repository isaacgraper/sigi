"use client";

import { Plus } from "lucide-react";
import Link from "next/link";

import { ErrorNotice } from "@/components/error-notice";
import { Status } from "@/components/ui/status";
import { buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBRL, formatDate, formatQuantity } from "@/lib/format";
import type { SaldoAta, SaldoItens } from "@/lib/notas-empenho/types";
import { useRead } from "@/lib/use-read";

/** What is left, with what is held in reserve in parentheses: "700 (300)" (SPEC-0006 AC-0006-13). */
function WithReserve({ left, reserved, format }: { left: string; reserved: string; format: (v: string) => string }) {
  return (
    <span className="tabular-nums">
      {format(left)}
      {Number(reserved) > 0 && (
        <span data-testid="saldo-reservado" className="text-attention">
          {" "}
          ({format(reserved)})
        </span>
      )}
    </span>
  );
}

/**
 * The saldo of an ATA, in value and per item in quantity (AC-0015-10). Summed
 * by the API on every read; the screen only shows it, with the instant it was
 * summed (AC-0006-09).
 */
export function SaldoSection({ ataId, opens, version }: { ataId: string; opens: boolean; version: number }) {
  const value = useRead<SaldoAta>(`/api/v1/atas/${ataId}/saldo?v=${version}`);
  const items = useRead<SaldoItens>(`/api/v1/atas/${ataId}/itens/saldo?v=${version}`);
  const s = value.data;

  return (
    <section aria-label="Saldo" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-normal">Saldo</h2>
        {opens && (
          <Link href={`/notas-empenho/nova?ata=${ataId}`} className={buttonVariants({ variant: "outline" })}>
            <Plus aria-hidden />
            Abrir NE
          </Link>
        )}
      </div>
      {value.failure && !s && <ErrorNotice error={value.failure} />}
      {s && (
        <div className="space-y-1">
          <dl className="grid grid-cols-2 gap-3 sm:flex">
            <div data-testid="saldo-disponivel" className="rounded-md border border-border/70 bg-card px-4 py-3 shadow-sm sm:min-w-52">
              <dt className="text-xs font-light text-muted-foreground">Saldo disponível (reservado)</dt>
              <dd className="text-xl font-normal leading-tight">
                <WithReserve left={s.saldo_disponivel} reserved={s.valor_reservado} format={formatBRL} />
              </dd>
            </div>
            <div className="rounded-md border border-border/70 bg-card px-4 py-3 shadow-sm sm:min-w-40">
              <dt className="text-xs font-light text-muted-foreground">Empenhado</dt>
              <dd className="text-xl font-normal leading-tight tabular-nums">{formatBRL(s.valor_empenhado)}</dd>
            </div>
            <div data-testid="saldo-comprometimento" className="rounded-md border border-border/70 bg-card px-4 py-3 shadow-sm sm:min-w-40">
              <dt className="text-xs font-light text-muted-foreground">Comprometido</dt>
              <dd className="text-xl font-normal leading-tight tabular-nums">
                {s.alto_consumo ? (
                  <Status tone="danger" className="text-xl">
                    {formatQuantity(s.comprometimento_percentual)}%
                  </Status>
                ) : (
                  `${formatQuantity(s.comprometimento_percentual)}%`
                )}
              </dd>
            </div>
          </dl>
          <p className="text-xs font-light text-muted-foreground">Calculado em {formatDate(s.calculado_em)}.</p>
        </div>
      )}
      {items.data && items.data.items.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Insumo</TableHead>
              <TableHead className="whitespace-nowrap text-right">Contratada</TableHead>
              <TableHead className="whitespace-nowrap text-right">Disponível (reservada)</TableHead>
              <TableHead className="whitespace-nowrap text-right">Empenhada</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.data.items.map((item) => (
              <TableRow key={item.item_ata_id} data-testid="saldo-item">
                <TableCell className="min-w-56">
                  {item.description}
                  <span className="block text-xs font-light text-muted-foreground">
                    {item.sku} · {item.unit}
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatQuantity(item.quantidade_contratada)}</TableCell>
                <TableCell data-testid="saldo-item-disponivel" className="whitespace-nowrap text-right">
                  {item.esgotado ? (
                    <Status tone="danger">Esgotado</Status>
                  ) : (
                    <WithReserve left={item.quantidade_disponivel} reserved={item.quantidade_reservada} format={formatQuantity} />
                  )}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatQuantity(item.quantidade_empenhada)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
