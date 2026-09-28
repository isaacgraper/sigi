import { LayoutDashboard, type LucideIcon, Users } from "lucide-react";

import { canSeeMembers, type Me } from "@/lib/me";

export interface Module {
  href: string;
  name: string;
  /** One line for the dashboard tile (AC-0011-13). */
  description: string;
  icon: LucideIcon;
  visibleTo: (me: Me) => boolean;
}

export const DASHBOARD: Module = {
  href: "/dashboard",
  name: "Painel",
  description: "Visão geral do SIGI.",
  icon: LayoutDashboard,
  visibleTo: () => true,
};

// Business modules take their place before "Membros" as their specs are
// approved (AC-0011-01). Only what has an Approved spec behind it is listed.
// Hiding one is cosmetic; the API refuses what a perfil may not do (C5).
const MODULES: Module[] = [
  {
    href: "/members",
    name: "Membros",
    description: "Quem tem acesso ao SIGI.",
    icon: Users,
    visibleTo: (me) => canSeeMembers(me.perfil),
  },
];

/** The modules this perfil is shown, in sidebar order, without the dashboard. */
export function modulesFor(me: Me): Module[] {
  return MODULES.filter((module) => module.visibleTo(me));
}

/** Every sidebar entry: the dashboard first, then the modules. */
export function navigationFor(me: Me): Module[] {
  return [DASHBOARD, ...modulesFor(me)];
}

/** The module a path belongs to, whether or not this perfil may see it. */
export function moduleAt(pathname: string): Module | undefined {
  return [DASHBOARD, ...MODULES].find(
    (module) => pathname === module.href || pathname.startsWith(`${module.href}/`),
  );
}

export function isActive(module: Module, pathname: string): boolean {
  return pathname === module.href || pathname.startsWith(`${module.href}/`);
}
