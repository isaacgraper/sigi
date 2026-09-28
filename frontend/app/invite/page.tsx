"use client";

import { useRouter } from "next/navigation";
import { Suspense } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { TokenPasswordForm } from "@/components/auth/token-password-form";
import { HOME } from "@/lib/return-path";
import { adopt } from "@/lib/session";

// Activation opens a session: activation and first login are one step
// (AC-0001-11, AC-0010-19).
function Activation() {
  const router = useRouter();
  return (
    <TokenPasswordForm
      endpoint="/api/v1/convites/ativar"
      title="Ativar acesso"
      description="Defina a senha da sua conta no SIGI."
      missingToken="Link de convite incompleto. Peça um novo ao gestor."
      finalCodes={["INVITE_ALREADY_USED", "INVITE_EXPIRED"]}
      submitLabel="Ativar conta"
      onSuccess={async (response) => {
        await adopt(response);
        router.replace(HOME);
      }}
    />
  );
}

export default function InvitationPage() {
  return (
    <AuthLayout>
      <Suspense>
        <Activation />
      </Suspense>
    </AuthLayout>
  );
}
