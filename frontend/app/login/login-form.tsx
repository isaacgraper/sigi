"use client";

import { Building2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Notice } from "@/components/auth/auth-layout";
import { PasswordInput } from "@/components/auth/password-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorNotice } from "@/components/error-notice";
import { ApiError, unavailable } from "@/lib/errors";
import { rememberNext, takeFlash } from "@/lib/flash";
import { safeReturnPath } from "@/lib/return-path";
import { useHydrated } from "@/lib/use-hydrated";
import { login, refresh } from "@/lib/session";

export function LoginForm({
  localEnabled,
  oidcEnabled,
}: {
  localEnabled: boolean;
  oidcEnabled: boolean;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const hydrated = useHydrated();
  const next = safeReturnPath(params.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [lockedFor, setLockedFor] = useState(0);
  const passwordRef = useRef<HTMLInputElement>(null);

  // A live session never sees the login page (AC-0010-51); a dead one arrives
  // with the API's reason, carried here as a flash (AC-0010-13).
  useEffect(() => {
    // sessionStorage exists only in the browser, so the flash is read after
    // mount rather than during a render the server also performs.
    const flash = takeFlash();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (flash) setNotice(flash);
    let cancelled = false;
    refresh()
      .then(() => {
        if (!cancelled) router.replace(next);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [next, router]);

  useEffect(() => {
    if (lockedFor <= 0) return;
    const timer = window.setTimeout(() => setLockedFor((s) => s - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [lockedFor]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    setNotice(null);
    try {
      await login(email, password);
      router.replace(next);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : null;
      setError(apiError ?? unavailable());
      if (apiError?.code === "ATTEMPTS_EXCEEDED" && apiError.retryAfter) {
        setLockedFor(apiError.retryAfter);
      }
      setPassword("");
      passwordRef.current?.focus();
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <h1 className="text-2xl font-normal tracking-tight">Entrar no SIGI</h1>
        <p className="text-sm font-light text-muted-foreground">Use sua conta institucional.</p>
      </div>

      {notice && <Notice>{notice}</Notice>}

      {oidcEnabled && (
        <Button
          type="button"
          variant={localEnabled ? "outline" : "default"}
          className="w-full"
          onClick={() => {
            // A full navigation, not a client route: the API answers with a
            // redirect to the identity provider (AC-0010-06).
            rememberNext(next);
            window.location.assign(new URL("/api/v1/auth/oidc/authorize", window.location.origin));
          }}
        >
          <Building2 aria-hidden />
          Entrar com conta institucional
        </Button>
      )}

      {oidcEnabled && localEnabled && (
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          ou
          <span className="h-px flex-1 bg-border" />
        </div>
      )}

      {localEnabled && (
        <form className="space-y-4" method="post" onSubmit={onSubmit} noValidate>
          <div className="space-y-2">
            <Label htmlFor="email">E-mail institucional</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-describedby={error ? "login-error" : undefined}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Senha</Label>
            <PasswordInput
              id="password"
              name="password"
              autoComplete="current-password"
              required
              ref={passwordRef}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <ErrorNotice id="login-error" error={error} />}
          <Button type="submit" className="w-full" disabled={!hydrated || pending || lockedFor > 0}>
            {pending ? "Entrando..." : "Entrar"}
          </Button>
        </form>
      )}

      <p className="text-sm text-muted-foreground">
        Esqueceu a senha? Procure o gestor da sua unidade.
      </p>
    </div>
  );
}
