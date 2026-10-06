"use client";

import { UserPlus } from "lucide-react";
import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
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
import { ApiError, unavailable } from "@/lib/errors";
import { PERFIL_LABEL, type Perfil } from "@/lib/me";
import { apiJson } from "@/lib/session";

const INVITE_FIELDS = ["email", "name", "registration"] as const;

/** The refusals this dialog can show beside a field; anything else is shown as a notice. */
function pickFields(fields: Record<string, string>): Record<string, string> {
  const shown: Record<string, string> = {};
  for (const field of INVITE_FIELDS) if (fields[field]) shown[field] = fields[field];
  return shown;
}

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} data-testid="field-error" className="text-sm text-destructive">
      {message}
    </p>
  );
}

export function InviteDialog({
  onInvited,
  label = "Convidar membro",
  variant = "default",
}: {
  onInvited: () => void;
  /** The trigger's words; the empty table offers the same dialog in its own words. */
  label?: string;
  variant?: "default" | "outline";
}) {
  const { handleSessionError } = useSession();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [registration, setRegistration] = useState("");
  const [perfil, setPerfil] = useState<Perfil>("servidor");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [link, setLink] = useState<string | null>(null);

  function reset() {
    setEmail("");
    setName("");
    setRegistration("");
    setPerfil("servidor");
    setError(null);
    setFieldErrors({});
    setLink(null);
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    // The screen checks only that the fields are filled in (AC-0010-60): no
    // format is known for the registration, and what the API accepts is its
    // answer to give (C3).
    const empty: Record<string, string> = {};
    if (!email.trim()) empty.email = "Campo obrigatório.";
    if (!name.trim()) empty.name = "Campo obrigatório.";
    if (!registration.trim()) empty.registration = "Campo obrigatório.";
    setFieldErrors(empty);
    if (Object.keys(empty).length > 0) return;

    setPending(true);
    try {
      const created = await apiJson<{ activation_link: string }>("/api/v1/usuarios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, perfil, name, registration }),
      });
      setLink(created.activation_link);
    } catch (err) {
      if (handleSessionError(err)) return;
      const shown = err instanceof ApiError ? pickFields(err.fields) : {};
      if (Object.keys(shown).length > 0) {
        setFieldErrors(shown);
      } else {
        setError(err instanceof ApiError ? err : unavailable());
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
        <Button variant={variant}>
          <UserPlus aria-hidden />
          {label}
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
                aria-invalid={fieldErrors.email ? true : undefined}
                aria-describedby={fieldErrors.email ? "invite-email-error" : undefined}
                onChange={(e) => setEmail(e.target.value)}
              />
              <FieldError id="invite-email-error" message={fieldErrors.email} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-name">Nome completo</Label>
              <Input
                id="invite-name"
                required
                value={name}
                aria-invalid={fieldErrors.name ? true : undefined}
                aria-describedby={fieldErrors.name ? "invite-name-error" : undefined}
                onChange={(e) => setName(e.target.value)}
              />
              <FieldError id="invite-name-error" message={fieldErrors.name} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-registration">Registro na prefeitura</Label>
              <Input
                id="invite-registration"
                required
                value={registration}
                aria-invalid={fieldErrors.registration ? true : undefined}
                aria-describedby={fieldErrors.registration ? "invite-registration-error" : undefined}
                onChange={(e) => setRegistration(e.target.value)}
              />
              <FieldError id="invite-registration-error" message={fieldErrors.registration} />
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
            {error && <ErrorNotice error={error} />}
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
