"use client";

import { useEffect, useState } from "react";

import { useSession } from "@/components/session-provider";
import { apiJson } from "@/lib/session";

/**
 * Several reads at once, each answer by its path; one that fails is left out,
 * so a record the perfil may not open reads as absent, never as an error.
 */
export function useReads<T>(paths: string[]): Record<string, T> {
  const { handleSessionError } = useSession();
  const [answers, setAnswers] = useState<Record<string, T>>({});
  const key = [...paths].sort().join("|");

  useEffect(() => {
    if (key === "") return;
    let cancelled = false;
    void Promise.all(
      key.split("|").map((path) =>
        apiJson<T>(path).then(
          (value) => [path, value] as const,
          (err: unknown) => {
            handleSessionError(err);
            return null;
          },
        ),
      ),
    ).then((results) => {
      if (cancelled) return;
      const next: Record<string, T> = {};
      for (const result of results) if (result) next[result[0]] = result[1];
      setAnswers(next);
    });
    return () => {
      cancelled = true;
    };
  }, [key, handleSessionError]);

  return answers;
}
