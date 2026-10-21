"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Field, focusFirst } from "@/components/ui/field";
import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { remember } from "@/lib/api-cache";
import {
  FORM_CODE_FIELD,
  FORM_EMPTY,
  FORM_FIELDS,
  FORM_ORDER,
  FORM_SECTIONS,
  REVIEW_EMPTY,
} from "@/lib/atas/constants";
import type { AtaDetail, FormField, FormKey, FormValues } from "@/lib/atas/types";
import { ApiError, unavailable } from "@/lib/errors";
import { formatBRL, formatCnpj, formatDay, parseMoney } from "@/lib/format";
import { apiJson } from "@/lib/session";
import { cn } from "@/lib/utils";

function valuesOf(ata: AtaDetail): FormValues {
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

function payload(values: FormValues, keys: FormKey[]): Record<string, unknown> {
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
 * The registration (AC-0013-07 to -09) and the correction (AC-0013-14), as a page.
 * A registration is reviewed before anything is sent, and the ATA is saved
 * vigente only when the gestor confirms it; a correction is saved directly.
 */
export function AtaForm({ ata, onStale }: { ata?: AtaDetail; onStale?: () => void }) {
  const { handleSessionError } = useSession();
  const router = useRouter();
  const editing = ata !== undefined;
  const initial = ata ? valuesOf(ata) : FORM_EMPTY;
  const back = editing ? `/atas/${ata.id}` : "/atas";

  const [values, setValues] = useState<FormValues>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const review = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    focusFirst(FORM_ORDER, errors, "ata");
  }, [errors]);

  useEffect(() => {
    if (reviewing) review.current?.focus();
  }, [reviewing]);

  function set(key: FormKey, value: string) {
    setValues((current) => ({ ...current, [key]: key === "fornecedor.cnpj" ? formatCnpj(value) : value }));
  }

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(null);

    // Only that a required field is filled in; the rest is the API's (AC-0013-08).
    const empty: Record<string, string> = {};
    for (const field of FORM_FIELDS) {
      if (!field.optional && !values[field.key].trim()) empty[field.key] = "Campo obrigatório.";
    }
    setErrors(empty);
    if (Object.keys(empty).length > 0) return;

    if (!editing) {
      setReviewing(true);
      return;
    }
    const keys = FORM_ORDER.filter((key) => values[key].trim() !== initial[key].trim());
    if (keys.length === 0) {
      router.push(back);
      return;
    }
    void save(keys);
  }

  async function save(keys: FormKey[]) {
    setPending(true);
    try {
      const saved = await apiJson<AtaDetail>(editing ? `/api/v1/atas/${ata.id}` : "/api/v1/atas", {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload(values, keys)),
      });
      // The page that opens is the result; no banner repeats it (AC-0013-07, -14).
      // It draws from the write's own reply rather than asking again.
      remember(`/api/v1/atas/${saved.id}`, saved);
      router.push(`/atas/${saved.id}`);
    } catch (err) {
      if (handleSessionError(err)) return;
      const error = err instanceof ApiError ? err : unavailable();
      const named: Record<string, string> = {};
      for (const key of FORM_ORDER) if (error.fields[key]) named[key] = error.fields[key];
      if (FORM_CODE_FIELD[error.code]) named[FORM_CODE_FIELD[error.code]] = error.message;
      setReviewing(false);
      if (Object.keys(named).length > 0) setErrors(named);
      else setFailure(error);
      if (editing && error.status === 409) onStale?.();
      setPending(false);
    }
  }

  if (reviewing) {
    return (
      <div className="space-y-6">
        <div className="space-y-1">
          <h2 ref={review} tabIndex={-1} className="text-lg font-normal outline-none">
            Confira os dados antes de cadastrar
          </h2>
          <p className="text-sm font-light text-muted-foreground">
            A ATA é cadastrada vigente. Depois, os dados podem ser corrigidos em Editar.
          </p>
        </div>
        <div data-testid="ata-review" className="divide-y rounded-lg border border-border/70 bg-card shadow-sm">
          {FORM_SECTIONS.map((section) => (
            <section
              key={section.title}
              aria-label={section.title}
              className="grid gap-x-8 gap-y-3 p-5 sm:p-6 md:grid-cols-[13rem_minmax(0,1fr)]"
            >
              <h3 className="text-base font-normal">{section.title}</h3>
              <dl className="grid min-w-0 gap-4 sm:grid-cols-2">
                {section.fields.map((field) => (
                  <div key={field.key} className={cn("min-w-0 space-y-1", field.wide && "sm:col-span-2")}>
                    <dt className="text-xs font-light text-muted-foreground">{field.label}</dt>
                    <dd className="break-words text-sm tabular-nums">{reviewed(field, values[field.key])}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
        <div className="sticky bottom-0 z-10 -mx-4 flex flex-col-reverse gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:flex-row sm:justify-end sm:px-6">
          <Button type="button" variant="outline" disabled={pending} onClick={() => setReviewing(false)}>
            Voltar e corrigir
          </Button>
          <Button type="button" disabled={pending} onClick={() => void save(FORM_ORDER)}>
            {pending ? "Cadastrando..." : "Confirmar cadastro"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      <div className="divide-y rounded-lg border border-border/70 bg-card shadow-sm">
        {FORM_SECTIONS.map((section) => (
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
              {section.fields.map((field) => (
                <div key={field.key} className={cn("min-w-0", field.wide && "sm:col-span-2")}>
                  <Field
                    id={`ata-${field.key.replace(".", "-")}`}
                    label={field.label}
                    help={field.help}
                    error={errors[field.key]}
                  >
                    {(props) => (
                      <Input
                        {...props}
                        type={field.type === "date" ? "date" : "text"}
                        inputMode={field.type === "money" ? "decimal" : undefined}
                        autoCapitalize={field.key === "fornecedor.cnpj" ? "characters" : undefined}
                        placeholder={
                          field.type === "money"
                            ? "0,00"
                            : field.key === "fornecedor.cnpj"
                              ? "00.000.000/0000-00"
                              : undefined
                        }
                        value={values[field.key]}
                        onChange={(e) => set(field.key, e.target.value)}
                      />
                    )}
                  </Field>
                </div>
              ))}
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
          {editing ? (pending ? "Salvando..." : "Salvar") : "Revisar cadastro"}
        </Button>
      </div>
    </form>
  );
}

/** A typed value as the review shows it: dates and money as they will read on the ATA page. */
function reviewed(field: FormField, value: string): string {
  const typed = value.trim();
  if (!typed) return REVIEW_EMPTY;
  if (field.type === "date") return formatDay(typed);
  if (field.type === "money") return formatBRL(parseMoney(typed));
  return typed;
}
