"use client";

import { LogOut } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { displayName, type Me, PERFIL_LABEL } from "@/lib/me";

/** Who is signed in, and the way out (AC-0011-08). */
export function UserMenu({ me, onLogout }: { me: Me; onLogout: () => void }) {
  const name = displayName(me);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex min-w-0 items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label="Menu do usuário"
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold uppercase text-primary-foreground">
          {name.slice(0, 1)}
        </span>
        <span className="hidden min-w-0 sm:block">
          <span data-testid="header-identity" className="block max-w-56 truncate font-medium">
            {name}
          </span>
          <span data-testid="header-perfil" className="block text-xs text-muted-foreground">
            {PERFIL_LABEL[me.perfil]}
          </span>
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel data-testid="menu-identity" className="font-normal">
          <span className="block truncate text-sm font-medium text-foreground">{name}</span>
          <span className="block">{PERFIL_LABEL[me.perfil]}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onLogout}>
          <LogOut aria-hidden />
          Sair
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
