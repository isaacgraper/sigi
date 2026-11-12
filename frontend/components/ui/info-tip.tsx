"use client";

import { Info } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * An "i" that opens a field's explanation by choice (SPEC-0013 AC-0013-19).
 *
 * A toggletip, not a hover tooltip: hover does not exist on a phone or a
 * keyboard. The text opens in the flow below the label rather than floating, so
 * it never covers the field it explains on a narrow screen.
 */
export function InfoTip({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointer(event: PointerEvent) {
      const target = event.target as Node;
      if (!button.current?.contains(target) && !panel.current?.contains(target)) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      // A dialog around the field listens for the same Escape on the document;
      // the window hears it first, so the explanation closes and the dialog stays.
      event.stopPropagation();
      setOpen(false);
      button.current?.focus();
    }
    document.addEventListener("pointerdown", onPointer);
    window.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [open]);

  return (
    <>
      <button
        ref={button}
        type="button"
        aria-label={`Sobre ${label}`}
        aria-expanded={open}
        aria-controls={id}
        data-testid="info-tip"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "inline-flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground",
          "outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
          open && "text-foreground",
        )}
      >
        <Info aria-hidden className="size-4" />
      </button>
      {/* Always in the tree, so screen readers announce it as it changes. */}
      <p
        ref={panel}
        id={id}
        role="status"
        className={cn(
          "basis-full rounded-md border bg-muted/40 px-3 py-2 text-xs font-light leading-relaxed text-foreground",
          !open && "hidden",
        )}
      >
        {open ? children : null}
      </p>
    </>
  );
}
