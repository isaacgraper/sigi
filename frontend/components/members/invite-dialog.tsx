"use client";

import { UserPlus } from "lucide-react";
import { useState } from "react";

import { FormMessage } from "@/components/auth/auth-layout";
import { CopyLink } from "@/components/members/copy-link";
import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError, GENERIC_FAILURE } from "@/lib/errors";
import { PERFIL_LABEL, type Perfil } from "@/lib/me";
import { apiJson } from "@/lib/session";

export function InviteDialog({ onInvited }: { onInvited: () => void }) {
  const { handleSessionError } = useSession();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [perfil, setPerfil] = useState<Perfil>("servidor");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [link, setLink] = useState<string | null>(null);

  function reset() {
    setEmail("");
    setPerfil("servidor");
    setError(null);
    setFieldError(null);
    setLink(null);
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setFieldError(null);
    try {
      const created = await apiJson<{ activation_link: string }>("/api/v1/usuarios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, perfil }),
      });
      setLink(created.activation_link);
    } catch (err) {
      if (handleSessionError(err)) return;
      if (err instanceof ApiError && err.fields.email) {
        setFieldError(err.fields.email);
      } else {
        setError(err instanceof ApiError ? err.message : GENERIC_FAILURE);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && link) onInvited();
        if (!next) reset();
        setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <UserPlus aria-hidden />
          Convidar membro
        </Button>
      </DialogTrigger>
      <DialogContent>
        {link ? (
          <>
            <DialogHeader>
              <DialogTitle>Convite criado</DialogTitle>
              <DialogDescription>
                Este link não será mostrado de novo. Envie-o agora à pessoa convidada.
              </DialogDescription>
            </DialogHeader>
            <CopyLink link={link} />
            <DialogFooter>
              <Button type="button" onClick={() => { onInvited(); reset(); setOpen(false); }}>
                Concluir
              </Button>
            </DialogFooter>
          </>
        ) : (
          <form className="grid gap-4" onSubmit={onSubmit} noValidate>
            <DialogHeader>
              <DialogTitle>Convidar membro</DialogTitle>
              <DialogDescription>
                A pessoa recebe um link de ativação, que você entrega.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor="invite-email">E-mail institucional</Label>
              <Input
                id="invite-email"
                type="email"
                required
                value={email}
                aria-invalid={fieldError ? true : undefined}
                aria-describedby={fieldError ? "invite-email-error" : undefined}
                onChange={(e) => setEmail(e.target.value)}
              />
              {fieldError && (
                <p id="invite-email-error" data-testid="field-error" className="text-sm text-destructive">
                  {fieldError}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-perfil">Perfil</Label>
              <Select value={perfil} onValueChange={(value) => setPerfil(value as Perfil)}>
                <SelectTrigger id="invite-perfil">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(["servidor", "gestor", "auditor"] as const).map((value) => (
                    <SelectItem key={value} value={value}>
                      {PERFIL_LABEL[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {error && <FormMessage>{error}</FormMessage>}
            <DialogFooter>
              <Button type="submit" disabled={pending}>
                {pending ? "Enviando..." : "Convidar"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
