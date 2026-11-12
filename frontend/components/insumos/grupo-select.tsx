"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FILTER_ALL } from "@/lib/constants";
import { flatten, pathText } from "@/lib/insumos/grupos";
import type { GrupoNode } from "@/lib/insumos/types";

/**
 * A grupo chosen from the tree, each as its path, never typed (AC-0014-08).
 * `all` adds the "Todos" choice a filter needs (AC-0014-03).
 */
export function GrupoSelect({
  tree,
  value,
  onChange,
  all,
  placeholder = "Escolha o grupo",
  ...props
}: {
  tree: GrupoNode[];
  value: string;
  onChange: (value: string) => void;
  all?: boolean;
  placeholder?: string;
  id: string;
  "aria-invalid"?: true;
  "aria-describedby"?: string;
}) {
  return (
    <Select value={value || (all ? FILTER_ALL : undefined)} onValueChange={onChange}>
      <SelectTrigger {...props} className="text-left [&>span]:truncate">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {all && <SelectItem value={FILTER_ALL}>Todos</SelectItem>}
        {flatten(tree).map(({ grupo, path }) => (
          <SelectItem key={grupo.id} value={grupo.id}>
            {pathText(path)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
