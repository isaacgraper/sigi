import type { Metadata } from "next";

import { EditInsumoPage } from "@/components/insumos/form-page";

export const metadata: Metadata = { title: "Editar insumo" };

export default function Page() {
  return <EditInsumoPage />;
}
