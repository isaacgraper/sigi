import type { Metadata } from "next";

import { Configuracoes } from "./configuracoes";

export const metadata: Metadata = { title: "Configurações" };

export default function ConfiguracoesPage() {
  return <Configuracoes />;
}
