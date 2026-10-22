import { PATH_SEPARATOR } from "@/lib/insumos/constants";
import type { GrupoEntry, GrupoNode, GrupoRef } from "@/lib/insumos/types";

/** The tree laid flat, parents before children, in the API's order, each with its path. */
export function flatten(tree: GrupoNode[], above: GrupoRef[] = []): GrupoEntry[] {
  return tree.flatMap((grupo) => {
    const path = [...above, { id: grupo.id, name: grupo.name, level: grupo.level }];
    return [{ grupo, path }, ...flatten(grupo.children, path)];
  });
}

/** "MATERIAL ODONTOLÓGICO › RESTAURADORES" (AC-0014-02), from grupos or from their names. */
export function pathText(path: (GrupoRef | string)[]): string {
  return path.map((grupo) => (typeof grupo === "string" ? grupo : grupo.name)).join(PATH_SEPARATOR);
}

/**
 * For each grupo below a ticked one, the highest ticked grupo above it
 * (AC-0014-28). Those are already in the servidor's scope (AC-0003-29), so the
 * dialog shows them as included rather than letting them be ticked too.
 */
export function includedBy(tree: GrupoNode[], ticked: ReadonlySet<string>): Map<string, GrupoRef> {
  const included = new Map<string, GrupoRef>();
  for (const { grupo, path } of flatten(tree)) {
    const ancestor = path.slice(0, -1).find((above) => ticked.has(above.id));
    if (ancestor) included.set(grupo.id, ancestor);
  }
  return included;
}

/** What is sent: the ticked grupos, never those they include (AC-0014-28). */
export function grupoSelection(tree: GrupoNode[], ticked: ReadonlySet<string>): string[] {
  const included = includedBy(tree, ticked);
  return flatten(tree)
    .map(({ grupo }) => grupo.id)
    .filter((id) => ticked.has(id) && !included.has(id));
}
