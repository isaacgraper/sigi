import type { Metadata } from "next";
import { connection } from "next/server";
import { Toaster } from "sonner";

import "./globals.css";

export const metadata: Metadata = {
  title: "SIGI",
  description: "Sistema Integrado de Governança de Insumos",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Every page renders per request, so each gets its own CSP nonce
  // (AC-0010-53). A prerendered page would carry no nonce and its scripts
  // would be blocked.
  await connection();
  return (
    <html lang="pt-BR">
      <body className="min-h-dvh">
        {children}
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
