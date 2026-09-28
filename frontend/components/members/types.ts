import type { Perfil } from "@/lib/me";

export type Status = "pendente" | "ativo" | "bloqueado" | "desativado";

export interface Member {
  id: string;
  name: string | null;
  email: string | null;
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

// Green only for health; waiting is slate, attention amber (DESIGN.md §2).
export const STATUS_TONE = {
  ativo: "success",
  pendente: "neutral",
  bloqueado: "attention",
  desativado: "muted",
} as const;
