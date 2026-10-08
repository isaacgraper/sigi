"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Menu, X } from "lucide-react";
import { useState } from "react";

import { NavLinks } from "@/components/shell/nav-links";
import { Brand } from "@/components/shell/sidebar";
import type { Me } from "@/lib/me";

/**
 * Below 1024 px the sidebar is a drawer (AC-0011-04 to -06). The dialog
 * primitive traps focus, closes on Escape and on the backdrop, and hands focus
 * back to the menu button; following an entry closes it by hand.
 */
export function MobileNav({ me }: { me: Me }) {
  const [open, setOpen] = useState(false);
  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Trigger
        className="-ml-2 flex size-10 items-center justify-center rounded-md text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
        aria-label="Abrir menu"
      >
        <Menu aria-hidden className="size-5" />
      </DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          data-testid="drawer-backdrop"
          className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-overlay-in data-[state=closed]:animate-overlay-out lg:hidden"
        />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          data-testid="drawer"
          className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col bg-sidebar shadow-xl data-[state=open]:animate-drawer-in data-[state=closed]:animate-drawer-out lg:hidden"
        >
          <DialogPrimitive.Title className="sr-only">Menu</DialogPrimitive.Title>
          <div className="flex items-center justify-between pr-2">
            <Brand />
            <DialogPrimitive.Close
              aria-label="Fechar menu"
              className="flex size-10 items-center justify-center rounded-md text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-foreground"
            >
              <X aria-hidden className="size-5" />
            </DialogPrimitive.Close>
          </div>
          <div className="pt-2">
            <NavLinks me={me} onNavigate={() => setOpen(false)} />
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
