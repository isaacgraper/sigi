"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { ImportFlow } from "@/components/insumos/import-flow";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { PageSkeleton } from "@/components/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { NOT_EDITABLE } from "@/lib/atas/constants";
import type { AtaDetail } from "@/lib/atas/types";
import { useRead } from "@/lib/use-read";

/** /insumos/importar (AC-0014-18, -19). */
export function CatalogueImportPage() {
  const { me } = useSession();
  return (
    <div className="space-y-6">
      <PageHeader
        title="Importar catálogo"
        description="Cada linha cria o insumo do SKU, ou o atualiza quando o SKU já existe. Nada é gravado antes de você confirmar."
      />
      {me.perfil === "gestor" ? (
        <ImportFlow
          target="catalogue"
          path="/api/v1/insumos/importacao"
          done={{ href: "/insumos", label: "Ver o catálogo" }}
        />
      ) : (
        <Back href="/insumos" message="Seu perfil não permite esta ação." />
      )}
    </div>
  );
}

/** /atas/{id}/itens/importar (AC-0014-20). */
export function ItemsImportPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const ata = useRead<AtaDetail>(`/api/v1/atas/${id}`);

  if (ata.failure && !ata.data) {
    return (
      <div className="space-y-6">
        <PageHeader title="Importar itens" description="Não foi possível abrir a ATA." />
        <ErrorNotice error={ata.failure} />
      </div>
    );
  }
  if (!ata.data) return <PageSkeleton rows={2} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Importar itens da ATA ${ata.data.number}`}
        description="Cada linha adiciona o item do SKU, ou o corrige quando a ATA já o tem. Itens fora do arquivo ficam como estão."
      />
      {me.perfil !== "gestor" ? (
        <Back href={`/atas/${id}`} message="Seu perfil não permite esta ação." />
      ) : NOT_EDITABLE.includes(ata.data.status) ? (
        <Back href={`/atas/${id}`} message="Uma ATA encerrada ou cancelada não pode ser editada." />
      ) : (
        <ImportFlow
          target="items"
          path={`/api/v1/atas/${id}/itens/importacao`}
          done={{ href: `/atas/${id}`, label: "Voltar para a ATA" }}
        />
      )}
    </div>
  );
}

/** A reader, or an ATA that takes no item. Cosmetic; the API refuses the import. */
function Back({ href, message }: { href: string; message: string }) {
  return (
    <EmptyState
      message={message}
      action={
        <Link href={href} className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft aria-hidden />
          Voltar
        </Link>
      }
    />
  );
}
