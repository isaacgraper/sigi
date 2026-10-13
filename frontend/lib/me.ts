import type { Perfil } from "@/lib/types";

/** Who this is, for a screen: the name when there is one, the e-mail otherwise (C4). */
export function displayName(person: { name: string | null; email: string | null }): string {
  return person.name ?? person.email ?? "—";
}

export function canSeeMembers(perfil: Perfil): boolean {
  return perfil === "gestor" || perfil === "auditor";
}
