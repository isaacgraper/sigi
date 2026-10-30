"use client";

import { ArrowLeft, Pencil } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ItemsSection } from "@/components/atas/items";
import { SaldoSection } from "@/components/atas/saldo";
import { AtaStatus } from "@/components/atas/status";
import { MoveActions } from "@/components/atas/move-actions";
import { AditivoDialog, ReajusteDialog } from "@/components/atas/record-dialogs";
import { AtaSkeleton } from "@/components/atas/skeletons";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cached, remember } from "@/lib/api-cache";
import { ADITIVO_KIND_LABEL, MOVE, NOT_EDITABLE } from "@/lib/atas/constants";
import type { Aditivo, AtaDetail } from "@/lib/atas/types";
import { ApiError, unavailable } from "@/lib/errors";
import { formatBRL, formatCnpj, formatDate, formatDay, formatQuantity } from "@/lib/format";
import type { Items } from "@/lib/insumos/types";
import { apiJson } from "@/lib/session";
import { useRead } from "@/lib/use-read";

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs font-light text-muted-foreground">{label}</dt>
      <dd className="break-words text-sm">{children}</dd>
    </div>
  );
}

function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-normal">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

/** The ATA as the API holds it, and the gestor's actions on it (AC-0013-10 to -17). */
export function AtaView() {
  const { id } = useParams<{ id: string }>();
  const { me, handleSessionError } = useSession();
  // An ATA seen before, or warmed from its link, draws at once and refreshes.
  const [ata, setAta] = useState<AtaDetail | null>(() => cached<AtaDetail>(`/api/v1/atas/${id}`) ?? null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  // Read by assistive technology only: the page itself shows the result (AC-0013-12).
  const [announcement, setAnnouncement] = useState("");
  const [version, setVersion] = useState(0);
  // Hiding the writes is cosmetic; the API refuses them (AC-0013-17, invariant 8).
  const writes = me.perfil === "gestor";

  // The items are a block of their own: a servidor reads its grupos' share (AC-0014-21, -22).
  const items = useRead<Items>(`/api/v1/atas/${id}/itens`);
  const reloadItems = items.reload;
  const reload = useCallback(() => {
    setVersion((v) => v + 1);
    reloadItems();
  }, [reloadItems]);

  useEffect(() => {
    let cancelled = false;
    apiJson<AtaDetail>(`/api/v1/atas/${id}`)
      .then((value) => {
        if (cancelled) return;
        setAta(value);
        setFailure(null);
      })
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setFailure(err instanceof ApiError ? err : unavailable());
      });
    return () => {
      cancelled = true;
    };
  }, [id, version, handleSessionError]);

  function changed(next: AtaDetail, message: string) {
    setAta(remember(`/api/v1/atas/${next.id}`, next));
    setAnnouncement(message);
  }

  // A malformed id never reaches a row either; to the person it is the same ATA that is not there.
  if (failure && (failure.code === "NOT_FOUND" || failure.status === 404 || failure.status === 422)) {
    return (
      <div className="space-y-6">
        <PageHeader title="ATA não encontrada" description="O endereço não corresponde a nenhuma ATA." />
        <EmptyState
          message="ATA não encontrada."
          action={
            <Link href="/atas" className={buttonVariants({ variant: "outline" })}>
              <ArrowLeft aria-hidden />
              Voltar para ATAs
            </Link>
          }
        />
      </div>
    );
  }

  if (failure && !ata) {
    return (
      <div className="space-y-6">
        <PageHeader title="ATA" description="Não foi possível carregar a ATA." />
        <ErrorNotice error={failure} />
      </div>
    );
  }

  if (!ata) return <AtaSkeleton />;

  const vigente = ata.status === "vigente";
  return (
    <div className="space-y-6">
      <PageHeader
        title={`ATA ${ata.number}`}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <AtaStatus ata={ata} />
            <span aria-hidden className="h-4 w-px bg-border" />
            <span>{ata.subject}</span>
          </span>
        }
        action={
          writes ? (
            <div data-testid="ata-actions" className="flex flex-wrap gap-2">
              {!NOT_EDITABLE.includes(ata.status) && (
                <Link href={`/atas/${ata.id}/editar`} className={buttonVariants({ variant: "outline" })}>
                  <Pencil aria-hidden />
                  Editar
                </Link>
              )}
              <MoveActions ata={ata} onMoved={(next, move) => changed(next, MOVE[move].done)} onStale={reload} />
            </div>
          ) : undefined
        }
      />

      <p role="status" className="sr-only">
        {announcement}
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Dados da ATA</CardTitle>
        </CardHeader>
        <CardContent>
          <dl data-testid="ata-dados" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Item label="Objeto">{ata.subject}</Item>
            <Item label="Órgão">{ata.organ}</Item>
            <Item label="Fornecedor">
              {ata.fornecedor.legal_name}
              <span className="block text-xs font-light tabular-nums text-muted-foreground">
                CNPJ {formatCnpj(ata.fornecedor.cnpj)}
              </span>
            </Item>
            <Item label="Data de emissão">{ata.issued_on ? formatDay(ata.issued_on) : "—"}</Item>
            <Item label="Vigência">
              <span className="tabular-nums">
                {formatDay(ata.vigencia_inicio)} a {formatDay(ata.vigencia_fim)}
              </span>
            </Item>
            <Item label="Valor total">
              <span className="tabular-nums">{formatBRL(ata.total_value)}</span>
            </Item>
            <Item label="Valor contratado">
              <span className="tabular-nums">{formatBRL(ata.valor_contratado)}</span>
            </Item>
            <Item label="Data do orçamento planilhado">
              <span className="tabular-nums">{formatDay(ata.budget_date)}</span>
            </Item>
            <Item label="Data de reajuste">
              <span className="tabular-nums">{formatDay(ata.data_reajuste)}</span>
            </Item>
          </dl>
        </CardContent>
      </Card>

      <SaldoSection ataId={ata.id} opens={writes && vigente} version={version} />

      <ItemsSection
        ata={ata}
        items={items.data}
        failure={items.failure}
        writes={writes}
        scoped={me.perfil === "servidor"}
        onItems={(next, message) => {
          items.replace(next);
          setAnnouncement(message);
        }}
        onAta={(next, message) => {
          changed(next, message);
          // An aditivo de quantidade raises its item's contracted quantity (AC-0014-25).
          items.reload();
        }}
        onStale={reload}
      />

      <Section
        title="Aditivos"
        action={writes && vigente ? <AditivoDialog ata={ata} onSaved={(next) => changed(next, "Aditivo registrado.")} /> : undefined}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tipo</TableHead>
              <TableHead className="whitespace-nowrap">Acréscimo ou novo fim</TableHead>
              <TableHead>Justificativa</TableHead>
              <TableHead className="whitespace-nowrap">Registrado em</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ata.aditivos.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-6 text-center font-light text-muted-foreground">
                  Nenhum aditivo registrado.
                </TableCell>
              </TableRow>
            )}
            {ata.aditivos.map((aditivo) => (
              <TableRow key={aditivo.id} data-testid="aditivo-row">
                <TableCell>{ADITIVO_KIND_LABEL[aditivo.kind]}</TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{aditivoText(aditivo, items.data)}</TableCell>
                <TableCell className="min-w-56">{aditivo.justification}</TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{formatDate(aditivo.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Section>

      <Section
        title="Pedidos de reajuste"
        action={
          writes && vigente ? (
            <ReajusteDialog ata={ata} onSaved={(next) => changed(next, "Pedido de reajuste registrado.")} />
          ) : undefined
        }
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="whitespace-nowrap">Processo SEI</TableHead>
              <TableHead className="whitespace-nowrap">Data do pedido</TableHead>
              <TableHead className="whitespace-nowrap">Registrado em</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ata.reajustes.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="py-6 text-center font-light text-muted-foreground">
                  Nenhum pedido de reajuste registrado.
                </TableCell>
              </TableRow>
            )}
            {ata.reajustes.map((reajuste) => (
              <TableRow key={reajuste.id} data-testid="reajuste-row">
                <TableCell className="whitespace-nowrap tabular-nums">{reajuste.processo_sei}</TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{formatDay(reajuste.requested_on)}</TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{formatDate(reajuste.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Section>
    </div>
  );
}

/**
 * What an aditivo added: money, a new end, or "+20 UN · CLORDEG21" for a quantity
 * (AC-0014-26). An item outside a servidor's grupos is not in its items, so only
 * the quantity shows.
 */
function aditivoText(aditivo: Aditivo, items: Items | null): string {
  if (aditivo.kind === "valor" && aditivo.valor_acrescimo) return formatBRL(aditivo.valor_acrescimo);
  if (aditivo.kind === "prazo" && aditivo.nova_vigencia_fim) return formatDay(aditivo.nova_vigencia_fim);
  if (aditivo.kind === "quantidade" && aditivo.quantity) {
    const item = items?.items.find((candidate) => candidate.id === aditivo.item_id);
    const added = `+${formatQuantity(aditivo.quantity)}`;
    return item ? `${added} ${item.insumo.unit} · ${item.insumo.sku}` : added;
  }
  return "—";
}
