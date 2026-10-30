"use client";

import { useState } from "react";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ACTION_LABEL, ADVANCE_CODE_FIELD, NUMERO_FIELD, STAGE_LABEL, STAGES } from "@/lib/notas-empenho/constants";
import type { NeAction, NotaEmpenho, Stage } from "@/lib/notas-empenho/types";
import { usePost } from "@/lib/use-post";

/**
 * The moves on an NE (AC-0015-06 to -09): advance to the next stage, asking for
 * the número the next one needs; reverse one stage; cancel. Reverse and cancel
 * ask for the justification RN03 records. A refusal stays in the dialog, read,
 * and the page reloads the NE, which the refusal says is not what it showed.
 */
export function NeActions({
  ne,
  gestor,
  onDone,
  onStale,
}: {
  ne: NotaEmpenho;
  gestor: boolean;
  onDone: (ne: NotaEmpenho, action: NeAction) => void;
  onStale: () => void;
}) {
  const [action, setAction] = useState<NeAction | null>(null);
  const [numero, setNumero] = useState("");
  const [justification, setJustification] = useState("");
  const { errors, failure, pending, send, clear } = usePost(
    ["numero_pre_empenho", "number", "justification"],
    ADVANCE_CODE_FIELD,
    "ne-action",
  );

  const index = STAGES.indexOf(ne.status as Stage);
  const terminal = ne.status === "ne_emitida" || ne.status === "cancelada";
  const next = !terminal && index >= 0 ? STAGES[index + 1] : null;
  const previous = !terminal && index > 0 ? STAGES[index - 1] : null;
  const asks = next ? NUMERO_FIELD[next] : undefined;

  function close() {
    setAction(null);
    setNumero("");
    setJustification("");
    clear();
  }

  async function confirm(chosen: NeAction) {
    const body: Record<string, unknown> =
      chosen === "avancar" ? (asks ? { [asks.key]: numero.trim() } : {}) : { justification: justification.trim() };
    const done = await send<NotaEmpenho>(`/api/v1/notas-empenho/${ne.id}/${chosen}`, body);
    if (done) {
      close();
      onDone(done, chosen);
    } else {
      onStale();
    }
  }

  if (terminal) return null;
  return (
    <>
      <div data-testid="ne-actions" className="flex flex-wrap gap-2">
        {next && <Button onClick={() => setAction("avancar")}>Avançar para {STAGE_LABEL[next]}</Button>}
        {gestor && previous && (
          <Button variant="outline" onClick={() => setAction("reverter")}>
            {ACTION_LABEL.reverter}
          </Button>
        )}
        {gestor && (
          <Button variant="outline" onClick={() => setAction("cancelar")}>
            {ACTION_LABEL.cancelar}
          </Button>
        )}
      </div>

      <AlertDialog open={action !== null} onOpenChange={(open) => !open && close()}>
        {action && (
          <AlertDialogContent>
            <AlertDialogTitle>
              {action === "avancar" && next
                ? `Avançar para ${STAGE_LABEL[next]}`
                : action === "reverter" && previous
                  ? `Voltar para ${STAGE_LABEL[previous]}`
                  : "Cancelar a NE"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {action === "avancar" && next === "pre_empenho"
                ? "O saldo da ATA é conferido e reservado agora."
                : action === "avancar" && next === "ne_emitida"
                  ? "A reserva vira empenho. A NE não muda mais depois disso."
                  : action === "avancar"
                    ? "A NE passa para a próxima etapa."
                    : action === "reverter"
                      ? "A justificativa fica registrada no histórico."
                      : "A reserva de saldo, se houver, é liberada. A justificativa fica registrada no histórico."}
            </AlertDialogDescription>

            {action === "avancar" && asks && (
              <Field id={`ne-action-${asks.key}`} label={asks.label} help={asks.help} error={errors[asks.key]}>
                {(props) => (
                  <Input {...props} autoComplete="off" maxLength={20} value={numero} onChange={(e) => setNumero(e.target.value)} />
                )}
              </Field>
            )}
            {action !== "avancar" && (
              <Field id="ne-action-justification" label="Justificativa" error={errors.justification}>
                {(props) => (
                  <Textarea {...props} maxLength={500} value={justification} onChange={(e) => setJustification(e.target.value)} />
                )}
              </Field>
            )}
            {failure && (
              <p role="alert" data-testid="ne-action-error" className="text-sm text-destructive">
                {failure.message}
              </p>
            )}

            <AlertDialogFooter>
              <AlertDialogCancel>Voltar</AlertDialogCancel>
              <Button
                variant={action === "cancelar" ? "destructive" : "default"}
                disabled={
                  pending ||
                  (action === "avancar" && asks !== undefined && !numero.trim()) ||
                  (action !== "avancar" && !justification.trim())
                }
                onClick={() => void confirm(action)}
              >
                {pending ? "Enviando..." : action === "avancar" ? "Avançar" : action === "reverter" ? "Reverter" : "Cancelar NE"}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        )}
      </AlertDialog>
    </>
  );
}
