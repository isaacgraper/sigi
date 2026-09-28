"use client";

import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PERFIL_LABEL } from "@/lib/me";
import { modulesFor } from "@/lib/modules";

// The single entry point (AC-0010-52): one tile per module the perfil is shown
// (AC-0011-13), and who is signed in (AC-0010-28). Nothing it cannot back with
// data, so no figures until the API serves one.
export function Dashboard() {
  const { me } = useSession();
  const modules = modulesFor(me);

  return (
    <div className="space-y-6">
      <PageHeader title="Painel" description="Bem-vindo ao SIGI." />

      <section aria-labelledby="modules-title" className="space-y-3">
        <h2 id="modules-title" className="text-base font-semibold">
          Módulos
        </h2>
        {modules.length === 0 ? (
          <p data-testid="no-modules" className="rounded-lg border border-dashed bg-card px-4 py-6 text-sm text-muted-foreground">
            Os módulos do SIGI aparecerão aqui conforme forem liberados.
          </p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {modules.map((module) => {
              const Icon = module.icon;
              return (
                <li key={module.href}>
                  <Link
                    href={module.href}
                    data-testid="module-tile"
                    className="flex h-full items-start gap-4 rounded-lg border bg-card p-5 shadow-sm transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Icon aria-hidden className="size-5" />
                    </span>
                    <span className="min-w-0">
                      <span className="block font-semibold">{module.name}</span>
                      <span className="block text-sm text-muted-foreground">{module.description}</span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Sua conta</CardTitle>
          <CardDescription>Dados da sessão atual.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            {me.name && (
              <>
                <dt className="text-muted-foreground">Nome</dt>
                <dd data-testid="me-name">{me.name}</dd>
              </>
            )}
            <dt className="text-muted-foreground">E-mail</dt>
            <dd data-testid="me-email" className="break-all">
              {me.email ?? "—"}
            </dd>
            <dt className="text-muted-foreground">Perfil</dt>
            <dd data-testid="me-perfil">{PERFIL_LABEL[me.perfil]}</dd>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
