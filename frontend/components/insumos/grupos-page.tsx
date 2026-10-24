"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { GrupoTree } from "@/components/insumos/grupo-tree";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { buttonVariants } from "@/components/ui/button";
import type { GrupoNode } from "@/lib/insumos/types";
import { useRead } from "@/lib/use-read";

/** /insumos/grupos (AC-0014-16, -17). A servidor sees its own grupos and those below them. */
export function GruposPage() {
  const { me } = useSession();
  const tree = useRead<GrupoNode[]>("/api/v1/grupos-materiais");
  const [announcement, setAnnouncement] = useState("");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Grupos de materiais"
        description="Grupo, subgrupo e classificação, como no DOMS."
        action={
          <Link href="/insumos" className={buttonVariants({ variant: "outline" })}>
            <ArrowLeft aria-hidden />
            Voltar para Insumos
          </Link>
        }
      />
      <p role="status" className="sr-only">
        {announcement}
      </p>
      {tree.failure && <ErrorNotice error={tree.failure} />}
      {!tree.data && !tree.failure && (
        <div role="status">
          <span className="sr-only">Carregando...</span>
          <TableSkeleton />
        </div>
      )}
      {tree.data && (
        <GrupoTree
          tree={tree.data}
          manages={me.perfil === "gestor"}
          onChanged={(message) => {
            setAnnouncement(message);
            tree.reload();
          }}
        />
      )}
    </div>
  );
}
