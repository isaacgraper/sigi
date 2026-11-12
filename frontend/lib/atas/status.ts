import { SITUACAO_LABEL, SOON_DAYS, STATUS_LABEL } from "@/lib/atas/constants";
import type { Ata, Urgency } from "@/lib/atas/types";
import type { StatusTone } from "@/lib/types";

/**
 * The ATA's status as one line of text (DESIGN.md §4, AC-0013-03): the status
 * word, then its situação only where it says something, for an ATA still
 * running and not plainly vigente. Both values are the API's; this only
 * chooses which to show and whether a dot asks for attention.
 */
export function ataStatus(ata: Pick<Ata, "status" | "situacao_vigencia">): {
  label: string;
  situacao: string | null;
  tone: StatusTone;
} {
  const label = STATUS_LABEL[ata.status];
  const running = ata.status === "vigente" || ata.status === "suspensa";
  if (!running) return { label, situacao: null, tone: "muted" };
  const situacao = ata.situacao_vigencia === "vigente" ? null : SITUACAO_LABEL[ata.situacao_vigencia].toLowerCase();
  const tone =
    ata.situacao_vigencia === "vencida"
      ? "danger"
      : ata.situacao_vigencia === "a_vencer" || ata.status === "suspensa"
        ? "attention"
        : "neutral";
  return { label, situacao, tone };
}

/**
 * How close a due date is, for colour only (AC-0013-02): past it, within
 * SOON_DAYS of it, or further. Which ATAs are due at all is the API's rule;
 * this only says how loudly to show them.
 */
export function urgency(remaining: number): Urgency {
  if (remaining < 0) return "overdue";
  return remaining <= SOON_DAYS ? "soon" : "later";
}
