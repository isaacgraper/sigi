"use client";

import { ArrowLeft, Pencil } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { AtaStatus } from "@/components/atas/status";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { InsumoActions } from "@/components/insumos/insumo-actions";
import { InsumoSituacao } from "@/components/insumos/situacao";
import { InsumoSkeleton } from "@/components/insumos/skeletons";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatDay, formatQuantity, formatUnitPrice } from "@/lib/format";
import { EMPTY_VALUE, INSUMO_NOT_FOUND } from "@/lib/insumos/constants";
import { pathText } from "@/lib/insumos/grupos";
import type { InsumoDetail } from "@/lib/insumos/types";
import { useRead } from "@/lib/use-read";

/** The insumo as the API holds it, its ATAs, and the actions on it (AC-0014-12 to -15). */
export function InsumoView() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const read = useRead<InsumoDetail>(`/api/v1/insumos/${id}`);
  // Read by assistive technology only: the page itself shows the result.
  const [announcement, setAnnouncement] = useState("");
  // Hiding the writes is cosmetic; the API refuses them (invariant 8).
  const edits = me.perfil === "gestor" || me.perfil === "servidor";
  const manages = me.perfil === "gestor";

  const failure = read.failure;
  // Unknown and outside a servidor's grupos read the same: both are a 404 (AC-0014-12).
  if (failure && (failure.status === 404 || failure.status === 422)) {
    return (
      <div className="space-y-6">
        <PageHeader title="Insumo não encontrado" description="O endereço não corresponde a nenhum insumo que você possa ver." />
        <EmptyState
          message={INSUMO_NOT_FOUND}
          action={
            <Link href="/insumos" className={buttonVariants({ variant: "outline" })}>
              <ArrowLeft aria-hidden />
              Voltar para Insumos
            </Link>
          }
        />
      </div>
    );
  }
  if (failure && !read.data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Insumo" description="Não foi possível carregar o insumo." />
        <ErrorNotice error={failure} />
      </div>
    );
  }
  const insumo = read.data;
  if (!insumo) return <InsumoSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={insumo.sku}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <InsumoSituacao insumo={insumo} />
            <span aria-hidden className="h-4 w-px bg-border" />
            <span>{insumo.description}</span>
          </span>
        }
        action={
          edits ? (
            <div data-testid="insumo-actions" className="flex flex-wrap gap-2">
              <Link href={`/insumos/${insumo.id}/editar`} className={buttonVariants({ variant: "outline" })}>
                <Pencil aria-hidden />
                Editar
              </Link>
              {manages && (
                <InsumoActions
                  insumo={insumo}
                  onChanged={(next, message) => {
                    read.replace(next);
                    setAnnouncement(message);
                  }}
                />
              )}
            </div>
          ) : undefined
        }
      />

      <p role="status" className="sr-only">
        {announcement}
      </p>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Dados do insumo</CardTitle>
        </CardHeader>
        <CardContent>
          <dl data-testid="insumo-dados" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Item label="Descrição">{insumo.description}</Item>
            <Item label="Unidade">{insumo.unit}</Item>
            <Item label="Grupo">{pathText(insumo.grupo_path)}</Item>
            <Item label="Código DOMS">
              <span className="font-mono text-xs">{insumo.codigo_doms ?? EMPTY_VALUE}</span>
            </Item>
            <Item label="Código externo">
              <span className="font-mono text-xs">{insumo.external_code ?? EMPTY_VALUE}</span>
            </Item>
            <Item label="Quantidade de referência">
              <span className="tabular-nums">
                {insumo.reference_quantity ? formatQuantity(insumo.reference_quantity) : EMPTY_VALUE}
              </span>
            </Item>
            <Item label="Cadastrado em">
              <span className="tabular-nums">{formatDate(insumo.created_at)}</span>
            </Item>
            {insumo.discontinued_on && (
              <Item label="Descontinuado em">
                <span className="tabular-nums">{formatDay(insumo.discontinued_on)}</span>
              </Item>
            )}
            {insumo.substitute && (
              <Item label="Substituído por">
                <Link
                  href={`/insumos/${insumo.substitute.id}`}
                  className="text-primary underline-offset-4 [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                >
                  <span className="font-mono text-xs">{insumo.substitute.sku}</span> · {insumo.substitute.description}
                </Link>
              </Item>
            )}
          </dl>
        </CardContent>
      </Card>

      <section aria-label="ATAs" className="space-y-3">
        <h2 className="text-base font-normal">ATAs</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ATA</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Quantidade</TableHead>
              <TableHead className="whitespace-nowrap text-right">Valor unitário</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {insumo.atas.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="py-6 text-center font-light text-muted-foreground">
                  Este insumo não é item de nenhuma ATA.
                </TableCell>
              </TableRow>
            )}
            {insumo.atas.map((ata) => (
              <TableRow key={ata.item_id} data-testid="insumo-ata-row">
                <TableCell className="whitespace-nowrap">
                  <Link
                    href={`/atas/${ata.ata_id}`}
                    className="text-primary underline-offset-4 [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                  >
                    {ata.ata_number}
                  </Link>
                </TableCell>
                <TableCell>
                  {/* The situação of the vigência is the ATA page's; here the status is enough. */}
                  <AtaStatus ata={{ status: ata.ata_status, situacao_vigencia: "vigente" }} />
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatQuantity(ata.quantity)}</TableCell>
                <TableCell className="whitespace-nowrap text-right tabular-nums">{formatUnitPrice(ata.unit_price)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
    </div>
  );
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs font-light text-muted-foreground">{label}</dt>
      <dd className="break-words text-sm">{children}</dd>
    </div>
  );
}
