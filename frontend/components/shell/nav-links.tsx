"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Me } from "@/lib/me";
import { isActive, navigationFor } from "@/lib/modules";
import { cn } from "@/lib/utils";

/**
 * The sidebar's entries (AC-0011-01), shared by the desktop sidebar and the
 * drawer so the two can never list different things.
 */
export function NavLinks({
  me,
  collapsed = false,
  animateLabels = false,
  onNavigate,
}: {
  me: Me;
  collapsed?: boolean;
  /** Fade the labels in, only right after the person expanded the sidebar. */
  animateLabels?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <nav aria-label="Principal" className="flex flex-col gap-1 px-2">
      {navigationFor(me).map((module) => {
        const active = isActive(module, pathname);
        const Icon = module.icon;
        return (
          <Link
            key={module.href}
            href={module.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            data-testid="nav-link"
            className={cn(
              "group relative flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-foreground",
              collapsed && "justify-center px-0",
              active
                ? "bg-sidebar-accent text-sidebar-foreground"
                : "text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground",
            )}
          >
            <Icon aria-hidden className="size-5 shrink-0" />
            {/* Collapsed, the name stays the link's accessible name (AC-0011-02). */}
            <span className={cn(collapsed ? "sr-only" : "truncate", animateLabels && "animate-label-in")}>
              {module.name}
            </span>
            {collapsed && (
              <span
                aria-hidden
                data-testid="nav-tooltip"
                className="pointer-events-none absolute left-full z-50 ml-3 whitespace-nowrap rounded-md bg-foreground px-2 py-1 text-xs font-medium text-background opacity-0 shadow-md transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100"
              >
                {module.name}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
