import type { Metadata } from "next";

import { NewInsumoPage } from "@/components/insumos/form-page";

export const metadata: Metadata = { title: "Novo insumo" };

export default function Page() {
  return <NewInsumoPage />;
}
