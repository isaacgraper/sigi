import type { Metadata } from "next";
import { Toaster } from "sonner";

import "./globals.css";

export const metadata: Metadata = {
  title: "SIGI",
  description: "Sistema Integrado de Governança de Insumos",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-dvh">
        {children}
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
