import type { LucideIcon } from "lucide-react";

import type { ILLUSTRATIONS, STATUS_TONE_CLASSES } from "@/lib/constants";

export type Perfil = "gestor" | "servidor" | "auditor";

/** The signed-in usuario, as GET /api/v1/auth/me returns them. */
export interface Me {
  id: string;
  name: string | null;
  email: string | null;
  perfil: Perfil;
  status: string;
}

/** An entry of the sidebar (AC-0011-01). */
export interface Module {
  href: string;
  name: string;
  icon: LucideIcon;
  visibleTo: (me: Me) => boolean;
}

export type StatusTone = keyof typeof STATUS_TONE_CLASSES;

export type IllustrationName = keyof typeof ILLUSTRATIONS;
