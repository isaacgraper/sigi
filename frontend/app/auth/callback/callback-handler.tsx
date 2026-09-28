"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { FormMessage } from "@/components/auth/auth-layout";
import { buttonVariants } from "@/components/ui/button";
import { ApiError, GENERIC_FAILURE } from "@/lib/errors";
import { takeNext } from "@/lib/flash";
import { safeReturnPath } from "@/lib/return-path";
import { adopt } from "@/lib/session";

const CANCELLED = "A entrada institucional foi cancelada ou não foi autorizada. Tente novamente.";

export function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const [failure, setFailure] = useState<string | null>(null);
  const started = useRef(false);

  const code = params.get("code");
  const state = params.get("state");
  // The provider sent the browser back without a code: nothing to exchange,
  // and the API is not called (AC-0010-48).
  const cancelled = Boolean(params.get("error")) || !code || !state;
  const error = cancelled ? CANCELLED : failure;

  useEffect(() => {
    // The code is single-use: React's development double effect must not
    // spend it twice.
    if (cancelled || !code || !state || started.current) return;
    started.current = true;
    const query = new URLSearchParams({ code, state });
    fetch(`/api/v1/auth/oidc/callback?${query}`, { credentials: "same-origin", cache: "no-store" })
      .then(adopt)
      .then(() => router.replace(safeReturnPath(takeNext())))
      .catch((err: unknown) => {
        window.history.replaceState(null, "", "/auth/callback");
        setFailure(err instanceof ApiError ? err.message : GENERIC_FAILURE);
      });
  }, [cancelled, code, state, router]);

  if (!error) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        Concluindo a entrada...
      </p>
    );
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Não foi possível entrar</h1>
      <FormMessage>{error}</FormMessage>
      <Link href="/login" className={buttonVariants({ variant: "outline", className: "w-full" })}>
        Tentar novamente
      </Link>
    </div>
  );
}
