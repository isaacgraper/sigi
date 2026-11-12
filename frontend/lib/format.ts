const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "America/Sao_Paulo",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** `dd/MM/yyyy` in America/Sao_Paulo, whatever the browser's own zone. */
export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
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

/**
 * A quantity typed in pt-BR (`1.000`, `2,5`) as the decimal text the API reads
 * (`1000`, `2.5`). Text to text, as money is: an extra decimal reaches the API
 * and is refused there (SPEC-0014 AC-0014-11).
 */
export function parseQuantity(typed: string): string {
  return parseMoney(typed);
}

/** A decimal from the API (`"1000.000"`) as pt-BR, without trailing zeros: `1.000`, `2,5`. */
export function formatQuantity(decimal: string): string {
  const negative = decimal.trim().startsWith("-");
  const [whole, fraction = ""] = decimal.trim().replace(/^-/, "").split(".");
  const grouped = whole.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const kept = fraction.replace(/0+$/, "");
  return `${negative ? "-" : ""}${grouped}${kept ? `,${kept}` : ""}`;
}

/**
 * A unit price from the API (`"0.00599"`, `"1.50000"`) with at least 2 and up to
 * 5 decimals, `R$ 0,00599`, `R$ 1,50`: the five places are kept only where they
 * say something (ADR-0016, AC-0014-21).
 */
export function formatUnitPrice(decimal: string): string {
  const [whole, fraction = ""] = decimal.trim().split(".");
  const kept = fraction.replace(/0+$/, "").padEnd(2, "0");
  return formatBRL(`${whole}.${kept}`);
}

/**
 * The CNPJ as 00.000.000/0000-00, as far as it has been typed. Letters are kept
 * and uppercased, because the alphanumeric CNPJ carries them (SPEC-0002 AC-0002-25);
 * whether they are in the right place is the API's to say.
 */
export function formatCnpj(typed: string): string {
  const d = typed.toUpperCase().replace(/[^0-9A-Z]/g, "").slice(0, 14);
  const parts = [d.slice(0, 2), d.slice(2, 5), d.slice(5, 8), d.slice(8, 12), d.slice(12, 14)];
  let out = parts[0];
  if (parts[1]) out += `.${parts[1]}`;
  if (parts[2]) out += `.${parts[2]}`;
  if (parts[3]) out += `/${parts[3]}`;
  if (parts[4]) out += `-${parts[4]}`;
  return out;
}
