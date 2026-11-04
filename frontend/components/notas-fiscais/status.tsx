import { Status } from "@/components/ui/status";
import {
  NF_STATUS_LABEL,
  NF_STATUS_TONE,
  QUARENTENA_LABEL,
} from "@/lib/notas-fiscais/constants";
import type { NfStatus } from "@/lib/notas-fiscais/types";

/** The NF's status as text, and the quarantine beside it when it holds (AC-0016-01, -08). */
export function NfStatusBadge({
  status,
  quarentena,
}: {
  status: NfStatus;
  quarentena: boolean;
}) {
  return (
    <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
      <Status tone={NF_STATUS_TONE[status]}>
        <span data-testid="nf-status">{NF_STATUS_LABEL[status]}</span>
      </Status>
      {quarentena && (
        <Status tone="attention">
          <span data-testid="nf-quarentena">{QUARENTENA_LABEL}</span>
        </Status>
      )}
    </span>
  );
}
