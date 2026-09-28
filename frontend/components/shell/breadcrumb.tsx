"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { DASHBOARD, moduleAt } from "@/lib/modules";

/** Where the usuario is, from "Painel" to the current page (AC-0011-07). */
export function Breadcrumb() {
  const pathname = usePathname();
  const here = moduleAt(pathname);
  const trail = here && here !== DASHBOARD ? [DASHBOARD, here] : [DASHBOARD];

  return (
    <nav aria-label="Trilha de navegação" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        {trail.map((module, index) => {
          const last = index === trail.length - 1;
          return (
            <li key={module.href} className="flex min-w-0 items-center gap-1.5">
              {index > 0 && <ChevronRight aria-hidden className="size-4 shrink-0 text-muted-foreground" />}
              {last ? (
                <span aria-current="page" className="truncate font-medium text-foreground">
                  {module.name}
                </span>
              ) : (
                <Link
                  href={module.href}
                  className="truncate rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {module.name}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
