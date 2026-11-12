"use client";

import { MEMBERS_FOR_NAMES } from "@/lib/historico/constants";
import { displayName } from "@/lib/me";
import type { MemberPage } from "@/lib/members/types";
import { useRead } from "@/lib/use-read";

/**
 * Each member's name by id, for "who" and for a reference to a member. Only a
 * gestor and an auditor read the members (SPEC-0017 §4): `enabled` false reads
 * nothing and names no one.
 */
export function useMemberNames(enabled: boolean): Record<string, string> {
  const read = useRead<MemberPage>(enabled ? `/api/v1/usuarios?page=1&size=${MEMBERS_FOR_NAMES}` : null);
  const names: Record<string, string> = {};
  for (const member of read.data?.items ?? []) names[member.id] = displayName(member);
  return names;
}
