import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { CallbackHandler } from "./callback-handler";

export const metadata: Metadata = { title: "Entrando · SIGI" };

export default function CallbackPage() {
  return (
    <AuthLayout>
      <Suspense>
        <CallbackHandler />
      </Suspense>
    </AuthLayout>
  );
}
