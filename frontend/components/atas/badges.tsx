import { Badge } from "@/components/ui/badge";
import {
  SITUACAO_LABEL,
  SITUACAO_TONE,
  type Situacao,
  STATUS_LABEL,
  STATUS_TONE,
  type Status,
} from "@/lib/atas";

export function StatusBadge({ status }: { status: Status }) {
  return (
    <Badge tone={STATUS_TONE[status]} data-testid="ata-status" className="whitespace-nowrap">
      {STATUS_LABEL[status]}
    </Badge>
  );
}

export function SituacaoBadge({ situacao }: { situacao: Situacao }) {
  return (
    <Badge tone={SITUACAO_TONE[situacao]} data-testid="ata-situacao" className="whitespace-nowrap">
      {SITUACAO_LABEL[situacao]}
    </Badge>
  );
}
