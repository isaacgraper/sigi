"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ErrorNotice, localError } from "@/components/error-notice";
import { ApiError, readError, unavailable } from "@/lib/errors";
import { useHydrated } from "@/lib/use-hydrated";

const MISMATCH = "As senhas não conferem.";

/**
 * Set a password with a single-use token from a link: invitation activation and
 * reset confirmation share every rule except what happens on success.
 */
export function TokenPasswordForm({
  endpoint,
  title,
  description,
  missingToken,
  finalCodes,
  submitLabel,
  onSuccess,
}: {
  endpoint: string;
  title: string;
  description: string;
  missingToken: string;
  /** Refusals after which this link can never work (spent, expired). */
  finalCodes: string[];
  submitLabel: string;
  onSuccess: (response: Response) => Promise<void>;
}) {
  const params = useSearchParams();
  const hydrated = useHydrated();
  // Read once, then kept only in memory: the address bar loses it at once.
  const [token] = useState(() => params.get("token"));
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [final, setFinal] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (window.location.search) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || !token) return;
    if (password !== confirmation) {
      setError(localError("PASSWORD_MISMATCH", MISMATCH));
      return;
    }
    setPending(true);
    setError(null);
    try {
      let response: Response;
      try {
        response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, password }),
          credentials: "same-origin",
          cache: "no-store",
        });
      } catch {
        throw unavailable();
      }
      if (!response.ok) throw await readError(response);
      await onSuccess(response);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : null;
      setError(apiError ?? unavailable());
      if (apiError && finalCodes.includes(apiError.code)) setFinal(true);
      setPassword("");
      setConfirmation("");
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-normal tracking-tight">{title}</h1>
        <p className="text-sm font-light text-muted-foreground">{description}</p>
      </div>

      {!token && <ErrorNotice error={localError("MISSING_TOKEN", missingToken)} />}
      {token && final && error && <ErrorNotice error={error} />}

      {token && !final && (
        <form className="space-y-4" method="post" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="password">Nova senha</Label>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmation">Confirme a senha</Label>
            <PasswordInput
              id="confirmation"
              autoComplete="new-password"
              required
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
            />
          </div>
          {error && <ErrorNotice error={error} />}
          <Button type="submit" className="w-full" disabled={!hydrated || pending}>
            {pending ? "Enviando..." : submitLabel}
          </Button>
        </form>
      )}
    </div>
  );
}
