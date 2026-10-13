"use client";

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import { Field, focusFirst } from "@/components/atas/field";
import { ErrorNotice } from "@/components/error-notice";
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
import { Textarea } from "@/components/ui/textarea";
import { ADITIVO_CODES, ADITIVO_ORDER, REAJUSTE_CODES, REAJUSTE_ORDER } from "@/lib/atas/constants";
import type { AtaDetail } from "@/lib/atas/types";
import { ApiError, unavailable } from "@/lib/errors";
import { parseMoney } from "@/lib/format";
import { apiJson } from "@/lib/session";

/** Today in America/Sao_Paulo, as the date input wants it. */
function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

/**
 * One dialog that posts to the ATA and lands the API's refusal on the field it
 * names. `codeField` places the refusals SPEC-0002 §3.7 sends without `fields`.
 */
function useRecord(ata: AtaDetail, path: string, order: string[], codeField: Record<string, string>, prefix: string) {
  const { handleSessionError } = useSession();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    focusFirst(order, errors, prefix);
  }, [errors, order, prefix]);

  async function post(body: Record<string, unknown>, empty: Record<string, string>): Promise<AtaDetail | null> {
    setFailure(null);
    setErrors(empty);
    if (Object.keys(empty).length > 0) return null;
    setPending(true);
    try {
      return await apiJson<AtaDetail>(`/api/v1/atas/${ata.id}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (err) {
      if (handleSessionError(err)) return null;
      const error = err instanceof ApiError ? err : unavailable();
      const named: Record<string, string> = {};
      for (const key of order) if (error.fields[key]) named[key] = error.fields[key];
      if (codeField[error.code]) named[codeField[error.code]] = error.message;
      if (Object.keys(named).length > 0) setErrors(named);
      else setFailure(error);
      return null;
    } finally {
      setPending(false);
    }
  }

  function clear() {
    setErrors({});
    setFailure(null);
  }

  return { errors, failure, pending, post, clear };
}

/** "Registrar aditivo" (AC-0013-15). The 25% ceiling is the API's to compute. */
export function AditivoDialog({ ata, onSaved }: { ata: AtaDetail; onSaved: (ata: AtaDetail) => void }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<"valor" | "prazo">("valor");
  const [acrescimo, setAcrescimo] = useState("");
  const [novoFim, setNovoFim] = useState("");
  const [justification, setJustification] = useState("");
  const record = useRecord(ata, "aditivos", ADITIVO_ORDER, ADITIVO_CODES, "aditivo");

  function reset() {
    setKind("valor");
    setAcrescimo("");
    setNovoFim("");
    setJustification("");
    record.clear();
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const empty: Record<string, string> = {};
    if (kind === "valor" && !acrescimo.trim()) empty.valor_acrescimo = "Campo obrigatório.";
    if (kind === "prazo" && !novoFim) empty.nova_vigencia_fim = "Campo obrigatório.";
    if (!justification.trim()) empty.justification = "Campo obrigatório.";
    const saved = await record.post(
      {
        kind,
        justification: justification.trim(),
        ...(kind === "valor" ? { valor_acrescimo: parseMoney(acrescimo.trim()) } : { nova_vigencia_fim: novoFim }),
      },
      empty,
    );
    if (saved) {
      setOpen(false);
      onSaved(saved);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) reset();
        setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus aria-hidden />
          Registrar aditivo
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>Registrar aditivo</DialogTitle>
            <DialogDescription>ATA {ata.number}. O aditivo fica registrado com a justificativa.</DialogDescription>
          </DialogHeader>
          <fieldset className="space-y-2">
            <legend className="text-sm font-normal">Tipo</legend>
            <div className="flex gap-6">
              {(["valor", "prazo"] as const).map((value) => (
                <label key={value} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="aditivo-kind"
                    value={value}
                    checked={kind === value}
                    onChange={() => setKind(value)}
                    className="size-4 accent-primary"
                  />
                  {value === "valor" ? "Valor" : "Prazo"}
                </label>
              ))}
            </div>
          </fieldset>
          {kind === "valor" ? (
            <Field id="aditivo-valor_acrescimo" label="Acréscimo (R$)" error={record.errors.valor_acrescimo}>
              {(props) => (
                <Input
                  {...props}
                  inputMode="decimal"
                  placeholder="0,00"
                  value={acrescimo}
                  onChange={(e) => setAcrescimo(e.target.value)}
                />
              )}
            </Field>
          ) : (
            <Field id="aditivo-nova_vigencia_fim" label="Novo fim da vigência" error={record.errors.nova_vigencia_fim}>
              {(props) => <Input {...props} type="date" value={novoFim} onChange={(e) => setNovoFim(e.target.value)} />}
            </Field>
          )}
          <Field id="aditivo-justification" label="Justificativa" error={record.errors.justification}>
            {(props) => (
              <Textarea
                {...props}
                maxLength={500}
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
              />
            )}
          </Field>
          {record.failure && <ErrorNotice error={record.failure} />}
          <DialogFooter>
            <Button type="submit" disabled={record.pending}>
              {record.pending ? "Enviando..." : "Registrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** "Registrar pedido de reajuste" (AC-0013-16): that it was filed in SEI, and under which process. */
export function ReajusteDialog({ ata, onSaved }: { ata: AtaDetail; onSaved: (ata: AtaDetail) => void }) {
  const [open, setOpen] = useState(false);
  const [processo, setProcesso] = useState("");
  const [requestedOn, setRequestedOn] = useState(today);
  const record = useRecord(ata, "reajustes", REAJUSTE_ORDER, REAJUSTE_CODES, "reajuste");

  function reset() {
    setProcesso("");
    setRequestedOn(today());
    record.clear();
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const empty: Record<string, string> = {};
    if (!processo.trim()) empty.processo_sei = "Campo obrigatório.";
    if (!requestedOn) empty.requested_on = "Campo obrigatório.";
    const saved = await record.post({ processo_sei: processo.trim(), requested_on: requestedOn }, empty);
    if (saved) {
      setOpen(false);
      onSaved(saved);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) reset();
        setOpen(next);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus aria-hidden />
          Registrar pedido de reajuste
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>Registrar pedido de reajuste</DialogTitle>
            <DialogDescription>
              ATA {ata.number}. O pedido é aberto no SEI; aqui fica registrado que foi feito.
            </DialogDescription>
          </DialogHeader>
          <Field
            id="reajuste-processo_sei"
            label="Processo SEI"
            hint="Formato NNNNN.NNNNNN/AAAA-DD"
            error={record.errors.processo_sei}
          >
            {(props) => (
              <Input
                {...props}
                placeholder="00000.000000/2026-00"
                value={processo}
                onChange={(e) => setProcesso(e.target.value)}
              />
            )}
          </Field>
          <Field id="reajuste-requested_on" label="Data do pedido" error={record.errors.requested_on}>
            {(props) => (
              <Input {...props} type="date" value={requestedOn} onChange={(e) => setRequestedOn(e.target.value)} />
            )}
          </Field>
          {record.failure && <ErrorNotice error={record.failure} />}
          <DialogFooter>
            <Button type="submit" disabled={record.pending}>
              {record.pending ? "Enviando..." : "Registrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
