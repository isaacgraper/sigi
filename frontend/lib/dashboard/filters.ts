import type { Filter } from "@/lib/dashboard/types";

/** A dropdown filter. Its options come with its data source. */
export function select(label: string): Filter {
  return { kind: "select", label };
}

/** A free-text filter. */
export function search(label: string): Filter {
  return { kind: "search", label };
}
