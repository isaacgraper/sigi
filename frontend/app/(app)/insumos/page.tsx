import type { Metadata } from "next";

import { Insumos } from "./insumos";

export const metadata: Metadata = { title: "Insumos" };

export default function InsumosPage() {
  return <Insumos />;
}
