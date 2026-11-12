import type { Metadata } from "next";

import { NewAtaPage } from "@/components/atas/form-page";

export const metadata: Metadata = { title: "Nova ATA" };

export default function Page() {
  return <NewAtaPage />;
}
