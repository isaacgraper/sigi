import type { Metadata } from "next";
import { connection } from "next/server";
import { Toaster } from "sonner";

import { ContactProvider } from "@/components/contact";
import { SkipLink } from "@/components/skip-link";

import "./globals.css";

export const metadata: Metadata = {
  // Every page names itself first: "Membros · SIGI" (AC-0011-11).
  title: { template: "%s · SIGI", default: "SIGI" },
  description: "Sistema Integrado de Governança de Insumos",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // Every page renders per request, so each gets its own CSP nonce
  // (AC-0010-53). A prerendered page would carry no nonce and its scripts
  // would be blocked.
  await connection();
  const contact = process.env.SUPPORT_CONTACT_EMAIL?.trim() || null;
  return (
    <html lang="pt-BR">
      <body className="min-h-dvh">
        <SkipLink />
        <ContactProvider email={contact}>
          {children}
          <Toaster richColors position="top-right" />
        </ContactProvider>
      </body>
    </html>
  );
}
