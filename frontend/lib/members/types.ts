import type { Perfil } from "@/lib/types";

export type Status = "pendente" | "ativo" | "bloqueado" | "desativado";

export interface Member {
  id: string;
  name: string | null;
  email: string | null;
  /** Read by a gestor or an auditor only; null before SPEC-0001 v1.7 and once deactivated. */
  registration: string | null;
  perfil: Perfil;
  status: Status;
  created_at: string;
  pseudonym: string | null;
}

export interface MemberPage {
  items: Member[];
  total: number;
  page: number;
  size: number;
}

// "unblock" has its own dialog, because it asks for a justification (AC-0010-59).
export type MemberAction = "block" | "deactivate" | "resetPassword" | "reinvite";

/** The actions that answer with a one-time link. */
export type LinkAction = "resetPassword" | "reinvite";
