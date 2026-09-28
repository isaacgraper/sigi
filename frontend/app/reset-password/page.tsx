"use client";

import { useRouter } from "next/navigation";
import { Suspense } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { TokenPasswordForm } from "@/components/auth/token-password-form";
import { setFlash } from "@/lib/flash";

// A confirmed reset returns no session (AC-0001-31): the person signs in again
// with the new password (AC-0010-25).
function ResetConfirmation() {
  const router = useRouter();
  return (
    <TokenPasswordForm
      endpoint="/api/v1/auth/redefinicoes/confirmar"
      title="Redefinir senha"
      description="Defina a nova senha da sua conta no SIGI."
      missingToken="Link de redefinição incompleto. Peça um novo ao gestor."
      finalCodes={["RESET_ALREADY_USED", "RESET_EXPIRED"]}
      submitLabel="Redefinir senha"
      onSuccess={async () => {
        setFlash("Senha redefinida. Entre com a nova senha.");
        router.replace("/login");
      }}
    />
  );
}

export default function ResetPage() {
  return (
    <AuthLayout>
      <Suspense>
        <ResetConfirmation />
      </Suspense>
    </AuthLayout>
  );
}
