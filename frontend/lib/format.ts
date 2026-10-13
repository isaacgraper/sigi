const DATE = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** `dd/MM/yyyy` in America/Sao_Paulo, whatever the browser's own zone. */
export function formatDate(iso: string): string {
  return DATE.format(new Date(iso));
}

/**
 * A calendar date (`2026-12-31`) as `dd/MM/yyyy`. It is not an instant, so it
 * never goes through `Date`: at UTC−3, midnight UTC is still the day before.
 */
export function formatDay(isoDate: string): string {
  const [year, month, day] = isoDate.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

/**
 * A decimal from the API (`"1234567.89"`) as `R$ 1.234.567,89`, digit by digit,
 * so a NUMERIC(15,2) never loses a cent to a float.
 */
export function formatBRL(decimal: string): string {
  const negative = decimal.trim().startsWith("-");
  const [whole, fraction = ""] = decimal.trim().replace(/^-/, "").split(".");
  const grouped = whole.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negative ? "-" : ""}R$ ${grouped},${fraction.padEnd(2, "0")}`;
}

/**
 * Money typed in pt-BR (`1.234.567,89`) as the decimal text the API reads
 * (`1234567.89`). Text to text: nothing is rounded, so a third decimal reaches
 * the API and is refused there (AC-0013-09).
 */
export function parseMoney(typed: string): string {
  return typed.replace(/R\$/g, "").replace(/\s/g, "").replace(/\./g, "").replace(",", ".");
}

/** The CNPJ's digits as 00.000.000/0000-00, as far as they have been typed. */
export function formatCnpj(typed: string): string {
  const d = typed.replace(/\D/g, "").slice(0, 14);
  const parts = [d.slice(0, 2), d.slice(2, 5), d.slice(5, 8), d.slice(8, 12), d.slice(12, 14)];
  let out = parts[0];
  if (parts[1]) out += `.${parts[1]}`;
  if (parts[2]) out += `.${parts[2]}`;
  if (parts[3]) out += `/${parts[3]}`;
  if (parts[4]) out += `-${parts[4]}`;
  return out;
}
