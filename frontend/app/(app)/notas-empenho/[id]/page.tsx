import type { Metadata } from "next";

import { NeView } from "./ne";

export const metadata: Metadata = { title: "Nota de empenho" };

export default function NePage() {
  return <NeView />;
}
