import type { Metadata } from "next";

import { Relatorios } from "./relatorios";

export const metadata: Metadata = { title: "Relatórios" };

export default function RelatoriosPage() {
  return <Relatorios />;
}
