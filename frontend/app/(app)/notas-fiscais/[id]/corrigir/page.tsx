import type { Metadata } from "next";

import { Corrigir } from "./corrigir";

export const metadata: Metadata = { title: "Corrigir NF" };

export default function Page() {
  return <Corrigir />;
}
