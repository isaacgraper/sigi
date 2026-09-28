import { ShieldCheck } from "lucide-react";

/** The split-screen frame every signed-out page shares (design reference §4.8). */
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-primary p-10 text-primary-foreground lg:flex">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <ShieldCheck aria-hidden className="size-6" />
          SIGI
        </div>
        <div className="max-w-md space-y-3">
          <p className="text-2xl font-semibold tracking-tight">
            Sistema Integrado de Governança de Insumos
          </p>
          <p className="text-sm text-primary-foreground/80">
            Da ATA à conclusão, cada etapa rastreável.
          </p>
        </div>
        <p className="text-xs text-primary-foreground/70">Acesso restrito a servidores autorizados.</p>
      </aside>
      <main className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}

export function FormMessage({ children, id }: { children: React.ReactNode; id?: string }) {
  return (
    <p
      id={id}
      role="alert"
      className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      {children}
    </p>
  );
}

export function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p role="status" className="rounded-md border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-accent">
      {children}
    </p>
  );
}
