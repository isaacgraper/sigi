import Link from "next/link";

import { ContactGestor } from "@/components/contact";
import { StatusPage } from "@/components/status-page";
import { buttonVariants } from "@/components/ui/button";

// AC-0010-55: an unknown address answers 404 with a page in pt-BR.
export default function NotFound() {
  return (
    <StatusPage
      illustration="not-found"
      title="Página não encontrada"
      description="O endereço que você abriu não existe ou foi alterado."
    >
      <Link href="/dashboard" className={buttonVariants()}>
        Ir para o painel
      </Link>
      <ContactGestor />
    </StatusPage>
  );
}
