import type { Metadata } from "next";

import { NeForm } from "@/components/notas-empenho/ne-form";

export const metadata: Metadata = { title: "Abrir NE" };

export default function Page() {
  return <NeForm />;
}
