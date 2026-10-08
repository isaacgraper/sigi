"use client";

import { Check, Copy } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";

// Browsers expose navigator.clipboard only over HTTPS or on localhost. An
// install opened by its network address over plain http gets the older
// execCommand path, and if that fails too the link is selected for the person
// to copy (AC-0010-58).
function copyWithFallback(text: string): boolean {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}

/** A one-time link, shown once, with a way to copy it (AC-0010-35, -40). */
export function CopyLink({ link }: { link: string }) {
  const [state, setState] = useState<"idle" | "copied" | "manual">("idle");
  const codeRef = useRef<HTMLElement>(null);

  async function copy() {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(link);
        setState("copied");
        return;
      }
    } catch {
      // Denied or unavailable: fall through to the fallback.
    }
    if (copyWithFallback(link)) {
      setState("copied");
      return;
    }
    const selection = window.getSelection();
    if (codeRef.current && selection) {
      const range = document.createRange();
      range.selectNodeContents(codeRef.current);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    setState("manual");
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <code
          ref={codeRef}
          data-testid="one-time-link"
          className="min-w-0 flex-1 select-all truncate rounded-md border bg-muted px-3 py-2 font-mono text-xs"
        >
          {link}
        </code>
        <Button type="button" variant="outline" onClick={copy}>
          {state === "copied" ? <Check aria-hidden /> : <Copy aria-hidden />}
          {state === "copied" ? "Copiado" : "Copiar"}
        </Button>
      </div>
      {state === "manual" && (
        <p role="status" className="text-sm text-muted-foreground">
          Selecione o link e copie com Ctrl+C.
        </p>
      )}
    </div>
  );
}
