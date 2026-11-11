"use client";

import { Download } from "lucide-react";
import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, readError, unavailable } from "@/lib/errors";
import {
  COLUMNS_NONE,
  DAY_END,
  DAY_START,
  EXPORT_COLUMNS,
  EXPORT_DESCRIPTION,
  EXPORT_DONE,
  EXPORT_LABEL,
  EXPORTING_LABEL,
  FALLBACK_FILENAME,
  FORMATOS,
  type Formato,
  type ListExport,
  REFERENCE_HELP,
  SAO_PAULO_OFFSET,
  START_HELP,
} from "@/lib/relatorios/constants";
import { apiFetch } from "@/lib/session";

/** Today in São Paulo, as a date input holds it. */
function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

/** The name the API gave the file, from its Content-Disposition. */
function filenameOf(response: Response): string {
  const match = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") ?? "");
  return match?.[1] ?? FALLBACK_FILENAME;
}

/**
 * "Exportar" on a list, and the dialog it opens (SPEC-0009 AC-0009-13): the
 * format, the columns, the data de referência and the start of the period. The
 * list's filters go with it; the API decides who may export what (AC-0009-11).
 */
export function ExportDialog({
  relatorio,
  title,
  filtros,
  size = "default",
}: {
  relatorio: ListExport;
  title: string;
  filtros: Record<string, string | null | undefined>;
  size?: "default" | "sm";
}) {
  const { handleSessionError } = useSession();
  const columns = EXPORT_COLUMNS[relatorio];
  const [open, setOpen] = useState(false);
  const [formato, setFormato] = useState<Formato>("csv");
  const [chosen, setChosen] = useState<string[]>(columns.map((column) => column.key));
  const [referencia, setReferencia] = useState(today());
  const [inicio, setInicio] = useState("");
  const [sending, setSending] = useState(false);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [announcement, setAnnouncement] = useState("");

  const fields = failure?.status === 422 ? failure.fields : {};
  const unexplained = failure && !(failure.status === 422 && Object.keys(failure.fields).length > 0);
  const missingColumns = chosen.length === 0;

  const reset = (next: boolean) => {
    setOpen(next);
    if (next) {
      setReferencia(today());
      setFailure(null);
    }
  };

  const send = async () => {
    if (missingColumns) return;
    setSending(true);
    setFailure(null);
    const params = new URLSearchParams({ formato });
    for (const [key, value] of Object.entries(filtros)) if (value) params.set(key, value);
    if (chosen.length < columns.length) params.set("colunas", chosen.join(","));
    // Today is "now"; a past day is read as it stood at its end in São Paulo.
    if (referencia && referencia !== today()) params.set("referencia", `${referencia}${DAY_END}${SAO_PAULO_OFFSET}`);
    if (inicio) params.set("inicio", `${inicio}${DAY_START}${SAO_PAULO_OFFSET}`);
    try {
      const response = await apiFetch(`/api/v1/relatorios/${relatorio}?${params}`);
      if (!response.ok) throw await readError(response);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = filenameOf(response);
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setAnnouncement(EXPORT_DONE);
      setOpen(false);
    } catch (err: unknown) {
      if (!handleSessionError(err)) setFailure(err instanceof ApiError ? err : unavailable());
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <Button variant="outline" size={size} onClick={() => reset(true)}>
        <Download aria-hidden />
        {EXPORT_LABEL}
      </Button>
      <p role="status" className="sr-only">
        {announcement}
      </p>
      <Dialog open={open} onOpenChange={reset}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Exportar {title}</DialogTitle>
            <DialogDescription>{EXPORT_DESCRIPTION}</DialogDescription>
          </DialogHeader>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void send();
            }}
          >
            <fieldset className="space-y-2">
              <legend className="text-sm">Formato</legend>
              <div className="flex flex-wrap gap-4">
                {FORMATOS.map((option) => (
                  <label key={option.value} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="formato"
                      value={option.value}
                      className="size-4 accent-primary"
                      checked={formato === option.value}
                      onChange={() => setFormato(option.value)}
                    />
                    {option.label}
                  </label>
                ))}
              </div>
              {fields.formato && <p className="text-sm text-destructive">{fields.formato}</p>}
            </fieldset>

            <fieldset className="space-y-2" aria-describedby={missingColumns || fields.colunas ? "exportar-colunas-erro" : undefined}>
              <legend className="text-sm">Colunas</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {columns.map((column) => (
                  <label key={column.key} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="size-4 accent-primary"
                      checked={chosen.includes(column.key)}
                      onChange={(event) =>
                        setChosen(
                          event.target.checked
                            ? columns.map((c) => c.key).filter((key) => key === column.key || chosen.includes(key))
                            : chosen.filter((key) => key !== column.key),
                        )
                      }
                    />
                    {column.label}
                  </label>
                ))}
              </div>
              {(missingColumns || fields.colunas) && (
                <p id="exportar-colunas-erro" data-testid="field-error" className="text-sm text-destructive">
                  {fields.colunas ?? COLUMNS_NONE}
                </p>
              )}
            </fieldset>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="exportar-referencia" label="Data de referência" hint={REFERENCE_HELP} error={fields.referencia}>
                {(props) => (
                  <Input {...props} type="date" max={today()} value={referencia} onChange={(e) => setReferencia(e.target.value)} />
                )}
              </Field>
              <Field id="exportar-inicio" label="Início do período" hint={START_HELP} error={fields.inicio}>
                {(props) => <Input {...props} type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} />}
              </Field>
            </div>

            {unexplained && failure && <ErrorNotice error={failure} />}

            <DialogFooter>
              <Button type="submit" disabled={sending || missingColumns}>
                <Download aria-hidden />
                {sending ? EXPORTING_LABEL : EXPORT_LABEL}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
