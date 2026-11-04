"use client";

import { useParams } from "next/navigation";

import { NfForm } from "@/components/notas-fiscais/nf-form";

/** /notas-fiscais/{id}/corrigir (AC-0016-09). */
export function Corrigir() {
  const { id } = useParams<{ id: string }>();
  return <NfForm nfId={id} />;
}
