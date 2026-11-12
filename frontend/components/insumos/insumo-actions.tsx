"use client";

import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { InsumoSearch } from "@/components/insumos/insumo-search";
import { Button } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";
import {
  ACTION,
  ACTION_ORDER,
  ACTIONS,
  HELP,
  SKU_CODE_FIELD,
  SKU_ORDER,
  SUBSTITUTE_CODE_FIELD,
} from "@/lib/insumos/constants";
import type { InsumoAction, InsumoDetail, Substitute } from "@/lib/insumos/types";
import { usePost } from "@/lib/use-post";

/**
 * The gestor's actions on an insumo (AC-0014-14, -15): "Alterar SKU", and the
 * situação moves its situação allows, which mirror AC-0003-14 to -16. A dialog
 * stays open on a refusal so the API's words are read.
 */
export function InsumoActions({
  insumo,
  onChanged,
}: {
  insumo: InsumoDetail;
  onChanged: (insumo: InsumoDetail, message: string) => void;
}) {
  const [open, setOpen] = useState<InsumoAction | "sku" | null>(null);
  return (
    <>
      <Button variant="outline" onClick={() => setOpen("sku")}>
        Alterar SKU
      </Button>
      {ACTIONS[insumo.status].map((action) => (
        <Button key={action} variant="outline" onClick={() => setOpen(action)}>
          {ACTION[action].label}
        </Button>
      ))}
      <SkuDialog
        insumo={insumo}
        open={open === "sku"}
        onClose={() => setOpen(null)}
        onSaved={(next) => {
          setOpen(null);
          onChanged(next, "SKU alterado.");
        }}
      />
      {open !== null && open !== "sku" && (
        <ActionDialog
          key={open}
          insumo={insumo}
          action={open}
          onClose={() => setOpen(null)}
          onSaved={(next) => {
            setOpen(null);
            onChanged(next, ACTION[open].done);
          }}
        />
      )}
    </>
  );
}

function SkuDialog({
  insumo,
  open,
  onClose,
  onSaved,
}: {
  insumo: InsumoDetail;
  open: boolean;
  onClose: () => void;
  onSaved: (insumo: InsumoDetail) => void;
}) {
  const [sku, setSku] = useState("");
  const [justification, setJustification] = useState("");
  const post = usePost(SKU_ORDER, SKU_CODE_FIELD, "sku");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await post.send<InsumoDetail>(`/api/v1/insumos/${insumo.id}/alterar-sku`, {
      sku: sku.trim(),
      justification: justification.trim(),
    });
    if (saved) onSaved(saved);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setSku("");
          setJustification("");
          post.clear();
          onClose();
        }
      }}
    >
      <DialogContent>
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>Alterar SKU</DialogTitle>
            <DialogDescription>
              SKU atual {insumo.sku}. As ATAs e notas que usam o insumo continuam ligadas a ele.
            </DialogDescription>
          </DialogHeader>
          <Field id="sku-sku" label="Novo SKU" help={HELP.new_sku} error={post.errors.sku}>
            {(props) => (
              <Input {...props} className="font-mono" autoCapitalize="characters" value={sku} onChange={(e) => setSku(e.target.value)} />
            )}
          </Field>
          <Field id="sku-justification" label="Justificativa" help={HELP.justification} error={post.errors.justification}>
            {(props) => (
              <Textarea {...props} maxLength={500} value={justification} onChange={(e) => setJustification(e.target.value)} />
            )}
          </Field>
          {post.failure && <ErrorNotice error={post.failure} />}
          <DialogFooter>
            <Button type="submit" disabled={post.pending || !sku.trim() || !justification.trim()}>
              {post.pending ? "Enviando..." : "Alterar SKU"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ActionDialog({
  insumo,
  action,
  onClose,
  onSaved,
}: {
  insumo: InsumoDetail;
  action: InsumoAction;
  onClose: () => void;
  onSaved: (insumo: InsumoDetail) => void;
}) {
  const [substitute, setSubstitute] = useState<Substitute | null>(null);
  const [justification, setJustification] = useState("");
  const post = usePost(ACTION_ORDER, SUBSTITUTE_CODE_FIELD, "acao");
  const config = ACTION[action];
  const substituting = action === "substituir";

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await post.send<InsumoDetail>(`/api/v1/insumos/${insumo.id}/${action}`, {
      justification: justification.trim(),
      ...(substituting && substitute ? { substitute_id: substitute.id } : {}),
    });
    if (saved) onSaved(saved);
  }

  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className={substituting ? undefined : "max-w-md"}>
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>{config.title}</DialogTitle>
            <DialogDescription>
              {insumo.sku}. {config.body}
            </DialogDescription>
          </DialogHeader>
          {substituting && (
            <Field id="acao-substitute_id" label="Substituto" help={HELP.substitute} error={post.errors.substitute_id}>
              {(props) => (
                <InsumoSearch
                  id={props.id}
                  invalid={props["aria-invalid"]}
                  describedBy={props["aria-describedby"]}
                  value={substitute}
                  onChange={setSubstitute}
                  exclude={insumo.id}
                />
              )}
            </Field>
          )}
          <Field id="acao-justification" label="Justificativa" help={HELP.justification} error={post.errors.justification}>
            {(props) => (
              <Textarea {...props} maxLength={500} value={justification} onChange={(e) => setJustification(e.target.value)} />
            )}
          </Field>
          {post.failure && <ErrorNotice error={post.failure} />}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Voltar
            </Button>
            <Button
              type="submit"
              variant={config.destructive ? "destructive" : "default"}
              disabled={post.pending || !justification.trim() || (substituting && !substitute)}
            >
              {post.pending ? "Enviando..." : config.label}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
