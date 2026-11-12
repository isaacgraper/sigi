import { Status } from "@/components/ui/status";
import { ataStatus } from "@/lib/atas/status";
import type { Ata } from "@/lib/atas/types";

/** "Vigente", "Vigente · a vencer", "Suspensa", "Cancelada" (AC-0013-03). */
export function AtaStatus({ ata }: { ata: Pick<Ata, "status" | "situacao_vigencia"> }) {
  const { label, situacao, tone } = ataStatus(ata);
  return (
    <Status tone={tone}>
      <span data-testid="ata-status">{label}</span>
      {situacao && (
        <span data-testid="ata-situacao" className="text-muted-foreground">
          · {situacao}
        </span>
      )}
    </Status>
  );
}
