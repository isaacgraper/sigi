"use client";

import { useCallback, useEffect, useState } from "react";

import { useSession } from "@/components/session-provider";
import { cached, remember } from "@/lib/api-cache";
import { ApiError, unavailable } from "@/lib/errors";
import { apiJson } from "@/lib/session";

/**
 * One API read for a page or a block: the last answer at once when this tab has
 * seen it (AC-0011-18), the fresh one when it lands, and the refusal otherwise.
 * The answer is kept with the path it answers, so a new path never shows the
 * previous one's data. `path` null reads nothing.
 */
export function useRead<T>(path: string | null) {
  const { handleSessionError } = useSession();
  const [answer, setAnswer] = useState<{ path: string; data?: T; failure?: ApiError } | null>(null);
  const [version, setVersion] = useState(0);

  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    apiJson<T>(path)
      .then((value) => !cancelled && setAnswer({ path, data: value }))
      .catch((err: unknown) => {
        if (cancelled || handleSessionError(err)) return;
        setAnswer((current) => ({
          path,
          data: current?.path === path ? current.data : undefined,
          failure: err instanceof ApiError ? err : unavailable(),
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [path, version, handleSessionError]);

  const own = path !== null && answer?.path === path ? answer : null;
  const remembered = path === null ? undefined : cached<T>(path);
  const data = own?.data ?? remembered ?? null;

  /** Show a write's own reply as this read's answer, without asking again. */
  const replace = useCallback(
    (value: T) => {
      if (path === null) return;
      setAnswer({ path: path, data: remember(path, value) });
    },
    [path],
  );

  return { data, failure: own?.failure ?? null, reload, replace };
}
