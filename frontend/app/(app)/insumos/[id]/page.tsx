import type { Metadata } from "next";

import { InsumoView } from "./insumo";

export const metadata: Metadata = { title: "Insumo" };

export default function InsumoPage() {
  return <InsumoView />;
}
