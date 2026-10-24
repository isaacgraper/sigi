"use client";

import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { TableSkeleton } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { GRUPOS_ORDER } from "@/lib/insumos/constants";
import { flatten, grupoSelection, includedBy } from "@/lib/insumos/grupos";
import type { GrupoNode, UserGrupos } from "@/lib/insumos/types";
import { displayName } from "@/lib/me";
import type { Member } from "@/lib/members/types";
import { usePost } from "@/lib/use-post";
import { useRead } from "@/lib/use-read";

/**
 * A servidor's grupos de materiais (AC-0014-28): the tree with the current set
 * ticked, the grupos below a ticked one shown as included, and the ticked set
 * sent to replace what the servidor had (AC-0003-30).
 */
export function GruposDialog({ member, onClose }: { member: Member; onClose: () => void }) {
  const tree = useRead<GrupoNode[]>("/api/v1/grupos-materiais");
  const current = useRead<UserGrupos>(`/api/v1/usuarios/${member.id}/grupos-materiais`);
  const failure = tree.failure ?? current.failure;
  const name = displayName(member);

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grupos de materiais de {name}</DialogTitle>
          <DialogDescription>O servidor vê os insumos dos grupos marcados e dos grupos abaixo deles.</DialogDescription>
        </DialogHeader>
        {failure && <ErrorNotice error={failure} />}
        {!failure && (!tree.data || !current.data) && (
          <div role="status">
            <span className="sr-only">Carregando...</span>
            <TableSkeleton rows={3} />
          </div>
        )}
        {tree.data && current.data && (
          <Choice member={member} tree={tree.data} initial={current.data.grupo_ids} onClose={onClose} />
        )}
      </DialogContent>
    </Dialog>
  );
}

function Choice({
  member,
  tree,
  initial,
  onClose,
}: {
  member: Member;
  tree: GrupoNode[];
  initial: string[];
  onClose: () => void;
}) {
  const [ticked, setTicked] = useState<Set<string>>(() => new Set(initial));
  const [confirmingEmpty, setConfirmingEmpty] = useState(false);
  const post = usePost(GRUPOS_ORDER, {}, "grupos");
  const included = includedBy(tree, ticked);
  const entries = flatten(tree);

  function toggle(id: string, on: boolean) {
    setConfirmingEmpty(false);
    setTicked((previous) => {
      const next = new Set(previous);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  async function save() {
    const grupoIds = grupoSelection(tree, ticked);
    // With no grupo the servidor sees no insumo, so that is asked once (AC-0014-28).
    if (grupoIds.length === 0 && !confirmingEmpty) {
      setConfirmingEmpty(true);
      return;
    }
    const saved = await post.send(`/api/v1/usuarios/${member.id}/grupos-materiais`, { grupo_ids: grupoIds });
    if (saved) onClose();
  }

  return (
    <div className="grid gap-4">
      {entries.length === 0 ? (
        <p className="text-sm font-light text-muted-foreground">Nenhum grupo cadastrado.</p>
      ) : (
        <ul aria-label="Grupos de materiais" className="max-h-80 divide-y overflow-y-auto rounded-md border">
          {entries.map(({ grupo }) => {
            const by = included.get(grupo.id);
            const id = `grupo-${grupo.id}`;
            return (
              <li key={grupo.id} className="flex items-center gap-2 px-3 py-2" style={{ paddingLeft: `${0.75 + (grupo.level - 1) * 1.5}rem` }}>
                <input
                  id={id}
                  type="checkbox"
                  className="size-4 accent-primary"
                  checked={by !== undefined || ticked.has(grupo.id)}
                  disabled={by !== undefined}
                  aria-describedby={by ? `${id}-by` : undefined}
                  onChange={(e) => toggle(grupo.id, e.target.checked)}
                />
                <label htmlFor={id} className="min-w-0 text-sm">
                  {grupo.name}
                </label>
                {by && (
                  <span id={`${id}-by`} className="text-xs font-light text-muted-foreground">
                    Incluído por {by.name}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {confirmingEmpty && (
        <p role="alert" data-testid="grupos-empty" className="rounded-md border border-attention/30 bg-attention/10 px-3 py-2 text-sm">
          Sem grupos, o servidor não vê nenhum insumo. Salve de novo para confirmar.
        </p>
      )}
      {post.failure && <ErrorNotice error={post.failure} />}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          Voltar
        </Button>
        <Button type="button" disabled={post.pending} onClick={() => void save()}>
          {post.pending ? "Salvando..." : confirmingEmpty ? "Salvar sem grupos" : "Salvar grupos"}
        </Button>
      </DialogFooter>
    </div>
  );
}
