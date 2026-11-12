import type { Metadata } from "next";

import { EditAtaPage } from "@/components/atas/form-page";

export const metadata: Metadata = { title: "Editar ATA" };

export default function Page() {
  return <EditAtaPage />;
}
