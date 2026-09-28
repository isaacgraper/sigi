"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "@/components/session-provider";
import { PERFIL_LABEL } from "@/lib/me";

// The single entry point (AC-0010-52). Until another spec is Approved, it says
// who is signed in and nothing it cannot back with data.
export default function DashboardPage() {
  const { me } = useSession();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Painel</h1>
        <p className="text-sm text-muted-foreground">Bem-vindo ao SIGI.</p>
      </div>
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
