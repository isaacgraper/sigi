"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { InviteDialog } from "@/components/members/invite-dialog";
import { MemberActions } from "@/components/members/member-actions";
import { type MemberPage, STATUS_LABEL, STATUS_TONE } from "@/components/members/types";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, unavailable } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import { PERFIL_LABEL } from "@/lib/me";
import { apiJson } from "@/lib/session";

const SIZE = 20;

function pageFrom(raw: string | null): number {
  const value = Number.parseInt(raw ?? "1", 10);
  return Number.isFinite(value) && value > 0 ? value : 1;
}

export function Members() {
  const { me, handleSessionError } = useSession();
  const router = useRouter();
  const page = pageFrom(useSearchParams().get("page"));

  const [data, setData] = useState<MemberPage | null>(null);
  const [refusal, setRefusal] = useState<ApiError | null>(null);
  const [actionError, setActionError] = useState<ApiError | null>(null);
  const [version, setVersion] = useState(0);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  // Only a gestor manages; hiding the controls is cosmetic, the API enforces
  // it (C2, AC-0010-32).
  const manages = me.perfil === "gestor";

  useEffect(() => {
    let cancelled = false;
    apiJson<MemberPage>(`/api/v1/usuarios?page=${page}&size=${SIZE}`)
      .then((value) => {
        if (cancelled) return;
        setData(value);
        setRefusal(null);
      })
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setRefusal(err instanceof ApiError ? err : unavailable());
      });
    return () => {
      cancelled = true;
    };
  }, [page, version, handleSessionError]);

  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Membros"
        description="Quem tem acesso ao SIGI."
        action={manages && !refusal ? <InviteDialog onInvited={reload} /> : undefined}
      />

      {refusal && <ErrorNotice error={refusal} />}
      {actionError && (
        <div data-testid="page-error">
          <ErrorNotice error={actionError} />
        </div>
      )}

      {!data && !refusal && (
        <div role="status">
          <span className="sr-only">Carregando...</span>
          <TableSkeleton />
        </div>
      )}

      {data && !refusal && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>Perfil</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Criado em</TableHead>
                {manages && <TableHead className="w-12"><span className="sr-only">Ações</span></TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={manages ? 6 : 5}>
                    <EmptyState
                      message="Nenhum membro encontrado."
                      action={
                        data.total > 0 ? (
                          // Past the last page: the rows exist, on page one.
                          <Link href="/members" className={buttonVariants({ variant: "outline" })}>
                            Voltar à primeira página
                          </Link>
                        ) : manages ? (
                          <InviteDialog onInvited={reload} label="Convidar o primeiro membro" variant="outline" />
                        ) : undefined
                      }
                    />
                  </TableCell>
                </TableRow>
              )}
              {data.items.map((member) => (
                <TableRow key={member.id} data-testid="member-row" data-member-id={member.id}>
                  {/* A deactivated member is known by the pseudonym (AC-0010-31, C4). */}
                  <TableCell data-testid="cell-name" className="font-medium">
                    {member.status === "desativado" ? member.pseudonym ?? "—" : member.name ?? "—"}
                  </TableCell>
                  <TableCell data-testid="cell-email" className="break-all">
                    {member.email ?? "—"}
                  </TableCell>
                  <TableCell>{PERFIL_LABEL[member.perfil]}</TableCell>
                  <TableCell>
                    <Badge tone={STATUS_TONE[member.status]} data-testid="cell-status">
                      {STATUS_LABEL[member.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{formatDate(member.created_at)}</TableCell>
                  {manages && (
                    <TableCell className="text-right">
                      <MemberActions
                        member={member}
                        onChanged={() => {
                          setActionError(null);
                          reload();
                        }}
                        onError={setActionError}
                      />
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <nav aria-label="Paginação" className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Página {page} de {lastPage} · {data.total} membros
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => router.push(`/members?page=${page - 1}`)}
              >
                <ChevronLeft aria-hidden />
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= lastPage}
                onClick={() => router.push(`/members?page=${page + 1}`)}
              >
                Próxima
                <ChevronRight aria-hidden />
              </Button>
            </div>
          </nav>
        </>
      )}
    </div>
  );
}
