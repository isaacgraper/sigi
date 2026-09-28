"use client";

import { Illustration } from "@/components/illustration";

import "./globals.css";

// Replaces the root layout when the layout itself fails, so nothing from it is
// available: no contact provider, hence the generic pointer to the gestor.
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-dvh">
        <main id="content" tabIndex={-1} className="flex min-h-dvh items-center justify-center px-4 focus:outline-none">
          <div className="max-w-md space-y-4 text-center">
            <Illustration name="error" className="mx-auto max-h-60" />
            <h1 className="text-2xl font-normal tracking-tight">Algo deu errado</h1>
            <p className="text-sm font-light text-muted-foreground">
              O SIGI não pôde ser carregado. Tente novamente em instantes ou procure o gestor da
              sua unidade.
            </p>
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-normal text-primary-foreground"
            >
              Tentar novamente
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
