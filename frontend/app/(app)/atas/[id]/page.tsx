import type { Metadata } from "next";

import { AtaView } from "./ata";

export const metadata: Metadata = { title: "ATA" };

export default function AtaPage() {
  return <AtaView />;
}
