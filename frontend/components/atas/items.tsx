"use client";

import { MoreHorizontal, Plus, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { InsumoSearch } from "@/components/insumos/insumo-search";
import { TableSkeleton } from "@/components/skeleton";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { NOT_EDITABLE } from "@/lib/atas/constants";
import type { AtaDetail } from "@/lib/atas/types";
import type { ApiError } from "@/lib/errors";
import { formatBRL, formatCnpj, formatQuantity, formatUnitPrice, parseMoney, parseQuantity } from "@/lib/format";
import {
  HELP,
  ITEM_CODE_FIELD,
  ITEM_COLUMNS,
  ITEM_FIGURES,
  ITEM_ORDER,
  QUANTITY_ADITIVO_CODE_FIELD,
  QUANTITY_ADITIVO_ORDER,
  REMOVE_ORDER,
} from "@/lib/insumos/constants";
import type { Item, Items, Substitute } from "@/lib/insumos/types";
import { usePost } from "@/lib/use-post";

type Open = { kind: "add" } | { kind: "correct" | "aditivo" | "remove"; item: Item };

/**
 * The "Itens" section of the ATA page (AC-0014-21 to -27): the items as the API
 * returns them, their sum beside the ATA's value, and the gestor's add, correct,
 * remove and aditivo de quantidade. The screen formats the API's figures and
 * never multiplies (AC-0003-21).
 */
export function ItemsSection({
  ata,
  items,
  failure,
  writes,
  scoped,
  onItems,
  onAta,
  onStale,
}: {
  ata: AtaDetail;
  items: Items | null;
  failure: ApiError | null;
  writes: boolean;
  scoped: boolean;
  onItems: (items: Items, message: string) => void;
  onAta: (ata: AtaDetail, message: string) => void;
  onStale: () => void;
}) {
  const [open, setOpen] = useState<Open | null>(null);
  // Mirrors AC-0003-20, -24 and -27: items change on an ATA still running, aditivos only on a vigente one.
  const editable = writes && !NOT_EDITABLE.includes(ata.status);
  const vigente = ata.status === "vigente";

  return (
    <section aria-label="Itens" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="space-y-0.5">
          <h2 className="text-base font-normal">Itens</h2>
          {scoped && <p className="text-sm font-light text-muted-foreground">Itens dos seus grupos de materiais.</p>}
        </div>
        {editable && (
          <div className="flex flex-wrap gap-2">
            <Link href={`/atas/${ata.id}/itens/importar`} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <Upload aria-hidden />
              Importar itens
            </Link>
            <Button variant="outline" size="sm" onClick={() => setOpen({ kind: "add" })}>
              <Plus aria-hidden />
              Adicionar item
            </Button>
          </div>
        )}
      </div>

      {failure && !items && <ErrorNotice error={failure} />}
      {!items && !failure && (
        <div role="status">
          <span className="sr-only">Carregando...</span>
          <TableSkeleton rows={2} />
        </div>
      )}

      {items && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                {ITEM_COLUMNS.map((name) => (
                  <TableHead key={name} className={ITEM_FIGURES.has(name) ? "whitespace-nowrap text-right" : "whitespace-nowrap"}>
                    {name}
                  </TableHead>
                ))}
                {editable && (
                  <TableHead className="w-12">
                    <span className="sr-only">Ações</span>
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={ITEM_COLUMNS.length + (editable ? 1 : 0)} className="py-6 text-center font-light text-muted-foreground">
                    Nenhum item cadastrado.
                  </TableCell>
                </TableRow>
              )}
              {items.items.map((item) => (
                <TableRow key={item.id} data-testid="item-row" data-item-id={item.id}>
                  <TableCell className="whitespace-nowrap tabular-nums">{item.item_number ?? ""}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    <Link
                      href={`/insumos/${item.insumo.id}`}
                      className="font-mono text-xs text-primary underline-offset-4 [@media(hover:hover)_and_(pointer:fine)]:hover:underline"
                    >
                      {item.insumo.sku}
                    </Link>
                  </TableCell>
                  <TableCell className="min-w-56">{item.insumo.description}</TableCell>
                  <TableCell className="whitespace-nowrap">{item.insumo.unit}</TableCell>
                  <TableCell data-testid="item-quantity" className="whitespace-nowrap text-right tabular-nums">
                    {quantityText(item)}
                  </TableCell>
                  <TableCell data-testid="item-unit-price" className="whitespace-nowrap text-right tabular-nums">
                    {formatUnitPrice(item.unit_price)}
                  </TableCell>
                  <TableCell data-testid="item-total" className="whitespace-nowrap text-right tabular-nums">
                    {formatBRL(item.total_value)}
                  </TableCell>
                  <TableCell data-testid="item-fornecedor" className="min-w-40">
                    {item.own_fornecedor ? item.fornecedor.legal_name : ""}
                  </TableCell>
                  {editable && (
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" aria-label={`Ações para ${item.insumo.sku}`}>
                            <MoreHorizontal aria-hidden />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onSelect={() => setOpen({ kind: "correct", item })}>Corrigir</DropdownMenuItem>
                          {vigente && (
                            <DropdownMenuItem onSelect={() => setOpen({ kind: "aditivo", item })}>
                              Aditivo de quantidade
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem className="text-destructive" onSelect={() => setOpen({ kind: "remove", item })}>
                            Remover
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* A servidor sees part of the items, so their sum would differ for a reason that is no error (AC-0014-22). */}
          {!scoped && (
            <div className="space-y-2" data-testid="items-sum">
              <p className="text-sm tabular-nums">
                Soma dos itens: {formatBRL(items.items_value)} · Valor total da ATA: {formatBRL(items.total_value)}
              </p>
              {items.items_value_differs && items.items.length > 0 && (
                <p role="status" data-testid="items-differ" className="rounded-md border border-attention/30 bg-attention/10 px-3 py-2 text-sm">
                  A soma dos itens difere do valor total da ATA. Confira os itens ou o valor da ATA.
                </p>
              )}
            </div>
          )}
        </>
      )}

      {open?.kind === "add" && (
        <ItemDialog ata={ata} onClose={() => setOpen(null)} onSaved={(next) => {
            setOpen(null);
            onItems(next, "Item adicionado.");
          }} onStale={onStale} />
      )}
      {open?.kind === "correct" && (
        <ItemDialog
          key={open.item.id}
          ata={ata}
          item={open.item}
          onClose={() => setOpen(null)}
          onSaved={(next) => {
            setOpen(null);
            onItems(next, "Item corrigido.");
          }}
          onStale={onStale}
        />
      )}
      {open?.kind === "aditivo" && (
        <QuantityAditivoDialog
          ata={ata}
          item={open.item}
          onClose={() => setOpen(null)}
          onSaved={(next) => {
            setOpen(null);
            onAta(next, "Aditivo de quantidade registrado.");
          }}
          onStale={onStale}
        />
      )}
      {open?.kind === "remove" && (
        <RemoveDialog
          ata={ata}
          item={open.item}
          onClose={() => setOpen(null)}
          onSaved={(next) => {
            setOpen(null);
            onItems(next, "Item removido.");
          }}
          onStale={onStale}
        />
      )}
    </section>
  );
}

/** "120 (100 + 20)" when an aditivo raised the item, its quantity otherwise (AC-0014-21). */
function quantityText(item: Item): string {
  const contracted = formatQuantity(item.contracted_quantity);
  if (item.contracted_quantity === item.quantity || Number(item.contracted_quantity) === Number(item.quantity)) {
    return contracted;
  }
  const added = subtract(item.contracted_quantity, item.quantity);
  return `${contracted} (${formatQuantity(item.quantity)} + ${formatQuantity(added)})`;
}

/** a − b on decimal text with up to 3 places, exactly: in thousandths, as integers. */
function subtract(a: string, b: string): string {
  const thousandths = (value: string) => {
    const [whole, fraction = ""] = value.split(".");
    return BigInt(whole) * 1000n + BigInt(fraction.padEnd(3, "0").slice(0, 3));
  };
  const diff = thousandths(a) - thousandths(b);
  return `${diff / 1000n}.${(diff % 1000n).toString().padStart(3, "0")}`;
}

function ItemDialog({
  ata,
  item,
  onClose,
  onSaved,
  onStale,
}: {
  ata: AtaDetail;
  item?: Item;
  onClose: () => void;
  onSaved: (items: Items) => void;
  onStale: () => void;
}) {
  const correcting = item !== undefined;
  const initial = {
    insumo: item ? { id: item.insumo.id, sku: item.insumo.sku, description: item.insumo.description } : null,
    quantity: item ? formatQuantity(item.quantity) : "",
    unitPrice: item ? formatUnitPrice(item.unit_price).replace("R$ ", "") : "",
    itemNumber: item?.item_number ?? "",
    own: item?.own_fornecedor ?? false,
    cnpj: item?.own_fornecedor ? formatCnpj(item.fornecedor.cnpj) : "",
    legalName: item?.own_fornecedor ? item.fornecedor.legal_name : "",
  };
  const [insumo, setInsumo] = useState<Substitute | null>(initial.insumo);
  const [quantity, setQuantity] = useState(initial.quantity);
  const [unitPrice, setUnitPrice] = useState(initial.unitPrice);
  const [itemNumber, setItemNumber] = useState(initial.itemNumber);
  const [own, setOwn] = useState(initial.own);
  const [cnpj, setCnpj] = useState(initial.cnpj);
  const [legalName, setLegalName] = useState(initial.legalName);
  const post = usePost(ITEM_ORDER, ITEM_CODE_FIELD, "item");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const empty: Record<string, string> = {};
    if (!insumo) empty.insumo_id = "Campo obrigatório.";
    if (!quantity.trim()) empty.quantity = "Campo obrigatório.";
    if (!unitPrice.trim()) empty.unit_price = "Campo obrigatório.";
    if (own && !cnpj.trim()) empty["fornecedor.cnpj"] = "Campo obrigatório.";
    if (own && !legalName.trim()) empty["fornecedor.legal_name"] = "Campo obrigatório.";

    const fornecedor = own ? { cnpj: cnpj.trim(), legal_name: legalName.trim() } : null;
    const full: Record<string, unknown> = {
      insumo_id: insumo?.id,
      quantity: parseQuantity(quantity.trim()),
      unit_price: parseMoney(unitPrice.trim()),
      item_number: itemNumber.trim() || null,
      fornecedor,
    };
    let body = full;
    if (correcting) {
      // Only what changed is sent (AC-0014-24); null clears the number and returns the item to the ATA's fornecedor.
      body = {};
      if (insumo?.id !== initial.insumo?.id) body.insumo_id = full.insumo_id;
      if (quantity.trim() !== initial.quantity) body.quantity = full.quantity;
      if (unitPrice.trim() !== initial.unitPrice) body.unit_price = full.unit_price;
      if (itemNumber.trim() !== initial.itemNumber) body.item_number = full.item_number;
      if (own !== initial.own || cnpj.trim() !== initial.cnpj || legalName.trim() !== initial.legalName) {
        body.fornecedor = fornecedor;
      }
      if (Object.keys(body).length === 0 && Object.keys(empty).length === 0) {
        onClose();
        return;
      }
    } else {
      if (!full.item_number) delete body.item_number;
      if (!fornecedor) delete body.fornecedor;
    }
    const saved = await post.send<Items>(
      correcting ? `/api/v1/atas/${ata.id}/itens/${item.id}` : `/api/v1/atas/${ata.id}/itens`,
      body,
      empty,
      correcting ? "PATCH" : "POST",
    );
    if (saved) onSaved(saved);
  }

  // The refusal says the ATA is not what the page showed, so it is read again on close (AC-0014-24).
  function close() {
    if (post.failure?.code === "ATA_NAO_EDITAVEL") onStale();
    onClose();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && close()}>
      <DialogContent>
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>{correcting ? `Corrigir item ${item.insumo.sku}` : "Adicionar item"}</DialogTitle>
            <DialogDescription>
              ATA {ata.number}. {correcting ? "A correção fica no histórico da ATA." : "O item entra com a quantidade e o preço da ATA."}
            </DialogDescription>
          </DialogHeader>
          <Field id="item-insumo_id" label="Insumo" help={HELP.insumo} error={post.errors.insumo_id}>
            {(props) => (
              <InsumoSearch
                id={props.id}
                invalid={props["aria-invalid"]}
                describedBy={props["aria-describedby"]}
                value={insumo}
                onChange={setInsumo}
              />
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="item-quantity" label="Quantidade" help={HELP.quantity} error={post.errors.quantity}>
              {(props) => <Input {...props} inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} />}
            </Field>
            <Field id="item-unit_price" label="Valor unitário (R$)" help={HELP.unit_price} error={post.errors.unit_price}>
              {(props) => (
                <Input {...props} inputMode="decimal" placeholder="0,00" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} />
              )}
            </Field>
            <Field id="item-item_number" label="Nº do item (opcional)" help={HELP.item_number} error={post.errors.item_number}>
              {(props) => <Input {...props} value={itemNumber} onChange={(e) => setItemNumber(e.target.value)} />}
            </Field>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="size-4 accent-primary" checked={own} onChange={(e) => setOwn(e.target.checked)} />
            Fornecedor diferente do da ATA
          </label>
          {own && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="item-fornecedor-cnpj" label="CNPJ do fornecedor" help={HELP.cnpj} error={post.errors["fornecedor.cnpj"]}>
                {(props) => (
                  <Input
                    {...props}
                    autoCapitalize="characters"
                    placeholder="00.000.000/0000-00"
                    value={cnpj}
                    onChange={(e) => setCnpj(formatCnpj(e.target.value))}
                  />
                )}
              </Field>
              <Field id="item-fornecedor-legal_name" label="Razão social" help={HELP.legal_name} error={post.errors["fornecedor.legal_name"]}>
                {(props) => <Input {...props} value={legalName} onChange={(e) => setLegalName(e.target.value)} />}
              </Field>
            </div>
          )}
          {post.failure && <ErrorNotice error={post.failure} />}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={close}>
              Voltar
            </Button>
            <Button type="submit" disabled={post.pending}>
              {post.pending ? "Salvando..." : correcting ? "Salvar" : "Adicionar item"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function QuantityAditivoDialog({
  ata,
  item,
  onClose,
  onSaved,
  onStale,
}: {
  ata: AtaDetail;
  item: Item;
  onClose: () => void;
  onSaved: (ata: AtaDetail) => void;
  onStale: () => void;
}) {
  const [quantity, setQuantity] = useState("");
  const [justification, setJustification] = useState("");
  const post = usePost(QUANTITY_ADITIVO_ORDER, QUANTITY_ADITIVO_CODE_FIELD, "aditivo-quantidade");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const empty: Record<string, string> = {};
    if (!quantity.trim()) empty.quantity = "Campo obrigatório.";
    if (!justification.trim()) empty.justification = "Campo obrigatório.";
    const saved = await post.send<AtaDetail>(
      `/api/v1/atas/${ata.id}/aditivos`,
      { kind: "quantidade", item_id: item.id, quantity: parseQuantity(quantity.trim()), justification: justification.trim() },
      empty,
    );
    if (saved) onSaved(saved);
  }

  function close() {
    if (post.failure?.code === "ATA_NAO_VIGENTE") onStale();
    onClose();
  }

  return (
    <Dialog open onOpenChange={(next) => !next && close()}>
      <DialogContent className="max-w-md">
        <form className="grid gap-4" onSubmit={onSubmit} noValidate>
          <DialogHeader>
            <DialogTitle>Aditivo de quantidade</DialogTitle>
            <DialogDescription>
              Item {item.insumo.sku}, quantidade contratada {formatQuantity(item.contracted_quantity)} {item.insumo.unit}.
            </DialogDescription>
          </DialogHeader>
          <Field id="aditivo-quantidade-quantity" label="Quantidade acrescida" help={HELP.added_quantity} error={post.errors.quantity}>
            {(props) => <Input {...props} inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} />}
          </Field>
          <Field id="aditivo-quantidade-justification" label="Justificativa" help={HELP.justification} error={post.errors.justification}>
            {(props) => (
              <Textarea {...props} maxLength={500} value={justification} onChange={(e) => setJustification(e.target.value)} />
            )}
          </Field>
          {post.failure && <ErrorNotice error={post.failure} />}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={close}>
              Voltar
            </Button>
            <Button type="submit" disabled={post.pending}>
              {post.pending ? "Enviando..." : "Registrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RemoveDialog({
  ata,
  item,
  onClose,
  onSaved,
  onStale,
}: {
  ata: AtaDetail;
  item: Item;
  onClose: () => void;
  onSaved: (items: Items) => void;
  onStale: () => void;
}) {
  const post = usePost(REMOVE_ORDER, {}, "remover");
  function close() {
    if (post.failure?.code === "ATA_NAO_EDITAVEL") onStale();
    onClose();
  }

  return (
    <AlertDialog open onOpenChange={(next) => !next && close()}>
      <AlertDialogContent>
        <AlertDialogTitle>Remover item?</AlertDialogTitle>
        <AlertDialogDescription>
          O item {item.insumo.sku} sai da ATA {ata.number} e da soma dos itens. A remoção fica no histórico da ATA.
        </AlertDialogDescription>
        {post.failure && (
          <p role="alert" data-testid="remove-error" className="text-sm text-destructive">
            {post.failure.message}
          </p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel>Voltar</AlertDialogCancel>
          <Button
            variant="destructive"
            disabled={post.pending}
            onClick={async () => {
              const saved = await post.send<Items>(`/api/v1/atas/${ata.id}/itens/${item.id}/remover`, undefined);
              if (saved) onSaved(saved);
            }}
          >
            {post.pending ? "Removendo..." : "Remover item"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
