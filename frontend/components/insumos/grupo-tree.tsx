"use client";

import { Pencil, Plus, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { GRUPO_CODE_FIELD, GRUPO_MAX_LEVEL, GRUPO_ORDER, HELP } from "@/lib/insumos/constants";
import { flatten } from "@/lib/insumos/grupos";
import type { GrupoNode } from "@/lib/insumos/types";
import { usePost } from "@/lib/use-post";
import { cn } from "@/lib/utils";

type Editing = { kind: "create"; parent: GrupoNode | null } | { kind: "rename"; grupo: GrupoNode };

/**
 * The three levels, each grupo under its parent (AC-0014-16), and the gestor's
 * create and rename (AC-0014-17). No fourth level is offered, mirroring
 * AC-0003-09; the API refuses one.
 */
export function GrupoTree({
  tree,
  manages,
  onChanged,
}: {
  tree: GrupoNode[];
  manages: boolean;
  onChanged: (message: string) => void;
}) {
  const [editing, setEditing] = useState<Editing | null>(null);
  const entries = flatten(tree);

  return (
    <div className="space-y-4">
      {manages && (
        <div className="flex justify-end">
          <Button onClick={() => setEditing({ kind: "create", parent: null })}>
            <Plus aria-hidden />
            Novo grupo
          </Button>
        </div>
      )}

      {entries.length === 0 ? (
        <div className="rounded-lg border bg-card">
          <EmptyState
            message="Nenhum grupo cadastrado."
            action={
              manages ? (
                <Link href="/insumos/importar" className={buttonVariants({ variant: "outline" })}>
                  <Upload aria-hidden />
                  Importar catálogo
                </Link>
              ) : undefined
            }
          />
        </div>
      ) : (
        <ul aria-label="Grupos de materiais" className="divide-y rounded-lg border bg-card shadow-sm">
          {entries.map(({ grupo }) => (
            <li
              key={grupo.id}
              data-testid="grupo-row"
              data-level={grupo.level}
              className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5"
            >
              <span
                className={cn("min-w-0 text-sm", grupo.level > 1 && "text-muted-foreground")}
                style={{ paddingLeft: `${(grupo.level - 1) * 1.5}rem` }}
              >
                {grupo.name}
              </span>
              {manages && (
                <span className="flex gap-1">
                  {grupo.level < GRUPO_MAX_LEVEL && (
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Adicionar subgrupo em ${grupo.name}`}
                      onClick={() => setEditing({ kind: "create", parent: grupo })}
                    >
                      <Plus aria-hidden />
                      <span className="hidden sm:inline">Adicionar subgrupo</span>
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Renomear ${grupo.name}`}
                    onClick={() => setEditing({ kind: "rename", grupo })}
                  >
                    <Pencil aria-hidden />
                    <span className="hidden sm:inline">Renomear</span>
                  </Button>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {editing && (
        <GrupoDialog
          key={editing.kind === "rename" ? editing.grupo.id : (editing.parent?.id ?? "raiz")}
          editing={editing}
          onClose={() => setEditing(null)}
          onSaved={(message) => {
            setEditing(null);
            onChanged(message);
          }}
        />
      )}
    </div>
  );
}

function GrupoDialog({
  editing,
  onClose,
  onSaved,
}: {
  editing: Editing;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const renaming = editing.kind === "rename";
  const [name, setName] = useState(renaming ? editing.grupo.name : "");
  const post = usePost(GRUPO_ORDER, GRUPO_CODE_FIELD, "grupo");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const empty: Record<string, string> = name.trim() ? {} : { name: "Campo obrigatório." };
    const saved = renaming
      ? await post.send(`/api/v1/grupos-materiais/${editing.grupo.id}`, { name: name.trim() }, empty, "PATCH")
      : await post.send(
          "/api/v1/grupos-materiais",
          { name: name.trim(), parent_id: editing.parent?.id ?? null },
          empty,
        );
    if (saved) onSaved(renaming ? "Grupo renomeado." : "Grupo criado.");
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-md">
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>{renaming ? "Renomear grupo" : editing.parent ? "Adicionar subgrupo" : "Novo grupo"}</DialogTitle>
            <DialogDescription>
              {renaming
                ? "Os insumos do grupo continuam nele."
                : editing.parent
                  ? `Abaixo de ${editing.parent.name}.`
                  : "Um grupo de primeiro nível, como no DOMS."}
            </DialogDescription>
          </DialogHeader>
          <Field id="grupo-name" label="Nome" help={HELP.grupo_name} error={post.errors.name}>
            {(props) => <Input {...props} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />}
          </Field>
          {post.failure && <ErrorNotice error={post.failure} />}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Voltar
            </Button>
            <Button type="submit" disabled={post.pending}>
              {post.pending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
