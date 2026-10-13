import { SECTIONS } from "@/lib/dashboard/constants";
import type { Section } from "@/lib/dashboard/types";

/** The section a `?aba=` value names, or the first one when it names none. */
export function sectionFor(aba: string | null): Section {
  return SECTIONS.find((section) => section.id === aba) ?? SECTIONS[0];
}
