import type { Metadata } from "next";

import { NfView } from "./nf";

export const metadata: Metadata = { title: "Nota fiscal" };

export default function NfPage() {
  return <NfView />;
}
