import type { AlertRow, DueRow } from "@/lib/atas/types";

/**
 * Both alerts as one list ordered by urgency (AC-0013-02). Which ATAs are in
 * each alert is the API's; this only puts its two answers side by side.
 */
export function dueRows(renovacao: AlertRow[], reajuste: AlertRow[]): DueRow[] {
  return [
    ...renovacao.map((row) => ({
      kind: "vencimento" as const,
      ata: row.ata,
      date: row.ata.vigencia_fim,
      remaining: row.days_remaining,
    })),
    ...reajuste.map((row) => ({
      kind: "reajuste" as const,
      ata: row.ata,
      date: row.ata.data_reajuste,
      remaining: row.days_remaining,
    })),
  ].sort((a, b) => a.remaining - b.remaining || a.ata.number.localeCompare(b.ata.number));
}

/** The API's days remaining, in words: "45 dias", "1 dia", "hoje", "há 3 dias". */
export function dueText(remaining: number): string {
  if (remaining === 0) return "hoje";
  const n = Math.abs(remaining);
  const days = n === 1 ? "1 dia" : `${n} dias`;
  return remaining > 0 ? days : `há ${days}`;
}
