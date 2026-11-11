"use client";

import { PageHeader } from "@/components/page-header";
import { ExportDialog } from "@/components/relatorios/export-dialog";
import { useSession } from "@/components/session-provider";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { canReadHistory } from "@/lib/me";
import { RELATORIOS_DENIED, REPORTS } from "@/lib/relatorios/constants";

/** /relatorios: the four reports of RF12, each exported through one dialog (SPEC-0018). */
export function Relatorios() {
  const { me } = useSession();
  // The same perfis read the reports as the whole history (SPEC-0009 AC-0009-05).
  const allowed = canReadHistory(me.perfil);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Relatórios"
        description="Os relatórios da prestação de contas, em CSV ou PDF, como estavam na data de referência."
      />
      {!allowed && (
        <p data-testid="relatorios-negado" role="status" className="rounded-md border border-border/70 bg-card px-4 py-3 text-sm">
          {RELATORIOS_DENIED}
        </p>
      )}
      {allowed && (
        <ul className="grid gap-4 sm:grid-cols-2">
          {REPORTS.map((report) => (
            <li key={report.key} data-testid="relatorio" data-relatorio={report.key}>
              <Card className="flex h-full flex-col">
                <CardHeader className="pb-2">
                  <CardTitle>{report.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col justify-between gap-4">
                  <p className="text-sm font-light text-muted-foreground">{report.description}</p>
                  <div>
                    <ExportDialog
                      relatorio={report.key}
                      title={report.name.toLowerCase()}
                      filtros={{}}
                      withAta
                      withPeriod={report.period}
                    />
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
