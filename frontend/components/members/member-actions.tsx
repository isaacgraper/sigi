"use client";

import { Ban, KeyRound, MoreHorizontal, UserX } from "lucide-react";
import { useState } from "react";

import { CopyLink } from "@/components/members/copy-link";
import type { Member } from "@/components/members/types";
import { useSession } from "@/components/session-provider";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ApiError, GENERIC_FAILURE } from "@/lib/errors";
import { displayName } from "@/lib/me";
import { apiJson } from "@/lib/session";

type Action = "bloquear" | "desativar" | "redefinir-senha";

const CONFIRM: Record<Action, { title: string; body: string; label: string; destructive: boolean }> = {
  bloquear: {
    title: "Bloquear membro?",
    body: "As sessões abertas desta pessoa são encerradas e ela não consegue mais entrar.",
    label: "Bloquear",
    destructive: true,
  },
  desativar: {
    title: "Desativar membro?",
    body: "Nome e e-mail serão apagados e esta ação não pode ser desfeita. O histórico do que a pessoa fez é mantido.",
    label: "Desativar",
    destructive: true,
  },
  "redefinir-senha": {
    title: "Redefinir senha?",
    body: "Um link de redefinição será gerado para você entregar à pessoa.",
    label: "Gerar link",
    destructive: false,
  },
};

export function MemberActions({
  member,
  onChanged,
  onError,
}: {
  member: Member;
  onChanged: () => void;
  onError: (message: string) => void;
}) {
  const { handleSessionError } = useSession();
  const [action, setAction] = useState<Action | null>(null);
  const [resetLink, setResetLink] = useState<string | null>(null);

  // A deactivated account has nothing left to act on (AC-0010-41); block and
  // reset apply only to an active one (AC-0010-37, -40).
  const available: Action[] = [];
  if (member.status === "ativo") available.push("bloquear", "redefinir-senha");
  if (member.status !== "desativado") available.push("desativar");
  if (available.length === 0) return null;

  async function run(chosen: Action) {
    try {
      const result = await apiJson<{ reset_link?: string }>(
        `/api/v1/usuarios/${member.id}/${chosen}`,
        { method: "POST" },
      );
      if (chosen === "redefinir-senha" && result.reset_link) setResetLink(result.reset_link);
      onChanged();
    } catch (err) {
      if (handleSessionError(err)) return;
      onError(err instanceof ApiError ? err.message : GENERIC_FAILURE);
    }
  }

  const confirm = action ? CONFIRM[action] : null;
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`Ações para ${displayName(member)}`}>
            <MoreHorizontal aria-hidden />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {available.includes("bloquear") && (
            <DropdownMenuItem onSelect={() => setAction("bloquear")}>
              <Ban aria-hidden />
              Bloquear
            </DropdownMenuItem>
          )}
          {available.includes("redefinir-senha") && (
            <DropdownMenuItem onSelect={() => setAction("redefinir-senha")}>
              <KeyRound aria-hidden />
              Redefinir senha
            </DropdownMenuItem>
          )}
          {available.includes("desativar") && (
            <DropdownMenuItem onSelect={() => setAction("desativar")} className="text-destructive">
              <UserX aria-hidden />
              Desativar
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={confirm !== null} onOpenChange={(open) => !open && setAction(null)}>
        {confirm && action && (
          <AlertDialogContent>
            <AlertDialogTitle>{confirm.title}</AlertDialogTitle>
            <AlertDialogDescription>{confirm.body}</AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction destructive={confirm.destructive} onClick={() => void run(action)}>
                {confirm.label}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        )}
      </AlertDialog>

      <Dialog open={resetLink !== null} onOpenChange={(open) => !open && setResetLink(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link de redefinição</DialogTitle>
            <DialogDescription>Este link não será mostrado de novo e expira em 1 hora.</DialogDescription>
          </DialogHeader>
          {resetLink && <CopyLink link={resetLink} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
