"use client";

import { useState } from "react";
import { toast } from "sonner";

import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError, readError, unavailable } from "@/lib/errors";
import { DIAS_SEMANA, FREQUENCIAS, PREFS_PATH, PREFS_SAVED } from "@/lib/notificacoes/constants";
import type { Frequencia, PreferenciaEmail } from "@/lib/notificacoes/types";
import { apiFetch } from "@/lib/session";
import { useRead } from "@/lib/use-read";

/** The form, once the stored choice is known, so it starts from it. */
function EmailForm({ initial, onSaved }: { initial: PreferenciaEmail; onSaved: (next: PreferenciaEmail) => void }) {
  const { handleSessionError } = useSession();
  const [frequencia, setFrequencia] = useState<Frequencia>(initial.frequencia);
  const [dia, setDia] = useState(initial.dia_semana);
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const fields = failure?.status === 422 ? failure.fields : {};

  const save = async () => {
    setSending(true);
    setFailure(null);
    try {
      const response = await apiFetch(PREFS_PATH, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frequencia, dia_semana: dia }),
      });
      if (!response.ok) throw await readError(response);
      onSaved((await response.json()) as PreferenciaEmail);
      toast.success(PREFS_SAVED);
    } catch (err: unknown) {
      if (!handleSessionError(err)) setFailure(err instanceof ApiError ? err : unavailable());
    } finally {
      setSending(false);
    }
  };

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <fieldset className="space-y-2">
        <legend className="text-sm">Frequência</legend>
        <div className="space-y-2">
          {FREQUENCIAS.map((option) => (
            <label key={option.value} className="flex items-start gap-2 text-sm">
              <input
                type="radio"
                name="frequencia"
                value={option.value}
                className="mt-0.5 size-4 accent-primary"
                checked={frequencia === option.value}
                onChange={() => setFrequencia(option.value)}
              />
              <span>
                {option.label}
                <span className="block text-xs font-light text-muted-foreground">{option.hint}</span>
              </span>
            </label>
          ))}
        </div>
        {fields.frequencia && <p className="text-sm text-destructive">{fields.frequencia}</p>}
      </fieldset>

      {frequencia === "semanal" && (
        <div className="max-w-xs">
          <Field id="dia-semana" label="Dia da semana" error={fields.dia_semana}>
            {(props) => (
              <Select value={String(dia)} onValueChange={(value) => setDia(Number(value))}>
                <SelectTrigger {...props}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DIAS_SEMANA.map((option) => (
                    <SelectItem key={option.value} value={String(option.value)}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </Field>
        </div>
      )}

      {failure && !(failure.status === 422 && Object.keys(fields).length > 0) && <ErrorNotice error={failure} />}

      <div className="flex justify-end">
        <Button type="submit" disabled={sending}>
          {sending ? "Salvando..." : "Salvar"}
        </Button>
      </div>
    </form>
  );
}

/** /configuracoes: what each member sets for themselves, the e-mail summary first (SPEC-0008 AC-0008-07). */
export function Configuracoes() {
  const read = useRead<PreferenciaEmail>(PREFS_PATH);

  return (
    <div className="space-y-6">
      <PageHeader title="Configurações" description="O que vale só para você no SIGI." />
      <Card className="max-w-2xl">
        <CardHeader className="pb-3">
          <CardTitle>Resumo por e-mail</CardTitle>
          <p className="text-sm font-light text-muted-foreground">
            Um e-mail com as ATAs que pedem atenção, as NEs por etapa e as NFs em conferência, devolvidas e em
            quarentena, no e-mail com que você entra no SIGI.
          </p>
        </CardHeader>
        <CardContent>
          {read.failure && !read.data && <ErrorNotice error={read.failure} />}
          {!read.data && !read.failure && <TableSkeleton rows={2} />}
          {read.data && <EmailForm initial={read.data} onSaved={read.replace} />}
        </CardContent>
      </Card>
    </div>
  );
}
