import { Status } from "@/components/ui/status";
import { SITUACAO_LABEL } from "@/lib/insumos/constants";
import type { Insumo } from "@/lib/insumos/types";

/** "Ativo", "Descontinuado", "Substituído por CLORDEG22" (AC-0014-04). */
export function InsumoSituacao({ insumo }: { insumo: Pick<Insumo, "status" | "substitute"> }) {
  const active = insumo.status === "ativo";
  return (
    <Status tone={active ? "neutral" : "muted"} data-testid="insumo-situacao">
      {SITUACAO_LABEL[insumo.status]}
      {insumo.status === "substituido" && insumo.substitute && ` por ${insumo.substitute.sku}`}
    </Status>
  );
}
