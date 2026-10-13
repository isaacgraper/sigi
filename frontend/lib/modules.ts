import { NAV_DASHBOARD, NAV_MODULES } from "@/lib/constants";
import type { Me, Module } from "@/lib/types";

/** The modules this perfil is shown, in sidebar order, without the dashboard. */
export function modulesFor(me: Me): Module[] {
  return NAV_MODULES.filter((module) => module.visibleTo(me));
}

/** Every sidebar entry: the dashboard first, then the modules. */
export function navigationFor(me: Me): Module[] {
  return [NAV_DASHBOARD, ...modulesFor(me)];
}

/** The module a path belongs to, whether or not this perfil may see it. */
export function moduleAt(pathname: string): Module | undefined {
  return [NAV_DASHBOARD, ...NAV_MODULES].find(
    (module) => pathname === module.href || pathname.startsWith(`${module.href}/`),
  );
}

export function isActive(module: Module, pathname: string): boolean {
  return pathname === module.href || pathname.startsWith(`${module.href}/`);
}
