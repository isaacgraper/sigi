import type { Perfil } from "@/lib/types";

/** Who this is, for a screen: the name when there is one, the e-mail otherwise (C4). */
export function displayName(person: { name: string | null; email: string | null }): string {
  return person.name ?? person.email ?? "—";
}

export function canSeeMembers(perfil: Perfil): boolean {
  return perfil === "gestor" || perfil === "auditor";
}

/** The whole history is the gestor's and the auditor's (SPEC-0007 AC-0007-09). */
export function canReadHistory(perfil: Perfil): boolean {
  return perfil === "gestor" || perfil === "auditor";
}
