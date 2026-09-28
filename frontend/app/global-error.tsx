"use client";

import "./globals.css";

// Replaces the root layout when the layout itself fails, so nothing from it is
// available: no contact provider, hence the generic pointer to the gestor.
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-dvh">
        <main className="flex min-h-dvh items-center justify-center px-4">
          <div className="max-w-md space-y-4 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">Algo deu errado</h1>
            <p className="text-sm text-muted-foreground">
              O SIGI não pôde ser carregado. Tente novamente em instantes ou procure o gestor da
              sua unidade.
            </p>
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
            >
              Tentar novamente
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
