"use client";

import { createContext, useContext } from "react";

/**
 * Who a servidor writes to when something only a gestor can fix goes wrong
 * (AC-0010-57). Read from SUPPORT_CONTACT_EMAIL on the server at request
 * time, so each deployment names its own mailbox.
 */
const Context = createContext<string | null>(null);

export function ContactProvider({ email, children }: { email: string | null; children: React.ReactNode }) {
  return <Context.Provider value={email}>{children}</Context.Provider>;
}

export function ContactGestor({
  reference,
  testId = "contact-gestor",
}: {
  reference?: string | null;
  testId?: string;
}) {
  const email = useContext(Context);
  if (!email) {
    return (
      <p data-testid={testId} className="text-sm text-muted-foreground">
        Procure o gestor da sua unidade.
      </p>
    );
  }
  // The reference travels in the e-mail, so nobody has to copy it by hand.
  const params = new URLSearchParams({ subject: "SIGI: preciso de ajuda" });
  if (reference) params.set("body", `Código de referência: ${reference}`);
  const href = `mailto:${email}?${params.toString().replace(/\+/g, "%20")}`;
  return (
    <p data-testid={testId} className="text-sm text-muted-foreground">
      Fale com o gestor:{" "}
      <a href={href} className="font-normal text-primary underline underline-offset-4">
        {email}
      </a>
    </p>
  );
}
