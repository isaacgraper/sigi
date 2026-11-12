import type { Metadata } from "next";

import { NotasFiscais } from "./notas-fiscais";

export const metadata: Metadata = { title: "Notas fiscais" };

export default function NotasFiscaisPage() {
  return <NotasFiscais />;
}
