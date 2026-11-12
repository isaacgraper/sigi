/** What the Membros screens read (SPEC-0010). Shared values live in lib/constants.ts. */
import type { LinkAction, MemberAction, Status } from "@/lib/members/types";
import type { StatusTone } from "@/lib/types";

// ── List ────────────────────────────────────────────────────────────────────

export const MEMBERS_PAGE_SIZE = 20;

export const STATUS_LABEL: Record<Status, string> = {
  pendente: "Pendente",
  ativo: "Ativo",
  bloqueado: "Bloqueado",
  desativado: "Desativado",
};

// Status is text (DESIGN.md §4): an account working normally needs no colour,
// a blocked one asks for attention, and waiting or gone recedes.
export const STATUS_TONE: Record<Status, StatusTone> = {
  ativo: "neutral",
  pendente: "muted",
  bloqueado: "attention",
  desativado: "muted",
};

// ── Invitation ──────────────────────────────────────────────────────────────

/** The refusals the invitation dialog shows beside a field; anything else is a notice. */
export const INVITE_FIELDS = ["email", "name", "registration"] as const;

// ── Actions on a member ─────────────────────────────────────────────────────

// The API's route segments (SPEC-0001 §7), kept in one place.
export const ACTION_ENDPOINT: Record<MemberAction, string> = {
  block: "bloquear",
  deactivate: "desativar",
  resetPassword: "redefinir-senha",
  reinvite: "reemitir-convite",
};

export const ACTION_CONFIRM: Record<
  MemberAction,
  { title: string; body: string; label: string; destructive: boolean }
> = {
  block: {
    title: "Bloquear membro?",
    body: "As sessões abertas desta pessoa são encerradas e ela não consegue mais entrar.",
    label: "Bloquear",
    destructive: true,
  },
  deactivate: {
    title: "Desativar membro?",
    body: "Nome e e-mail serão apagados e esta ação não pode ser desfeita. O histórico do que a pessoa fez é mantido.",
    label: "Desativar",
    destructive: true,
  },
  resetPassword: {
    title: "Redefinir senha?",
    body: "Um link de redefinição será gerado para você entregar à pessoa.",
    label: "Gerar link",
    destructive: false,
  },
  reinvite: {
    title: "Gerar novo convite?",
    body: "Um novo link de ativação será gerado para você entregar à pessoa. O link anterior deixa de funcionar.",
    label: "Gerar link",
    destructive: false,
  },
};

// A one-time link is shown once and never again (AC-0010-40, -61).
export const LINK_DIALOG: Record<LinkAction, { title: string; description: string }> = {
  resetPassword: {
    title: "Link de redefinição",
    description: "Este link não será mostrado de novo e expira em 1 hora.",
  },
  reinvite: {
    title: "Novo link de convite",
    description: "Este link não será mostrado de novo. O link anterior deixa de funcionar.",
  },
};
