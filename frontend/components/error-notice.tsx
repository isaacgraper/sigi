import { FormMessage } from "@/components/auth/auth-layout";
import { ContactGestor } from "@/components/contact";
import { ApiError } from "@/lib/errors";

// Failures the servidor cannot fix alone (AC-0010-57). Validation errors and a
// wrong password stay without a contact: the person can fix those.
const NEEDS_GESTOR = new Set([
  "UNAVAILABLE",
  "USUARIO_INATIVO",
  "PERFIL_NAO_AUTORIZADO",
  "USUARIO_NAO_PROVISIONADO",
  "INVITE_EXPIRED",
  "INVITE_ALREADY_USED",
  "RESET_EXPIRED",
  "RESET_ALREADY_USED",
  "MISSING_TOKEN",
]);

/** An error for the person on the page: the message, and who to ask when it helps. */
export function ErrorNotice({ error, id }: { error: ApiError; id?: string }) {
  return (
    <div className="space-y-2">
      <FormMessage id={id}>{error.message}</FormMessage>
      {NEEDS_GESTOR.has(error.code) && <ContactGestor reference={error.correlationId} />}
    </div>
  );
}

/** A message the page itself owns, with the code that decides the contact. */
export function localError(code: string, message: string): ApiError {
  return new ApiError({ status: 0, code, message });
}
