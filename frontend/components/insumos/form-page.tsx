"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { InsumoForm } from "@/components/insumos/insumo-form";
import { InsumoFormSkeleton } from "@/components/insumos/skeletons";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { buttonVariants } from "@/components/ui/button";
import { INSUMO_NOT_FOUND } from "@/lib/insumos/constants";
import type { GrupoNode, InsumoDetail } from "@/lib/insumos/types";
import { useRead } from "@/lib/use-read";

/** /insumos/novo (AC-0014-08). */
export function NewInsumoPage() {
  const { me } = useSession();
  const writes = me.perfil !== "auditor";
  const grupos = useRead<GrupoNode[]>(writes ? "/api/v1/grupos-materiais" : null);
  return (
    <div className="space-y-6">
      <PageHeader title="Novo insumo" description="O SKU identifica o insumo em todas as ATAs e notas." />
      {!writes ? (
        <NotAllowed back="/insumos" />
      ) : grupos.failure ? (
        <ErrorNotice error={grupos.failure} />
      ) : grupos.data ? (
        <InsumoForm tree={grupos.data} />
      ) : (
        <InsumoFormSkeleton />
      )}
    </div>
  );
}

/** /insumos/{id}/editar (AC-0014-10). */
export function EditInsumoPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const writes = me.perfil !== "auditor";
  const insumo = useRead<InsumoDetail>(`/api/v1/insumos/${id}`);
  const grupos = useRead<GrupoNode[]>(writes ? "/api/v1/grupos-materiais" : null);

  const failure = insumo.failure ?? grupos.failure;
  if (failure && !insumo.data) {
    const missing = failure.status === 404 || failure.status === 422;
    return (
      <div className="space-y-6">
        <PageHeader title={missing ? "Insumo não encontrado" : "Editar insumo"} description="Não foi possível abrir o insumo." />
        {missing ? <NotAllowed back="/insumos" message={INSUMO_NOT_FOUND} /> : <ErrorNotice error={failure} />}
      </div>
    );
  }
  if (!insumo.data || (writes && !grupos.data)) return <InsumoFormSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title={`Editar insumo ${insumo.data.sku}`} description={insumo.data.description} />
      {writes && grupos.data ? (
        <InsumoForm insumo={insumo.data} tree={grupos.data} />
      ) : (
        <NotAllowed back={`/insumos/${id}`} />
      )}
    </div>
  );
}

/** A reader who opens the address directly. Cosmetic; the API refuses the write (AC-0014-08). */
function NotAllowed({ back, message = "Seu perfil não permite esta ação." }: { back: string; message?: string }) {
  return (
    <EmptyState
      message={message}
      action={
        <Link href={back} className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft aria-hidden />
          Voltar
        </Link>
      }
    />
  );
}
