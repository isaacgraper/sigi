"use client";

import { useState } from "react";

import { Field } from "@/components/ui/field";
import { useSession } from "@/components/session-provider";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MOVE, MOVES } from "@/lib/atas/constants";
import type { AtaDetail, Move } from "@/lib/atas/types";
import { ApiError, unavailable } from "@/lib/errors";
import { apiJson } from "@/lib/session";

/**
 * The lifecycle moves a gestor may ask for on this status (AC-0013-12, -13).
 * The dialog stays open on a refusal so the API's words are read, and the page
 * reloads the ATA, which the refusal says is not what the screen showed.
 */
export function MoveActions({
  ata,
  onMoved,
  onStale,
}: {
  ata: AtaDetail;
  onMoved: (ata: AtaDetail, move: Move) => void;
  onStale: () => void;
}) {
  const { handleSessionError } = useSession();
  const [move, setMove] = useState<Move | null>(null);
  const [justification, setJustification] = useState("");
  const [refusal, setRefusal] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  // The dialog outlives the buttons: a refusal reloads the ATA, and the reload
  // may leave no move to offer while its message is still being read.
  const moves = MOVES[ata.status];

  function close() {
    setMove(null);
    setJustification("");
    setRefusal(null);
  }

  async function confirm(chosen: Move) {
    setPending(true);
    setRefusal(null);
    try {
      const moved = await apiJson<AtaDetail>(`/api/v1/atas/${ata.id}/${chosen}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: chosen === "cancelar" ? JSON.stringify({ justification: justification.trim() }) : undefined,
      });
      close();
      onMoved(moved, chosen);
    } catch (err) {
      if (handleSessionError(err)) return;
      setRefusal(err instanceof ApiError ? err : unavailable());
      onStale();
    } finally {
      setPending(false);
    }
  }

  const config = move ? MOVE[move] : null;
  const fieldError = refusal?.fields.justification;
  return (
    <>
      {moves.map((name) => (
        <Button key={name} variant="outline" onClick={() => setMove(name)}>
          {MOVE[name].label}
        </Button>
      ))}

      <AlertDialog open={move !== null} onOpenChange={(open) => !open && close()}>
        {config && move && (
          <AlertDialogContent>
            <AlertDialogTitle>{config.title}</AlertDialogTitle>
            <AlertDialogDescription>
              ATA {ata.number}. {config.body}
            </AlertDialogDescription>
            {move === "cancelar" && (
              <Field id="move-justification" label="Justificativa" error={fieldError}>
                {(props) => (
                  <Textarea
                    {...props}
                    maxLength={500}
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                  />
                )}
              </Field>
            )}
            {refusal && !fieldError && (
              <p role="alert" data-testid="move-error" className="text-sm text-destructive">
                {refusal.message}
              </p>
            )}
            <AlertDialogFooter>
              {/* Not "Cancelar": that is one of the moves. */}
              <AlertDialogCancel>Voltar</AlertDialogCancel>
              <Button
                variant={config.destructive ? "destructive" : "default"}
                disabled={pending || (move === "cancelar" && !justification.trim())}
                onClick={() => void confirm(move)}
              >
                {pending ? "Enviando..." : move === "cancelar" ? "Cancelar ATA" : config.label}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        )}
      </AlertDialog>
    </>
  );
}
