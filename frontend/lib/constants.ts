/**
 * Values the whole application shares (docs/process/coding-standards.md §2).
 * A value one feature owns lives in lib/<feature>/constants.ts instead.
 */
import { FileText, LayoutDashboard, Users } from "lucide-react";

import { canSeeMembers } from "@/lib/me";
import type { Module, Perfil } from "@/lib/types";

// ── Navigation ──────────────────────────────────────────────────────────────

/** Where a session lands, and where an unsafe return path falls back to (AC-0010-16, -52). */
export const HOME_PATH = "/dashboard";

export const NAV_DASHBOARD: Module = {
  href: HOME_PATH,
  name: "Painel",
  icon: LayoutDashboard,
  visibleTo: () => true,
};

// Business modules take their place before "Membros" as their specs are
// approved (AC-0011-01). Only what has an Approved spec behind it is listed.
// Hiding one is cosmetic; the API refuses what a perfil may not do (C5).
export const NAV_MODULES: Module[] = [
  {
    href: "/atas",
    name: "ATAs",
    icon: FileText,
    // Every perfil reads ATAs (AC-0002-23, AC-0013-01); only a gestor writes.
    visibleTo: () => true,
  },
  {
    href: "/members",
    name: "Membros",
    icon: Users,
    visibleTo: (me) => canSeeMembers(me.perfil),
  },
];

// ── Perfis ──────────────────────────────────────────────────────────────────

export const PERFIL_LABEL: Record<Perfil, string> = {
  gestor: "Gestor",
  servidor: "Servidor",
  auditor: "Auditor",
};

// ── Session, storage and cookies ────────────────────────────────────────────

// sessionStorage holds a sentence or a path, never a token (C1).
export const FLASH_STORAGE_KEY = "sigi.flash";
export const NEXT_STORAGE_KEY = "sigi.next";

/** The Web Lock that keeps two tabs from spending one refresh cookie (AC-0010-47). */
export const REFRESH_LOCK_NAME = "sigi-refresh";

// Read by the server layout too, so it lives in a module with no "use client"
// (AC-0011-03): imported from a client module it would arrive as a reference.
export const SIDEBAR_COOKIE = "sigi_sidebar";

/** Codes after which no retry can help: the refresh is spent, or the account stopped being active (AC-0010-13). */
export const SESSION_OVER_CODES = new Set(["INVALID_REFRESH", "USUARIO_INATIVO"]);

// ── Messages ────────────────────────────────────────────────────────────────

/** The one text the screen owns when the API gives none: a 5xx or no answer (AC-0010-42). */
export const GENERIC_FAILURE = "Não foi possível concluir. Tente novamente em instantes.";

export const PASSWORD_MISMATCH = "As senhas não conferem.";

export const OIDC_CANCELLED = "A entrada institucional foi cancelada ou não foi autorizada. Tente novamente.";

// Failures the servidor cannot fix alone (AC-0010-57). Validation errors and a
// wrong password stay without a contact: the person can fix those.
export const NEEDS_GESTOR_CODES = new Set([
  "UNAVAILABLE",
  "USUARIO_INATIVO",
  "PERFIL_NAO_AUTORIZADO",
  "USUARIO_NAO_PROVISIONADO",
  "INVITE_EXPIRED",
  "INVITE_ALREADY_USED",
  "RESET_EXPIRED",
  "RESET_ALREADY_USED",
  "MISSING_TOKEN",
]);

// ── API proxy ───────────────────────────────────────────────────────────────

// Hop-by-hop headers, and the ones `fetch` recomputes after decoding the body.
export const PROXY_DROPPED_HEADERS = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "host",
  "keep-alive",
  "transfer-encoding",
]);

// ── Build ───────────────────────────────────────────────────────────────────

// Inlined at build time from package.json (next.config.ts), so the footer names
// the version this bundle was built from (AC-0011-10).
export const APP_VERSION = process.env.NEXT_PUBLIC_SIGI_VERSION ?? "dev";

// ── Presentation ────────────────────────────────────────────────────────────

// Intrinsic sizes from each file's viewBox, so the space is reserved before
// the file arrives and nothing shifts.
export const ILLUSTRATIONS = {
  login: { src: "/illustrations/login.svg", width: 918, height: 766 },
  "not-found": { src: "/illustrations/not-found.svg", width: 1097, height: 811 },
  error: { src: "/illustrations/error.svg", width: 663, height: 762 },
  empty: { src: "/illustrations/empty.svg", width: 820, height: 781 },
} as const;

/**
 * A status as text, never a pill (DESIGN.md §4): the word carries the meaning,
 * a dot marks only what needs attention, finished states recede.
 */
export const STATUS_TONE_CLASSES = {
  neutral: { text: "text-foreground", dot: null },
  attention: { text: "text-foreground", dot: "bg-attention" },
  danger: { text: "text-foreground", dot: "bg-danger" },
  muted: { text: "text-muted-foreground", dot: null },
} as const;
