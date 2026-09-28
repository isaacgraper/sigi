"use client";

import { LayoutDashboard, LogOut, ShieldCheck, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { canSeeMembers, displayName, type Me, PERFIL_LABEL } from "@/lib/me";
import { cn } from "@/lib/utils";

// Only what has an Approved spec behind it (AC-0010-27).
function navigation(me: Me) {
  const items = [{ href: "/dashboard", label: "Painel", icon: LayoutDashboard }];
  if (canSeeMembers(me.perfil)) items.push({ href: "/members", label: "Membros", icon: Users });
  return items;
}

export function AppShell({
  me,
  onLogout,
  children,
}: {
  me: Me;
  onLogout: () => void;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const items = navigation(me);

  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <aside className="border-b bg-card md:w-60 md:shrink-0 md:border-b-0 md:border-r">
        <div className="flex h-14 items-center gap-2 px-4 font-semibold text-primary">
          <ShieldCheck aria-hidden className="size-5" />
          SIGI
        </div>
        <nav aria-label="Principal" className="flex gap-1 px-2 pb-2 md:flex-col md:pb-0">
          {items.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon aria-hidden className="size-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-end border-b bg-card/95 px-4 backdrop-blur">
          <DropdownMenu>
            <DropdownMenuTrigger
              className="flex items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Menu do usuário"
            >
              <span className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold uppercase text-primary">
                {displayName(me).slice(0, 1)}
              </span>
              <span className="hidden min-w-0 sm:block">
                <span data-testid="header-identity" className="block max-w-56 truncate font-medium">
                  {displayName(me)}
                </span>
                <span data-testid="header-perfil" className="block text-xs text-muted-foreground">
                  {PERFIL_LABEL[me.perfil]}
                </span>
              </span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel className="sm:hidden">
                {displayName(me)} · {PERFIL_LABEL[me.perfil]}
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="sm:hidden" />
              <DropdownMenuItem onSelect={onLogout}>
                <LogOut aria-hidden />
                Sair
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
