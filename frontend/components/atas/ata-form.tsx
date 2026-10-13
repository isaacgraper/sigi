"use client";

import { Pencil, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
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
import type { AtaDetail } from "@/lib/atas";
import { ApiError, unavailable } from "@/lib/errors";
import { setFlash } from "@/lib/flash";
import { formatBRL, formatCnpj, parseMoney } from "@/lib/format";
import { apiJson } from "@/lib/session";

// Keys are the API's payload paths, so a refusal's `fields` lands as it comes.
type Key =
  | "number"
  | "subject"
  | "organ"
  | "fornecedor.cnpj"
  | "fornecedor.legal_name"
  | "issued_on"
  | "vigencia_inicio"
  | "vigencia_fim"
  | "total_value"
  | "budget_date";

const FIELDS: { key: Key; label: string; type?: "date" | "money"; optional?: boolean; locks?: boolean }[] = [
  { key: "number", label: "Número", locks: true },
  { key: "subject", label: "Objeto" },
  { key: "organ", label: "Órgão" },
  { key: "fornecedor.cnpj", label: "CNPJ do fornecedor", locks: true },
  { key: "fornecedor.legal_name", label: "Razão social", locks: true },
  { key: "issued_on", label: "Data de emissão (opcional)", type: "date", optional: true, locks: true },
  { key: "vigencia_inicio", label: "Início da vigência", type: "date", locks: true },
  { key: "vigencia_fim", label: "Fim da vigência", type: "date", locks: true },
  { key: "total_value", label: "Valor total (R$)", type: "money", locks: true },
  { key: "budget_date", label: "Data do orçamento planilhado", type: "date", locks: true },
];

const ORDER = FIELDS.map((field) => field.key);

// Refusals that name no field in `fields` but belong to one (SPEC-0002 §3.7).
const CODE_FIELD: Record<string, Key> = { ATA_DUPLICADA: "number" };

type Values = Record<Key, string>;

const EMPTY: Values = {
  number: "",
  subject: "",
  organ: "",
  "fornecedor.cnpj": "",
  "fornecedor.legal_name": "",
  issued_on: "",
  vigencia_inicio: "",
  vigencia_fim: "",
  total_value: "",
  budget_date: "",
};

function valuesOf(ata: AtaDetail): Values {
  return {
    number: ata.number,
    subject: ata.subject,
    organ: ata.organ,
    "fornecedor.cnpj": formatCnpj(ata.fornecedor.cnpj),
    "fornecedor.legal_name": ata.fornecedor.legal_name,
    issued_on: ata.issued_on ?? "",
    vigencia_inicio: ata.vigencia_inicio,
    vigencia_fim: ata.vigencia_fim,
    total_value: formatBRL(ata.total_value).replace("R$ ", ""),
    budget_date: ata.budget_date,
  };
}

function payload(values: Values, keys: Key[]): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const key of keys) {
    if (key.startsWith("fornecedor.")) continue;
    const value = values[key].trim();
    if (key === "total_value") body[key] = parseMoney(value);
    else if (key === "issued_on") body[key] = value || null;
    else body[key] = value;
  }
  if (keys.some((key) => key.startsWith("fornecedor."))) {
    body.fornecedor = {
      cnpj: values["fornecedor.cnpj"].trim(),
      legal_name: values["fornecedor.legal_name"].trim(),
    };
  }
  return body;
}

/**
 * "Cadastrar ATA" (AC-0013-07 to -09) and "Editar" (AC-0013-14). Past
 * "rascunho" the figures change only through an aditivo, so the dialog shows
 * them read-only; the API refuses them anyway (AC-0002-24).
 */
export function AtaForm({
  ata,
  onSaved,
  onStale,
}: {
  ata?: AtaDetail;
  onSaved?: (ata: AtaDetail) => void;
  /** The API refused because the ATA changed meanwhile: the page reloads it (§5). */
  onStale?: () => void;
}) {
  const { handleSessionError } = useSession();
  const router = useRouter();
  const editing = ata !== undefined;
  const locked = editing && ata.status !== "rascunho";
  const initial = ata ? valuesOf(ata) : EMPTY;

  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Values>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    focusFirst(ORDER, errors, "ata");
  }, [errors]);

  function reset() {
    setValues(ata ? valuesOf(ata) : EMPTY);
    setErrors({});
    setFailure(null);
  }

  function set(key: Key, value: string) {
    setValues((current) => ({ ...current, [key]: key === "fornecedor.cnpj" ? formatCnpj(value) : value }));
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(null);

    const editable = FIELDS.filter((field) => !(locked && field.locks));
    // Only that a required field is filled in; the rest is the API's (AC-0013-08).
    const empty: Record<string, string> = {};
    for (const field of editable) {
      if (!field.optional && !values[field.key].trim()) empty[field.key] = "Campo obrigatório.";
    }
    setErrors(empty);
    if (Object.keys(empty).length > 0) return;

    const keys = editable
      .map((field) => field.key)
      .filter((key) => !editing || values[key].trim() !== initial[key].trim());
    if (editing && keys.length === 0) {
      setOpen(false);
      return;
    }

    setPending(true);
    try {
      const saved = await apiJson<AtaDetail>(editing ? `/api/v1/atas/${ata.id}` : "/api/v1/atas", {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload(values, keys)),
      });
      if (editing) {
        setOpen(false);
        onSaved?.(saved);
      } else {
        setFlash("ATA cadastrada como rascunho.");
        router.push(`/atas/${saved.id}`);
      }
    } catch (err) {
      if (handleSessionError(err)) return;
      const error = err instanceof ApiError ? err : unavailable();
      const named: Record<string, string> = {};
      for (const key of ORDER) if (error.fields[key]) named[key] = error.fields[key];
      if (CODE_FIELD[error.code]) named[CODE_FIELD[error.code]] = error.message;
      if (Object.keys(named).length > 0) setErrors(named);
      else setFailure(error);
      if (editing && error.status === 409) onStale?.();
    } finally {
      setPending(false);
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
        {editing ? (
          <Button variant="outline">
            <Pencil aria-hidden />
            Editar
          </Button>
        ) : (
          <Button>
            <Plus aria-hidden />
            Cadastrar ATA
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto">
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>{editing ? `Editar ATA ${ata.number}` : "Cadastrar ATA"}</DialogTitle>
            <DialogDescription>
              {locked
                ? "Depois de ativada, valores e prazos só mudam por aditivo."
                : editing
                  ? "Enquanto rascunho, todos os campos podem mudar."
                  : "A ATA é cadastrada como rascunho e passa a valer quando for ativada."}
            </DialogDescription>
          </DialogHeader>
          {FIELDS.map((field) => {
            const readOnly = locked && field.locks;
            return (
              <Field key={field.key} id={`ata-${field.key.replace(".", "-")}`} label={field.label} error={errors[field.key]}>
                {(props) => (
                  <Input
                    {...props}
                    type={field.type === "date" ? "date" : "text"}
                    inputMode={field.type === "money" ? "decimal" : field.key === "fornecedor.cnpj" ? "numeric" : undefined}
                    placeholder={field.type === "money" ? "0,00" : field.key === "fornecedor.cnpj" ? "00.000.000/0000-00" : undefined}
                    value={values[field.key]}
                    readOnly={readOnly}
                    disabled={readOnly}
                    onChange={(e) => set(field.key, e.target.value)}
                  />
                )}
              </Field>
            );
          })}
          {failure && <ErrorNotice error={failure} />}
          <DialogFooter>
            <Button type="submit" disabled={pending}>
              {pending ? "Salvando..." : editing ? "Salvar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
