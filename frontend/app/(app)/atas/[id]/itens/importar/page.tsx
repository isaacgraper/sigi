import type { Metadata } from "next";

import { ItemsImportPage } from "@/components/insumos/import-pages";

export const metadata: Metadata = { title: "Importar itens" };

export default function Page() {
  return <ItemsImportPage />;
}
