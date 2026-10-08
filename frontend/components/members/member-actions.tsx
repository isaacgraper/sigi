"use client";

import { Ban, KeyRound, MailPlus, MoreHorizontal, UserCheck, UserX } from "lucide-react";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, unavailable } from "@/lib/errors";
import { displayName } from "@/lib/me";
import { apiJson } from "@/lib/session";

// "unblock" has its own dialog, because it asks for a justification (AC-0010-59).
type Action = "block" | "deactivate" | "resetPassword" | "reinvite";

// The API's route segments (SPEC-0001 §7), kept in one place.
const ENDPOINT: Record<Action, string> = {
  block: "bloquear",
  deactivate: "desativar",
  resetPassword: "redefinir-senha",
  reinvite: "reemitir-convite",
};

const CONFIRM: Record<Action, { title: string; body: string; label: string; destructive: boolean }> = {
  block: {
    title: "Bloquear membro?",
    body: "As sessões abertas desta pessoa são encerradas e ela não consegue mais entrar.",
    label: "Bloquear",
    destructive: true,
  },
  deactivate: {
    title: "Desativar membro?",
    body: "Nome e e-mail serão apagados e esta ação não pode ser desfeita. O histórico do que a pessoa fez é mantido.",
    label: "Desativar",
    destructive: true,
  },
  resetPassword: {
    title: "Redefinir senha?",
    body: "Um link de redefinição será gerado para você entregar à pessoa.",
    label: "Gerar link",
    destructive: false,
  },
  reinvite: {
    title: "Gerar novo convite?",
    body: "Um novo link de ativação será gerado para você entregar à pessoa. O link anterior deixa de funcionar.",
    label: "Gerar link",
    destructive: false,
  },
};

// A one-time link is shown once and never again (AC-0010-40, -61).
const LINK_DIALOG: Record<"resetPassword" | "reinvite", { title: string; description: string }> = {
  resetPassword: {
    title: "Link de redefinição",
    description: "Este link não será mostrado de novo e expira em 1 hora.",
  },
  reinvite: {
    title: "Novo link de convite",
    description: "Este link não será mostrado de novo. O link anterior deixa de funcionar.",
  },
};

export function MemberActions({
  member,
  onChanged,
  onError,
}: {
  member: Member;
  onChanged: () => void;
  onError: (error: ApiError) => void;
}) {
  const { handleSessionError } = useSession();
  const [action, setAction] = useState<Action | null>(null);
  const [oneTime, setOneTime] = useState<{ kind: "resetPassword" | "reinvite"; link: string } | null>(
    null,
  );
  const [unblocking, setUnblocking] = useState(false);
  const [justification, setJustification] = useState("");
  const [pending, setPending] = useState(false);
  const [unblockError, setUnblockError] = useState<ApiError | null>(null);

  // A deactivated account has nothing left to act on (AC-0010-41); block and
  // reset apply only to an active one (AC-0010-37, -40), and unblock only to a
  // blocked one (AC-0010-59).
  const available: (Action | "unblock")[] = [];
  if (member.status === "ativo") available.push("block", "resetPassword");
  if (member.status === "bloqueado") available.push("unblock");
  // A pending account's only link may have been lost; this replaces it (AC-0010-61).
  if (member.status === "pendente") available.push("reinvite");
  if (member.status !== "desativado") available.push("deactivate");
  if (available.length === 0) return null;

  function closeUnblock() {
    setUnblocking(false);
    setJustification("");
    setUnblockError(null);
  }

  async function unblock(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setUnblockError(null);
    try {
      await apiJson(`/api/v1/usuarios/${member.id}/desbloquear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ justification }),
      });
      closeUnblock();
      onChanged();
    } catch (err) {
      if (handleSessionError(err)) return;
      const shown = err instanceof ApiError ? err : unavailable();
      setUnblockError(shown);
      // The account is no longer blocked, so the list is what is out of date.
      if (shown.code === "NOT_BLOCKED") onChanged();
    } finally {
      setPending(false);
    }
  }

  async function run(chosen: Action) {
    try {
      const result = await apiJson<{ reset_link?: string; activation_link?: string }>(
        `/api/v1/usuarios/${member.id}/${ENDPOINT[chosen]}`,
        { method: "POST" },
      );
      if (chosen === "resetPassword" && result.reset_link) {
        setOneTime({ kind: "resetPassword", link: result.reset_link });
      }
      if (chosen === "reinvite" && result.activation_link) {
        setOneTime({ kind: "reinvite", link: result.activation_link });
      }
      onChanged();
    } catch (err) {
      if (handleSessionError(err)) return;
      onError(err instanceof ApiError ? err : unavailable());
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
          {available.includes("block") && (
            <DropdownMenuItem onSelect={() => setAction("block")}>
              <Ban aria-hidden />
              Bloquear
            </DropdownMenuItem>
          )}
          {available.includes("unblock") && (
            <DropdownMenuItem onSelect={() => setUnblocking(true)}>
              <UserCheck aria-hidden />
              Desbloquear
            </DropdownMenuItem>
          )}
          {available.includes("reinvite") && (
            <DropdownMenuItem onSelect={() => setAction("reinvite")}>
              <MailPlus aria-hidden />
              Gerar novo convite
            </DropdownMenuItem>
          )}
          {available.includes("resetPassword") && (
            <DropdownMenuItem onSelect={() => setAction("resetPassword")}>
              <KeyRound aria-hidden />
              Redefinir senha
            </DropdownMenuItem>
          )}
          {available.includes("deactivate") && (
            <DropdownMenuItem onSelect={() => setAction("deactivate")} className="text-destructive">
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

      <Dialog open={unblocking} onOpenChange={(open) => !open && closeUnblock()}>
        <DialogContent>
          <form className="grid gap-4" onSubmit={unblock} noValidate>
            <DialogHeader>
              <DialogTitle>Desbloquear membro?</DialogTitle>
              <DialogDescription>
                A pessoa volta a entrar com a credencial que já tinha. Registre o motivo.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor="unblock-justification">Justificativa</Label>
              <Input
                id="unblock-justification"
                value={justification}
                aria-invalid={unblockError?.fields.justification ? true : undefined}
                aria-describedby={unblockError?.fields.justification ? "unblock-justification-error" : undefined}
                onChange={(e) => setJustification(e.target.value)}
              />
              {unblockError?.fields.justification && (
                <p id="unblock-justification-error" data-testid="field-error" className="text-sm text-destructive">
                  {unblockError.fields.justification}
                </p>
              )}
            </div>
            {unblockError && !unblockError.fields.justification && (
              <p role="alert" data-testid="unblock-error" className="text-sm text-destructive">
                {unblockError.message}
              </p>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeUnblock}>
                Cancelar
              </Button>
              <Button type="submit" disabled={pending}>
                {pending ? "Enviando..." : "Desbloquear"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={oneTime !== null} onOpenChange={(open) => !open && setOneTime(null)}>
        <DialogContent>
          {oneTime && (
            <>
              <DialogHeader>
                <DialogTitle>{LINK_DIALOG[oneTime.kind].title}</DialogTitle>
                <DialogDescription>{LINK_DIALOG[oneTime.kind].description}</DialogDescription>
              </DialogHeader>
              <CopyLink link={oneTime.link} />
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
