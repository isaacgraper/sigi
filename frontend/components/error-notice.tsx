import { FormMessage } from "@/components/auth/auth-layout";
import { ContactGestor } from "@/components/contact";
import { NEEDS_GESTOR_CODES } from "@/lib/constants";
import { ApiError } from "@/lib/errors";


/** An error for the person on the page: the message, and who to ask when it helps. */
export function ErrorNotice({ error, id }: { error: ApiError; id?: string }) {
  return (
    <div className="space-y-2">
      <FormMessage id={id}>{error.message}</FormMessage>
      {NEEDS_GESTOR_CODES.has(error.code) && <ContactGestor reference={error.correlationId} />}
    </div>
  );
}

/** A message the page itself owns, with the code that decides the contact. */
export function localError(code: string, message: string): ApiError {
  return new ApiError({ status: 0, code, message });
}
