"use client";

import Link from "next/link";
import { useState } from "react";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import {
  EDITABLE,
  NF_ACTION_ASKS,
  NF_ACTION_DESCRIPTION,
  NF_ACTION_LABEL,
  NF_ACTION_ORDER,
  QUARANTINABLE,
} from "@/lib/notas-fiscais/constants";
import type { NfAction, NotaFiscal } from "@/lib/notas-fiscais/types";
import type { Perfil } from "@/lib/types";
import { usePost } from "@/lib/use-post";

/**
 * The moves on an NF (AC-0016-06 to -08): correct while it waits or was sent
 * back, send it for conferência, and the gestor's approve, return and release.
 * The API decides; these buttons only hide what it would refuse anyway.
 */
export function NfActions({
  nf,
  perfil,
  onDone,
  onStale,
}: {
  nf: NotaFiscal;
  perfil: Perfil;
  onDone: (nf: NotaFiscal, action: NfAction) => void;
  onStale: () => void;
}) {
  const [action, setAction] = useState<NfAction | null>(null);
  const [text, setText] = useState("");
  const { errors, failure, pending, send, clear } = usePost(NF_ACTION_ORDER, {}, "nf-action");

  const gestor = perfil === "gestor";
  const writer = gestor || perfil === "servidor";
  if (!writer) return null;

  const conferencia = nf.status === "em_conferencia";
  const moves: NfAction[] = [];
  if (EDITABLE.includes(nf.status)) moves.push("enviar");
  if (gestor && conferencia && !nf.quarentena) moves.push("aprovar");
  if (gestor && conferencia) moves.push("devolver");
  if (QUARANTINABLE.includes(nf.status) && !nf.quarentena) moves.push("quarentena");
  if (gestor && nf.quarentena) moves.push("liberar");
  const editable = EDITABLE.includes(nf.status);
  if (moves.length === 0 && !editable) return null;

  const asks = action ? NF_ACTION_ASKS[action] : undefined;

  function close() {
    setAction(null);
    setText("");
    clear();
  }

  async function confirm(chosen: NfAction) {
    const ask = NF_ACTION_ASKS[chosen];
    const body = ask ? { [ask.key]: text.trim() } : undefined;
    const done = await send<NotaFiscal>(`/api/v1/notas-fiscais/${nf.id}/${chosen}`, body);
    if (done) {
      close();
      onDone(done, chosen);
    } else {
      onStale();
    }
  }

  return (
    <>
      <div data-testid="nf-actions" className="flex flex-wrap gap-2">
        {moves.map((move, i) => (
          <Button key={move} variant={i === 0 ? "default" : "outline"} onClick={() => setAction(move)}>
            {NF_ACTION_LABEL[move]}
          </Button>
        ))}
        {editable && (
          <Link href={`/notas-fiscais/${nf.id}/corrigir`} className={buttonVariants({ variant: "outline" })}>
            Corrigir
          </Link>
        )}
      </div>

      <AlertDialog open={action !== null} onOpenChange={(open) => !open && close()}>
        {action && (
          <AlertDialogContent>
            <AlertDialogTitle>{NF_ACTION_LABEL[action]}</AlertDialogTitle>
            <AlertDialogDescription>{NF_ACTION_DESCRIPTION[action]}</AlertDialogDescription>

            {asks && (
              <Field id={`nf-action-${asks.key}`} label={asks.label} error={errors[asks.key]}>
                {(props) => (
                  <Textarea {...props} maxLength={500} value={text} onChange={(e) => setText(e.target.value)} />
                )}
              </Field>
            )}
            {failure && (
              <p role="alert" data-testid="nf-action-error" className="text-sm text-destructive">
                {failure.message}
              </p>
            )}

            <AlertDialogFooter>
              <AlertDialogCancel>Voltar</AlertDialogCancel>
              <Button
                variant={action === "devolver" ? "destructive" : "default"}
                disabled={pending || (asks !== undefined && !text.trim())}
                onClick={() => void confirm(action)}
              >
                {pending ? "Enviando..." : NF_ACTION_LABEL[action]}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        )}
      </AlertDialog>
    </>
  );
}
