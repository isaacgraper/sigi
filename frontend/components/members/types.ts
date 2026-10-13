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

export const STATUS_LABEL: Record<Status, string> = {
  pendente: "Pendente",
  ativo: "Ativo",
  bloqueado: "Bloqueado",
  desativado: "Desativado",
};

// Status is text (DESIGN.md §4): an account working normally needs no colour,
// a blocked one asks for attention, and waiting or gone recedes.
export const STATUS_TONE = {
  ativo: "neutral",
  pendente: "muted",
  bloqueado: "attention",
  desativado: "muted",
} as const;
