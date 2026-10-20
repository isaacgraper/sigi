"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AtaForm } from "@/components/atas/ata-form";
import { FormSkeleton } from "@/components/atas/skeletons";
import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { buttonVariants } from "@/components/ui/button";
import { cached } from "@/lib/api-cache";
import { NOT_EDITABLE } from "@/lib/atas/constants";
import type { AtaDetail } from "@/lib/atas/types";
import { ApiError, unavailable } from "@/lib/errors";
import { apiJson } from "@/lib/session";

/**
 * A reader who opens the address directly. Cosmetic like every perfil check
 * on screen: the API refuses the write whatever this page shows (AC-0013-07).
 */
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

/** /atas/nova (AC-0013-07). */
export function NewAtaPage() {
  const { me } = useSession();
  return (
    <div className="space-y-6">
      <PageHeader title="Nova ATA" description="Preencha os dados da ATA e revise antes de cadastrar." />
      {me.perfil === "gestor" ? <AtaForm /> : <NotAllowed back="/atas" />}
    </div>
  );
}

/** /atas/{id}/editar (AC-0013-14). */
export function EditAtaPage() {
  const { id } = useParams<{ id: string }>();
  const { me, handleSessionError } = useSession();
  const [ata, setAta] = useState<AtaDetail | null>(() => cached<AtaDetail>(`/api/v1/atas/${id}`) ?? null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelled = false;
    apiJson<AtaDetail>(`/api/v1/atas/${id}`)
      .then((value) => !cancelled && setAta(value))
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setFailure(err instanceof ApiError ? err : unavailable());
      });
    return () => {
      cancelled = true;
    };
  }, [id, version, handleSessionError]);

  if (failure && !ata) {
    const missing = failure.status === 404 || failure.status === 422;
    return (
      <div className="space-y-6">
        <PageHeader title={missing ? "ATA não encontrada" : "Editar ATA"} description="Não foi possível abrir a ATA." />
        {missing ? <Missing /> : <ErrorNotice error={failure} />}
      </div>
    );
  }
  if (!ata) return <FormSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title={`Editar ATA ${ata.number}`} description={ata.subject} />
      {/* Remounted on reload, so a stale edit restarts from what the API holds. */}
      {me.perfil !== "gestor" ? (
        <NotAllowed back={`/atas/${ata.id}`} />
      ) : NOT_EDITABLE.includes(ata.status) ? (
        <NotAllowed back={`/atas/${ata.id}`} message="Uma ATA encerrada ou cancelada não pode ser editada." />
      ) : (
        <AtaForm key={version} ata={ata} onStale={reload} />
      )}
    </div>
  );
}

function Missing() {
  return (
    <EmptyState
      message="ATA não encontrada."
      action={
        <Link href="/atas" className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft aria-hidden />
          Voltar para ATAs
        </Link>
      }
    />
  );
}
