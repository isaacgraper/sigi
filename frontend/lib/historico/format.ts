/** A change's value as a person reads it, by its tipo (SPEC-0017 AC-0017-01). */
import { formatBRL, formatDate, formatDay, formatQuantity } from "@/lib/format";
import { ATALHO_TIPOS, ISO_DAY, NO, NOTHING, STATUS_VALUE_LABEL, YES } from "@/lib/historico/constants";
import type { Alteracao, Atalho, Evento, Tipo, Valor } from "@/lib/historico/types";

/** One value: a date `dd/MM/yyyy`, money in R$, a quantity in pt-BR, a status by its name. */
export function formatValor(tipo: Tipo, valor: Valor, names: Record<string, string> = {}): string {
  if (valor === null || valor === undefined || valor === "") return NOTHING;
  if (typeof valor === "boolean") return valor ? YES : NO;
  if (Array.isArray(valor)) {
    if (valor.length === 0) return NOTHING;
    return valor.map((line) => (line.quantidade ? formatQuantity(String(line.quantidade)) : NOTHING)).join(" · ");
  }
  if (typeof valor === "object") return NOTHING;
  const text = String(valor);
  switch (tipo) {
    case "data":
      return ISO_DAY.test(text) ? formatDay(text) : formatDate(text);
    case "dinheiro":
      return formatBRL(text);
    case "quantidade":
      return formatQuantity(text);
    case "status":
      return STATUS_VALUE_LABEL[text] ?? text;
    case "referencia":
      return names[text] ?? text;
    default:
      return text;
  }
}

/** A detail's value, written with the tipo its text looks like. */
export function formatDetalhe(valor: Valor, names: Record<string, string> = {}): string {
  if (typeof valor === "string" && ISO_DAY.test(valor)) return formatDay(valor);
  if (typeof valor === "string" && STATUS_VALUE_LABEL[valor]) return STATUS_VALUE_LABEL[valor];
  if (typeof valor === "string" && names[valor]) return names[valor];
  if (Array.isArray(valor)) return valor.map(String).join(", ");
  return formatValor("texto", valor);
}

/** A creation has nothing before; a removal nothing after (AC-0017-03). */
export function kindOf(alteracoes: Alteracao[]): "created" | "removed" | "changed" {
  if (alteracoes.length === 0) return "changed";
  if (alteracoes.every((a) => a.antes === null) && alteracoes.length > 1) return "created";
  if (alteracoes.every((a) => a.depois === null) && alteracoes.length > 1) return "removed";
  return "changed";
}

/**
 * Whether an event changed what a shortcut keeps (AC-0017-11). A creation sets
 * its first values and changes none, so it never counts.
 */
export function matches(evento: Evento, atalho: Atalho | null): boolean {
  if (atalho === null) return true;
  if (kindOf(evento.alteracoes) === "created") return false;
  return evento.alteracoes.some((a) => ATALHO_TIPOS[atalho].includes(a.tipo));
}

const momentFormatter = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** When an event happened: `dd/MM/yyyy, HH:mm` in America/Sao_Paulo. */
export function formatMoment(iso: string): string {
  return momentFormatter.format(new Date(iso));
}
