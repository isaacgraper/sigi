import type { Metadata } from "next";

import { NfForm } from "@/components/notas-fiscais/nf-form";

export const metadata: Metadata = { title: "Registrar NF" };

export default function Page() {
  return <NfForm />;
}
