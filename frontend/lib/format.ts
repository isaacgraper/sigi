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
