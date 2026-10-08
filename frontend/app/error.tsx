"use client";

import Link from "next/link";

import { ContactGestor } from "@/components/contact";
import { StatusPage } from "@/components/status-page";
import { Button, buttonVariants } from "@/components/ui/button";

// AC-0010-56: a page that throws while rendering shows this instead of the
// framework's English crash screen. `digest` is the server's reference for the
// failure; it goes to the gestor inside the e-mail, not to the screen.
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <StatusPage
      illustration="error"
      title="Algo deu errado"
      description="Esta página não pôde ser exibida. Tente novamente em instantes."
    >
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button onClick={reset}>Tentar novamente</Button>
        <Link href="/dashboard" className={buttonVariants({ variant: "outline" })}>
          Ir para o painel
        </Link>
      </div>
      <ContactGestor reference={error.digest} />
    </StatusPage>
  );
}
