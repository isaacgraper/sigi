"use client";

import { useCallback, useEffect, useState } from "react";

import { useSession } from "@/components/session-provider";
import { focusFirst, isUnder } from "@/components/ui/field";
import { ApiError, unavailable } from "@/lib/errors";
import { apiJson } from "@/lib/session";

/**
 * One write from a dialog or a form, with the API's refusal landed on the field
 * it names (DESIGN.md §4): `fields` as they come, and `codeField` for the codes
 * a spec sends without them. A line of a list keeps its own key, `items.0.quantity`,
 * so the form can put it on that row. Anything else is the dialog's notice. Focus
 * moves to the first named field, in `order`, under ids `{prefix}-{key}` with the
 * dots as dashes.
 */
export function usePost(
  order: string[],
  codeField: Record<string, string>,
  prefix: string,
) {
  const { handleSessionError } = useSession();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    focusFirst(order, errors, prefix);
  }, [errors, order, prefix]);

  async function send<T>(
    path: string,
    body: Record<string, unknown> | undefined,
    empty: Record<string, string> = {},
    method = "POST",
  ): Promise<T | null> {
    setFailure(null);
    setErrors(empty);
    if (Object.keys(empty).length > 0) return null;
    setPending(true);
    try {
      return await apiJson<T>(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (err) {
      if (handleSessionError(err)) return null;
      const error = err instanceof ApiError ? err : unavailable();
      const named: Record<string, string> = {};
      for (const [key, message] of Object.entries(error.fields))
        if (order.some((field) => isUnder(key, field))) named[key] = message;
      if (codeField[error.code]) named[codeField[error.code]] = error.message;
      if (Object.keys(named).length > 0) setErrors(named);
      else setFailure(error);
      return null;
    } finally {
      setPending(false);
    }
  }

  const clear = useCallback(() => {
    setErrors({});
    setFailure(null);
  }, []);

  return { errors, failure, pending, send, clear };
}
