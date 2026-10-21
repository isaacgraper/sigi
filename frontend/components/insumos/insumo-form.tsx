"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { GrupoSelect } from "@/components/insumos/grupo-select";
import { useSession } from "@/components/session-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field, focusFirst } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { remember } from "@/lib/api-cache";
import { ApiError, unavailable } from "@/lib/errors";
import { formatQuantity, parseQuantity } from "@/lib/format";
import {
  CLEARABLE,
  HELP,
  INSUMO_CODE_FIELD,
  INSUMO_EMPTY,
  INSUMO_FIELDS,
  INSUMO_ORDER,
} from "@/lib/insumos/constants";
import type { GrupoNode, InsumoDetail, InsumoKey, InsumoValues } from "@/lib/insumos/types";
import { apiJson } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * The registration (AC-0014-08, -09) and the correction (AC-0014-10), as a page.
 * Saved directly: an insumo is a short form, and "Editar" corrects a mistake.
 * The SKU is not editable here; it changes only by "Alterar SKU" (AC-0003-11).
 */
export function InsumoForm({ insumo, tree }: { insumo?: InsumoDetail; tree: GrupoNode[] }) {
  const { handleSessionError } = useSession();
  const router = useRouter();
  const editing = insumo !== undefined;
  const initial = insumo ? valuesOf(insumo) : INSUMO_EMPTY;
  const back = editing ? `/insumos/${insumo.id}` : "/insumos";

  const [values, setValues] = useState<InsumoValues>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    focusFirst(INSUMO_ORDER, errors, "insumo");
  }, [errors]);

  function set(key: InsumoKey, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(null);

    // Only that a required field is filled in; the rest is the API's (AC-0014-09).
    const empty: Record<string, string> = {};
    for (const field of INSUMO_FIELDS) {
      if (editing && field.key === "sku") continue;
      if (!field.optional && !values[field.key].trim()) empty[field.key] = "Campo obrigatório.";
    }
    setErrors(empty);
    if (Object.keys(empty).length > 0) return;

    const keys = editing
      ? INSUMO_ORDER.filter((key) => key !== "sku" && values[key].trim() !== initial[key].trim())
      : INSUMO_ORDER;
    if (keys.length === 0) {
      router.push(back);
      return;
    }

    setPending(true);
    try {
      const saved = await apiJson<InsumoDetail>(editing ? `/api/v1/insumos/${insumo.id}` : "/api/v1/insumos", {
        method: editing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload(values, keys)),
      });
      // The page that opens is the result; no banner repeats it (AC-0014-08, -10).
      remember(`/api/v1/insumos/${saved.id}`, saved);
      router.push(`/insumos/${saved.id}`);
    } catch (err) {
      if (handleSessionError(err)) return;
      const error = err instanceof ApiError ? err : unavailable();
      const named: Record<string, string> = {};
      for (const key of INSUMO_ORDER) if (error.fields[key]) named[key] = error.fields[key];
      if (INSUMO_CODE_FIELD[error.code]) named[INSUMO_CODE_FIELD[error.code]] = error.message;
      if (Object.keys(named).length > 0) setErrors(named);
      else setFailure(error);
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-6">
      <div className="grid gap-4 rounded-lg border border-border/70 bg-card p-5 shadow-sm sm:grid-cols-2 sm:p-6">
        {INSUMO_FIELDS.map((field) => (
          <div key={field.key} className={cn("min-w-0", field.wide && "sm:col-span-2")}>
            <Field
              id={`insumo-${field.key}`}
              label={field.label}
              help={HELP[field.key]}
              error={errors[field.key]}
              hint={editing && field.key === "sku" ? "Para mudar o SKU, use Alterar SKU na página do insumo." : undefined}
            >
              {(props) =>
                field.key === "grupo_id" ? (
                  <GrupoSelect {...props} tree={tree} value={values.grupo_id} onChange={(value) => set("grupo_id", value)} />
                ) : (
                  <Input
                    {...props}
                    className={cn(field.mono && "font-mono")}
                    readOnly={editing && field.key === "sku"}
                    inputMode={field.quantity ? "decimal" : undefined}
                    autoCapitalize={field.key === "sku" ? "characters" : undefined}
                    placeholder={field.key === "sku" ? "CLORDEG21" : field.key === "unit" ? "UN" : undefined}
                    value={values[field.key]}
                    onChange={(e) => set(field.key, e.target.value)}
                  />
                )
              }
            </Field>
          </div>
        ))}
      </div>

      {failure && <ErrorNotice error={failure} />}

      <div className="sticky bottom-0 z-10 -mx-4 flex flex-col-reverse gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:flex-row sm:justify-end sm:px-6">
        <Link href={back} className={buttonVariants({ variant: "outline" })}>
          Voltar
        </Link>
        <Button type="submit" disabled={pending}>
          {editing ? (pending ? "Salvando..." : "Salvar") : pending ? "Cadastrando..." : "Cadastrar insumo"}
        </Button>
      </div>
    </form>
  );
}

function valuesOf(insumo: InsumoDetail): InsumoValues {
  return {
    sku: insumo.sku,
    description: insumo.description,
    unit: insumo.unit,
    grupo_id: insumo.grupo_id,
    codigo_doms: insumo.codigo_doms ?? "",
    external_code: insumo.external_code ?? "",
    reference_quantity: insumo.reference_quantity ? formatQuantity(insumo.reference_quantity) : "",
  };
}

function payload(values: InsumoValues, keys: InsumoKey[]): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const key of keys) {
    const value = values[key].trim();
    // An optional field emptied is sent as null, which clears it (AC-0014-10).
    if (!value && CLEARABLE.includes(key)) body[key] = null;
    else body[key] = key === "reference_quantity" ? parseQuantity(value) : value;
  }
  return body;
}
