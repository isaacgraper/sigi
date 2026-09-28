"use client";

import { PanelLeftClose, PanelLeftOpen, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { NavLinks } from "@/components/shell/nav-links";
import type { Me } from "@/lib/me";
import { SIDEBAR_COOKIE } from "@/lib/sidebar";
import { cn } from "@/lib/utils";

// A display preference, not a credential (C1). If the browser refuses it the
// sidebar simply starts expanded (SPEC-0011 §5).
function remember(collapsed: boolean) {
  try {
    document.cookie = collapsed
      ? `${SIDEBAR_COOKIE}=collapsed; path=/; max-age=31536000; samesite=lax`
      : `${SIDEBAR_COOKIE}=; path=/; max-age=0; samesite=lax`;
  } catch {
    // Nothing to do: the choice lasts until the page is reloaded.
  }
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={cn(
        "flex h-14 shrink-0 items-center gap-2 text-lg font-normal text-sidebar-foreground",
        compact ? "justify-center" : "px-5",
      )}
    >
      <ShieldCheck aria-hidden className="size-6 shrink-0" />
      <span className={cn(compact && "sr-only")}>SIGI</span>
    </div>
  );
}

/** The desktop sidebar, from 1024 px (AC-0011-01 to -03). */
export function Sidebar({ me, initiallyCollapsed }: { me: Me; initiallyCollapsed: boolean }) {
  const [collapsed, setCollapsed] = useState(initiallyCollapsed);
  const [expandedByHand, setExpandedByHand] = useState(false);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    setExpandedByHand(!next);
    remember(next);
  }

  return (
    <aside
      id="sidebar"
      data-testid="sidebar"
      data-collapsed={collapsed ? "true" : "false"}
      // The width snaps: it is a layout property, which DESIGN.md §7 never animates.
      className={cn(
        "sticky top-0 hidden h-dvh shrink-0 flex-col bg-sidebar lg:flex",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <Brand compact={collapsed} />
      <div className="flex-1 pt-2">
        <NavLinks me={me} collapsed={collapsed} animateLabels={expandedByHand} />
      </div>
      <div className="p-2">
        <button
          type="button"
          onClick={toggle}
          aria-controls="sidebar"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expandir menu lateral" : "Recolher menu lateral"}
          className={cn(
            "flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm text-sidebar-muted transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-foreground",
            collapsed && "justify-center px-0",
          )}
        >
          {collapsed ? (
            <PanelLeftOpen aria-hidden className="size-5" />
          ) : (
            <>
              <PanelLeftClose aria-hidden className="size-5" />
              <span aria-hidden>Recolher</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
