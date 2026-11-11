import type { Metadata } from "next";

import { Historico } from "./historico";

export const metadata: Metadata = { title: "Histórico" };

export default function HistoricoPage() {
  return <Historico />;
}
