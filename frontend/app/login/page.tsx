import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Entrar · SIGI" };
export const dynamic = "force-dynamic";

// Read at request time, not build time: the switches mirror the API's and
// differ per deployment (OQ-33).
function flag(name: string, fallback: boolean): boolean {
  const raw = process.env[name];
  return raw === undefined ? fallback : raw === "true";
}

export default function LoginPage() {
  return (
    <AuthLayout>
      <Suspense>
        <LoginForm
          localEnabled={flag("LOCAL_LOGIN_ENABLED", true)}
          oidcEnabled={flag("OIDC_ENABLED", false)}
        />
      </Suspense>
    </AuthLayout>
  );
}
