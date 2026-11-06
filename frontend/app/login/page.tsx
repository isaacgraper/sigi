import type { Metadata } from "next";
import { headers } from "next/headers";
import { Suspense } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { DEFAULT_MECHANISMS, MECHANISMS_PATH, MECHANISMS_TIMEOUT_MS } from "@/lib/constants";
import type { Mechanisms } from "@/lib/types";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Entrar · SIGI" };
export const dynamic = "force-dynamic";

// Asked on every request, from the server: the API owns the switches its login
// routes obey, so the page cannot drift from them (AC-0010-05, OQ-33).
async function fetchMechanisms(): Promise<Mechanisms | null> {
  const origin = process.env.API_ORIGIN ?? "http://localhost:8000";
  const forwarded = (await headers()).get("x-forwarded-for");
  try {
    const response = await fetch(new URL(MECHANISMS_PATH, origin), {
      headers: forwarded ? { "x-forwarded-for": forwarded } : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(MECHANISMS_TIMEOUT_MS),
    });
    if (response.status !== 200) return null;
    const body = (await response.json()) as Partial<Mechanisms>;
    if (typeof body.local !== "boolean" || typeof body.oidc !== "boolean") return null;
    return { local: body.local, oidc: body.oidc };
  } catch {
    return null;
  }
}

export default async function LoginPage() {
  const mechanisms = await fetchMechanisms();
  const { local, oidc } = mechanisms ?? DEFAULT_MECHANISMS;
  return (
    <AuthLayout>
      <Suspense>
        <LoginForm localEnabled={local} oidcEnabled={oidc} mechanismsUnavailable={mechanisms === null} />
      </Suspense>
    </AuthLayout>
  );
}
