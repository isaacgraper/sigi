import { ShieldCheck } from "lucide-react";

import { Illustration } from "@/components/illustration";

/**
 * The frame every signed-out page shares (AC-0011-15, DESIGN.md §3): a navy
 * panel with the brand, one sentence and the login illustration from 1024 px,
 * and only the form below that.
 */
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside
        data-testid="brand-panel"
        className="hidden flex-col justify-between gap-10 bg-primary p-10 text-primary-foreground lg:flex"
      >
        <div className="flex items-center gap-2 text-lg font-normal">
          <ShieldCheck aria-hidden className="size-6" />
          SIGI
        </div>
        <Illustration name="login" className="mx-auto max-h-72" />
        <div className="max-w-md space-y-2">
          <p className="text-2xl font-normal tracking-tight">Da ATA à conclusão, cada etapa rastreável.</p>
          <p className="text-sm font-light text-sidebar-muted">Sistema Integrado de Governança de Insumos</p>
        </div>
      </aside>
      <main
        id="content"
        tabIndex={-1}
        className="flex items-center justify-center px-4 py-12 focus:outline-none sm:px-8"
      >
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
      data-testid="form-error"
      className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger"
    >
      {children}
    </p>
  );
}

export function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p role="status" className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
      {children}
    </p>
  );
}
