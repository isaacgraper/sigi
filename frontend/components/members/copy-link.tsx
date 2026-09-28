"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

/** A one-time link, shown once, with a way to copy it (AC-0010-35, -40). */
export function CopyLink({ link }: { link: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-center gap-2">
      <code
        data-testid="one-time-link"
        className="min-w-0 flex-1 truncate rounded-md border bg-muted px-3 py-2 font-mono text-xs"
      >
        {link}
      </code>
      <Button
        type="button"
        variant="outline"
        onClick={async () => {
          await navigator.clipboard.writeText(link);
          setCopied(true);
        }}
      >
        {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
        {copied ? "Copiado" : "Copiar"}
      </Button>
    </div>
  );
}
