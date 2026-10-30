import { Status } from "@/components/ui/status";
import { STAGE_LABEL, STAGE_TONE } from "@/lib/notas-empenho/constants";
import type { NeStatus } from "@/lib/notas-empenho/types";

/** The NE's stage as text, a dot only while saldo is held in reserve (DESIGN.md §4). */
export function NeStage({ status }: { status: NeStatus }) {
  return (
    <Status tone={STAGE_TONE[status]}>
      <span data-testid="ne-stage">{STAGE_LABEL[status]}</span>
    </Status>
  );
}

/** One small figure above a list: a label and a number (AC-0015-01). */
export function Figure({ testId, label, value }: { testId: string; label: string; value: number | string }) {
  return (
    <div data-testid={testId} className="rounded-md border border-border/70 bg-card px-4 py-3 shadow-sm sm:min-w-40">
      <p className="text-xs font-light text-muted-foreground">{label}</p>
      <p className="text-2xl font-normal leading-tight tabular-nums">{value}</p>
    </div>
  );
}
