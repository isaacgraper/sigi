"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { remember } from "@/lib/api-cache";
import type { AtaPage } from "@/lib/atas/types";
import type { Items } from "@/lib/insumos/types";
import { formatQuantity, formatUnitPrice, parseQuantity } from "@/lib/format";
import { OPEN_CODE_FIELD, OPEN_ORDER, PROCESSO_SEI_HINT } from "@/lib/notas-empenho/constants";
import type { NotaEmpenho, SaldoItens } from "@/lib/notas-empenho/types";
import { useRead } from "@/lib/use-read";
import { usePost } from "@/lib/use-post";

/**
 * /notas-empenho/nova (AC-0015-03, -04): the ATA, the Processo SEI and how much
 * of each item. The price is the ATA's; the screen only shows it. Every rule is
 * the API's, and its refusal lands on the field it names.
 */
export function NeForm() {
  const { me } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const [ataId, setAtaId] = useState(params.get("ata") ?? "");
  const [processo, setProcesso] = useState("");
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const { errors, failure, pending, send } = usePost(OPEN_ORDER, OPEN_CODE_FIELD, "ne");

  const atas = useRead<AtaPage>("/api/v1/atas?status=vigente&size=100");
  const items = useRead<Items>(ataId ? `/api/v1/atas/${ataId}/itens` : null);
  const saldo = useRead<SaldoItens>(ataId ? `/api/v1/atas/${ataId}/itens/saldo` : null);
  const available = new Map((saldo.data?.items ?? []).map((s) => [s.item_ata_id, s.quantidade_disponivel]));

  if (me.perfil !== "gestor") {
    return (
      <div className="space-y-6">
        <PageHeader title="Abrir NE" description="Só o gestor abre uma nota de empenho." />
        <EmptyState
          message="Seu perfil não permite esta ação."
          action={
            <Link href="/notas-empenho" className={buttonVariants({ variant: "outline" })}>
              <ArrowLeft aria-hidden />
              Voltar
            </Link>
          }
        />
      </div>
    );
  }

  const lines = Object.entries(quantities)
    .filter(([, typed]) => typed.trim())
    .map(([item_ata_id, typed]) => ({ item_ata_id, quantity: parseQuantity(typed) }));

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const empty: Record<string, string> = {};
    if (!ataId) empty.ata_id = "Escolha a ATA.";
    if (!processo.trim()) empty.processo_sei = "Informe o Processo SEI.";
    if (lines.length === 0) empty.items = "Informe a quantidade de ao menos um insumo.";
    const saved = await send<NotaEmpenho>(
      "/api/v1/notas-empenho",
      { ata_id: ataId, processo_sei: processo.trim(), items: lines },
      empty,
    );
    if (saved) {
      remember(`/api/v1/notas-empenho/${saved.id}`, saved);
      router.push(`/notas-empenho/${saved.id}`);
    }
  }

  const itemsError = errors.items ?? Object.entries(errors).find(([key]) => key.startsWith("items."))?.[1];
  return (
    <div className="space-y-6">
      <PageHeader title="Abrir NE" description="A NE abre em Demanda. O saldo só é reservado no pré-empenho." />
      <form noValidate onSubmit={(e) => void submit(e)} className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="ne-ata_id" label="ATA" error={errors.ata_id} help="Só ATAs vigentes recebem novos empenhos.">
            {(props) => (
              <Select
                value={ataId}
                onValueChange={(value) => {
                  setAtaId(value);
                  setQuantities({});
                }}
              >
                <SelectTrigger {...props}>
                  <SelectValue placeholder="Escolha a ATA" />
                </SelectTrigger>
                <SelectContent>
                  {(atas.data?.items ?? []).map((ata) => (
                    <SelectItem key={ata.id} value={ata.id}>
                      {ata.number} · {ata.subject}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </Field>
          <Field id="ne-processo_sei" label="Processo SEI" error={errors.processo_sei} hint={PROCESSO_SEI_HINT}>
            {(props) => (
              <Input
                {...props}
                inputMode="numeric"
                autoComplete="off"
                value={processo}
                onChange={(e) => setProcesso(e.target.value)}
              />
            )}
          </Field>
        </div>

        {ataId && (
          <section aria-label="Itens da NE" className="space-y-2">
            <h2 className="text-base font-normal">Itens</h2>
            <p className="text-sm font-light text-muted-foreground">
              Informe a quantidade dos insumos desta NE. Deixe em branco os que não entram.
            </p>
            {items.failure && <ErrorNotice error={items.failure} />}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Insumo</TableHead>
                  <TableHead className="whitespace-nowrap text-right">Valor unitário</TableHead>
                  <TableHead className="whitespace-nowrap text-right">Disponível</TableHead>
                  <TableHead className="w-40">Quantidade</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(items.data?.items ?? []).map((item) => (
                  <TableRow key={item.id} data-testid="ne-form-item">
                    <TableCell className="min-w-56">
                      {item.insumo.description}
                      <span className="block text-xs font-light text-muted-foreground">
                        {item.insumo.sku} · {item.insumo.unit}
                      </span>
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">{formatUnitPrice(item.unit_price)}</TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">
                      {available.has(item.id) ? formatQuantity(available.get(item.id) ?? "0") : "—"}
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`Quantidade de ${item.insumo.description}`}
                        inputMode="decimal"
                        value={quantities[item.id] ?? ""}
                        onChange={(e) => setQuantities((current) => ({ ...current, [item.id]: e.target.value }))}
                      />
                    </TableCell>
                  </TableRow>
                ))}
                {items.data && items.data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-center font-light text-muted-foreground">
                      Esta ATA não tem itens.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            {itemsError && (
              <p data-testid="field-error" id="ne-items" className="text-sm text-destructive">
                {itemsError}
              </p>
            )}
          </section>
        )}

        {failure && <ErrorNotice error={failure} />}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={pending}>
            {pending ? "Enviando..." : "Abrir NE"}
          </Button>
          <Link href="/notas-empenho" className={buttonVariants({ variant: "outline" })}>
            Voltar
          </Link>
        </div>
      </form>
    </div>
  );
}

