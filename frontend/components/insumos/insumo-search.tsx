"use client";

import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { useSession } from "@/components/session-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PICKER_SIZE, SEARCH_DELAY_MS } from "@/lib/insumos/constants";
import type { Insumo, Substitute } from "@/lib/insumos/types";
import { apiJson } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * An "ativo" insumo searched by SKU or descrição (AC-0014-15, -23). The results
 * are buttons in the flow below the field, not a floating list, so a keyboard
 * reaches them with Tab and a phone shows them without covering the dialog.
 */
export function InsumoSearch({
  id,
  value,
  onChange,
  exclude,
  invalid,
  describedBy,
}: {
  id: string;
  value: Substitute | null;
  onChange: (value: Substitute | null) => void;
  exclude?: string;
  invalid?: boolean;
  describedBy?: string;
}) {
  const { handleSessionError } = useSession();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Insumo[] | null>(null);

  useEffect(() => {
    const typed = query.trim();
    if (!typed) return;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ q: typed, status: "ativo", size: String(PICKER_SIZE) });
      apiJson<{ items: Insumo[] }>(`/api/v1/insumos?${params}`)
        .then((page) => !cancelled && setResults(page.items.filter((insumo) => insumo.id !== exclude)))
        .catch((err: unknown) => {
          if (!cancelled && !handleSessionError(err)) setResults([]);
        });
    }, SEARCH_DELAY_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, exclude, handleSessionError]);

  if (value) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border px-3 py-2" data-testid="insumo-chosen">
        <span className="min-w-0 text-sm">
          <span className="font-mono text-xs">{value.sku}</span>
          <span className="text-muted-foreground"> · {value.description}</span>
        </span>
        <Button type="button" variant="ghost" size="sm" onClick={() => onChange(null)}>
          Trocar
        </Button>
      </div>
    );
  }

  const typed = query.trim();
  return (
    <div className="space-y-2">
      <div className="relative">
        <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          id={id}
          type="search"
          autoComplete="off"
          placeholder="SKU ou descrição"
          className="pl-9"
          aria-invalid={invalid ? true : undefined}
          aria-describedby={describedBy}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!e.target.value.trim()) setResults(null);
          }}
        />
      </div>
      {typed && results !== null && (
        <ul aria-label="Insumos encontrados" className="max-h-48 overflow-y-auto rounded-md border">
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm font-light text-muted-foreground">Nenhum insumo ativo encontrado.</li>
          )}
          {results.map((insumo) => (
            <li key={insumo.id}>
              <button
                type="button"
                data-testid="insumo-option"
                onClick={() => onChange({ id: insumo.id, sku: insumo.sku, description: insumo.description })}
                className={cn(
                  "flex w-full flex-col items-start px-3 py-2 text-left text-sm outline-none",
                  "focus-visible:bg-muted [@media(hover:hover)_and_(pointer:fine)]:hover:bg-muted",
                )}
              >
                <span className="font-mono text-xs">{insumo.sku}</span>
                <span className="text-muted-foreground">
                  {insumo.description} ({insumo.unit})
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
