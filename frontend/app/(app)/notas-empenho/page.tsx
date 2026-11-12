import type { Metadata } from "next";

import { NotasEmpenho } from "./notas-empenho";

export const metadata: Metadata = { title: "Notas de empenho" };

export default function NotasEmpenhoPage() {
  return <NotasEmpenho />;
}
