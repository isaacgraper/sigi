import type { Metadata } from "next";

import { GruposPage } from "@/components/insumos/grupos-page";

export const metadata: Metadata = { title: "Grupos de materiais" };

export default function Page() {
  return <GruposPage />;
}
