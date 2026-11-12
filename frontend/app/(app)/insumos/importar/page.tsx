import type { Metadata } from "next";

import { CatalogueImportPage } from "@/components/insumos/import-pages";

export const metadata: Metadata = { title: "Importar catálogo" };

export default function Page() {
  return <CatalogueImportPage />;
}
