"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Notice } from "@/components/auth/auth-layout";
import { Field, focusFirst } from "@/components/atas/field";
import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AtaDetail } from "@/lib/atas";
import { ApiError, unavailable } from "@/lib/errors";
import { setFlash } from "@/lib/flash";
import { formatBRL, formatCnpj, parseMoney } from "@/lib/format";
import { apiJson } from "@/lib/session";
import { cn } from "@/lib/utils";

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

interface FieldSpec {
  key: Key;
  label: string;
  type?: "date" | "money";
  optional?: boolean;
  /** Past "rascunho" it changes only through an aditivo (AC-0002-24). */
  locks?: boolean;
  wide?: boolean;
}

// The ATA page's own grouping, so the form looks like the page it produces (AC-0013-07).
const SECTIONS: { title: string; hint: string; fields: FieldSpec[] }[] = [
  {
    title: "Identificação",
    hint: "O número é único entre as ATAs.",
    fields: [
      { key: "number", label: "Número", locks: true },
      { key: "organ", label: "Órgão" },
      { key: "subject", label: "Objeto", wide: true },
    ],
  },
  {
    title: "Fornecedor",
    hint: "Se o CNPJ já estiver cadastrado, a razão social dele é mantida.",
    fields: [
      { key: "fornecedor.cnpj", label: "CNPJ do fornecedor", locks: true },
      { key: "fornecedor.legal_name", label: "Razão social", locks: true },
    ],
  },
  {
    title: "Vigência",
    hint: "O fim precisa ser depois do início.",
    fields: [
      { key: "vigencia_inicio", label: "Início da vigência", type: "date", locks: true },
      { key: "vigencia_fim", label: "Fim da vigência", type: "date", locks: true },
      { key: "issued_on", label: "Data de emissão (opcional)", type: "date", optional: true, locks: true },
    ],
  },
  {
    title: "Valores",
    hint: "O reajuste vence um ano depois do orçamento planilhado.",
    fields: [
      { key: "total_value", label: "Valor total (R$)", type: "money", locks: true },
      { key: "budget_date", label: "Data do orçamento planilhado", type: "date", locks: true },
    ],
  },
];

const FIELDS = SECTIONS.flatMap((section) => section.fields);
const ORDER = FIELDS.map((field) => field.key);

// Refusals that name no field in `fields` but belong to one (SPEC-0002 §3.7).
const CODE_FIELD: Record<string, Key> = { ATA_DUPLICADA: "number" };

type Values = Record<Key, string>;

const EMPTY = Object.fromEntries(ORDER.map((key) => [key, ""])) as Values;

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
 * The registration (AC-0013-07 to -09) and the edit (AC-0013-14), as a page.
 * Past "rascunho" the figures change only through an aditivo, so they are shown
 * read-only; the API refuses them anyway (AC-0002-24).
 */
export function AtaForm({ ata, onStale }: { ata?: AtaDetail; onStale?: () => void }) {
  const { handleSessionError } = useSession();
  const router = useRouter();
  const editing = ata !== undefined;
  const locked = editing && ata.status !== "rascunho";
  const initial = ata ? valuesOf(ata) : EMPTY;
  const back = editing ? `/atas/${ata.id}` : "/atas";

  const [values, setValues] = useState<Values>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    focusFirst(ORDER, errors, "ata");
  }, [errors]);

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
      router.push(back);
      return;
    }

    setPending(true);
    try {
      const saved = await apiJson<AtaDetail>(editing ? `/api/v1/atas/${ata.id}` : "/api/v1/atas", {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload(values, keys)),
      });
      setFlash(editing ? "ATA atualizada." : "ATA cadastrada como rascunho.");
      router.push(`/atas/${saved.id}`);
    } catch (err) {
      if (handleSessionError(err)) return;
      const error = err instanceof ApiError ? err : unavailable();
      const named: Record<string, string> = {};
      for (const key of ORDER) if (error.fields[key]) named[key] = error.fields[key];
      if (CODE_FIELD[error.code]) named[CODE_FIELD[error.code]] = error.message;
      if (Object.keys(named).length > 0) setErrors(named);
      else setFailure(error);
      if (editing && error.status === 409) onStale?.();
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      {locked && <Notice>Depois de ativada, valores e prazos só mudam por aditivo.</Notice>}

      <div className="divide-y rounded-lg border border-border/70 bg-card shadow-sm">
        {SECTIONS.map((section) => (
          <section
            key={section.title}
            aria-labelledby={`secao-${section.title}`}
            className="grid gap-x-8 gap-y-4 p-5 sm:p-6 md:grid-cols-[13rem_minmax(0,1fr)]"
          >
            <div className="space-y-1">
              <h2 id={`secao-${section.title}`} className="text-base font-normal">
                {section.title}
              </h2>
              <p className="text-sm font-light text-muted-foreground">{section.hint}</p>
            </div>
            <div className="grid min-w-0 gap-4 sm:grid-cols-2">
              {section.fields.map((field) => {
                const readOnly = locked && field.locks;
                return (
                  <div key={field.key} className={cn("min-w-0", field.wide && "sm:col-span-2")}>
                    <Field id={`ata-${field.key.replace(".", "-")}`} label={field.label} error={errors[field.key]}>
                      {(props) => (
                        <Input
                          {...props}
                          type={field.type === "date" ? "date" : "text"}
                          inputMode={
                            field.type === "money" ? "decimal" : field.key === "fornecedor.cnpj" ? "numeric" : undefined
                          }
                          placeholder={
                            field.type === "money"
                              ? "0,00"
                              : field.key === "fornecedor.cnpj"
                                ? "00.000.000/0000-00"
                                : undefined
                          }
                          value={values[field.key]}
                          readOnly={readOnly}
                          disabled={readOnly}
                          onChange={(e) => set(field.key, e.target.value)}
                        />
                      )}
                    </Field>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      {failure && <ErrorNotice error={failure} />}

      {/* The actions stay in view however long the form (AC-0013-07). */}
      <div className="sticky bottom-0 z-10 -mx-4 flex flex-col-reverse gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:flex-row sm:justify-end sm:px-6">
        <Link href={back} className={buttonVariants({ variant: "outline" })}>
          Voltar
        </Link>
        <Button type="submit" disabled={pending}>
          {pending ? "Salvando..." : editing ? "Salvar" : "Cadastrar"}
        </Button>
      </div>
    </form>
  );
}
