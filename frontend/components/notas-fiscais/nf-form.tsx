"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { ErrorNotice } from "@/components/error-notice";
import { PageHeader } from "@/components/page-header";
import { useSession } from "@/components/session-provider";
import { TableSkeleton } from "@/components/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { remember } from "@/lib/api-cache";
import type { Ata } from "@/lib/atas/types";
import {
  formatBRL,
  formatCnpj,
  formatQuantity,
  parseMoney,
  parseQuantity,
} from "@/lib/format";
import type { NotaEmpenho } from "@/lib/notas-empenho/types";
import {
  DATA_ANTERIOR,
  NF_CODE_FIELD,
  NF_ORDER,
} from "@/lib/notas-fiscais/constants";
import type { NotaFiscal } from "@/lib/notas-fiscais/types";
import { usePost } from "@/lib/use-post";
import { useRead } from "@/lib/use-read";

/**
 * /notas-fiscais/nova?ne= and /notas-fiscais/{id}/corrigir (AC-0016-03, -04,
 * -05, -09): the NF's header and how much of each NE item it delivers. Every
 * check is the API's; its refusal lands on the field it names.
 */
export function NfForm({ nfId }: { nfId?: string }) {
  const { me } = useSession();
  const params = useSearchParams();
  const nf = useRead<NotaFiscal>(nfId ? `/api/v1/notas-fiscais/${nfId}` : null);
  const neId = nfId ? nf.data?.nota_empenho_id : params.get("ne");
  const ne = useRead<NotaEmpenho>(neId ? `/api/v1/notas-empenho/${neId}` : null);
  const ata = useRead<Ata>(ne.data ? `/api/v1/atas/${ne.data.ata_id}` : null);
  const title = nfId ? "Corrigir NF" : "Registrar NF";
  const back = nfId ? `/notas-fiscais/${nfId}` : neId ? `/notas-empenho/${neId}` : "/notas-fiscais";

  if (me.perfil !== "gestor" && me.perfil !== "servidor") {
    return (
      <div className="space-y-6">
        <PageHeader title={title} description="Só o gestor e o servidor registram notas fiscais." />
        <EmptyState
          message="Seu perfil não permite esta ação."
          action={
            <Link href={back} className={buttonVariants({ variant: "outline" })}>
              <ArrowLeft aria-hidden />
              Voltar
            </Link>
          }
        />
      </div>
    );
  }

  if (!nfId && !neId) {
    return (
      <div className="space-y-6">
        <PageHeader title={title} description="Uma NF é registrada contra uma NE emitida." />
        <EmptyState
          message="Registre a NF a partir da página da NE emitida."
          action={
            <Link href="/notas-empenho" className={buttonVariants({ variant: "outline" })}>
              Ver notas de empenho
            </Link>
          }
        />
      </div>
    );
  }

  const failure = nf.failure ?? ne.failure ?? ata.failure;
  const ready = ne.data && ata.data && (!nfId || nf.data);
  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={
          ne.data
            ? `NE ${ne.data.number ?? "sem número"} · ATA ${ne.data.ata_number}`
            : undefined
        }
      />
      {failure ? (
        <ErrorNotice error={failure} />
      ) : ready ? (
        <NfFields ne={ne.data!} cnpj={ata.data!.fornecedor.cnpj} nf={nf.data ?? undefined} back={back} />
      ) : (
        <div role="status">
          <span className="sr-only">Carregando...</span>
          <TableSkeleton />
        </div>
      )}
    </div>
  );
}

function NfFields({
  ne,
  cnpj,
  nf,
  back,
}: {
  ne: NotaEmpenho;
  cnpj: string;
  nf?: NotaFiscal;
  back: string;
}) {
  const router = useRouter();
  const [numero, setNumero] = useState(nf?.numero ?? "");
  const [data, setData] = useState(nf?.data_emissao ?? "");
  const [valor, setValor] = useState(nf ? formatBRL(nf.valor).replace("R$ ", "") : "");
  // The NF must come from the NE's fornecedor, so it starts as theirs (AC-0016-03).
  const [fornecedorCnpj, setFornecedorCnpj] = useState(formatCnpj(cnpj));
  const [quantities, setQuantities] = useState<Record<string, string>>(
    Object.fromEntries(
      (nf?.itens ?? []).map((line) => [line.item_nota_empenho_id, formatQuantity(line.quantidade)]),
    ),
  );
  // The NE line of each sent line: the API names a line by its index in the request.
  const [sent, setSent] = useState<string[]>([]);
  const { errors, failure, pending, send } = usePost(NF_ORDER, NF_CODE_FIELD, "nf");

  const lines = ne.items
    .filter((item) => quantities[item.id]?.trim())
    .map((item) => ({
      item_nota_empenho_id: item.id,
      quantidade: parseQuantity(quantities[item.id]),
    }));

  async function submit(confirmar: boolean) {
    const empty: Record<string, string> = {};
    if (!numero.trim()) empty.numero = "Informe o número da NF.";
    if (!data) empty.data_emissao = "Informe a data de emissão.";
    if (!valor.trim()) empty.valor = "Informe o valor da NF.";
    if (!fornecedorCnpj.trim()) empty.fornecedor_cnpj = "Informe o CNPJ do fornecedor.";
    if (lines.length === 0) empty.itens = "Informe a quantidade de ao menos um item.";
    setSent(lines.map((line) => line.item_nota_empenho_id));
    const body = {
      numero: numero.trim(),
      data_emissao: data,
      valor: parseMoney(valor.trim()),
      fornecedor_cnpj: fornecedorCnpj.trim(),
      itens: lines,
      confirmar_data_anterior: confirmar,
      ...(nf ? {} : { nota_empenho_id: ne.id }),
    };
    const saved = nf
      ? await send<NotaFiscal>(`/api/v1/notas-fiscais/${nf.id}`, body, empty, "PUT")
      : await send<NotaFiscal>("/api/v1/notas-fiscais", body, empty);
    if (saved) {
      remember(`/api/v1/notas-fiscais/${saved.id}`, saved);
      router.push(`/notas-fiscais/${saved.id}`);
    }
  }

  function lineError(lineId: string): { id: string; message: string } | null {
    const index = sent.indexOf(lineId);
    if (index < 0) return null;
    const found = Object.entries(errors).find(([key]) => key.startsWith(`itens.${index}.`));
    return found ? { id: `nf-itens-${index}-quantidade`, message: found[1] } : null;
  }

  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        void submit(false);
      }}
      className="space-y-6"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="nf-numero" label="Número da NF" error={errors.numero}>
          {(props) => (
            <Input {...props} autoComplete="off" maxLength={40} value={numero} onChange={(e) => setNumero(e.target.value)} />
          )}
        </Field>
        <Field id="nf-data_emissao" label="Data de emissão" error={errors.data_emissao}>
          {(props) => <Input {...props} type="date" value={data} onChange={(e) => setData(e.target.value)} />}
        </Field>
        <Field id="nf-valor" label="Valor (R$)" error={errors.valor}>
          {(props) => (
            <Input {...props} inputMode="decimal" autoComplete="off" value={valor} onChange={(e) => setValor(e.target.value)} />
          )}
        </Field>
        <Field
          id="nf-fornecedor_cnpj"
          label="CNPJ do fornecedor"
          error={errors.fornecedor_cnpj}
          help="O CNPJ da NF precisa ser o do fornecedor da ATA."
        >
          {(props) => (
            <Input
              {...props}
              autoComplete="off"
              autoCapitalize="characters"
              value={fornecedorCnpj}
              onChange={(e) => setFornecedorCnpj(formatCnpj(e.target.value))}
            />
          )}
        </Field>
      </div>

      <section aria-label="Itens da NF" className="space-y-2">
        <h2 className="text-base font-normal">Itens</h2>
        <p className="text-sm font-light text-muted-foreground">
          Informe quanto desta NF chegou de cada item. Deixe em branco os que não vieram.
        </p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Insumo</TableHead>
              <TableHead className="whitespace-nowrap text-right">Empenhada</TableHead>
              <TableHead className="whitespace-nowrap text-right">Faltante</TableHead>
              <TableHead className="w-40">Quantidade</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ne.items.map((item) => {
              const error = lineError(item.id);
              return (
                <TableRow key={item.id} data-testid="nf-form-item">
                  <TableCell className="min-w-56">
                    {item.description}
                    <span className="block text-xs font-light text-muted-foreground">
                      {item.sku} · {item.unit}
                    </span>
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-right tabular-nums">{formatQuantity(item.quantity)}</TableCell>
                  <TableCell data-testid="nf-form-faltante" className="whitespace-nowrap text-right tabular-nums">
                    {formatQuantity(item.quantidade_faltante)}
                  </TableCell>
                  <TableCell className="align-top">
                    <Input
                      id={error?.id}
                      aria-label={`Quantidade de ${item.description}`}
                      aria-invalid={error ? true : undefined}
                      aria-describedby={error ? `${error.id}-error` : undefined}
                      inputMode="decimal"
                      value={quantities[item.id] ?? ""}
                      onChange={(e) => setQuantities((current) => ({ ...current, [item.id]: e.target.value }))}
                    />
                    {error && (
                      <p id={`${error.id}-error`} data-testid="field-error" className="mt-1 text-xs text-destructive">
                        {error.message}
                      </p>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {errors.itens && (
          <p data-testid="field-error" id="nf-itens" tabIndex={-1} className="text-sm text-destructive">
            {errors.itens}
          </p>
        )}
      </section>

      {failure?.code === DATA_ANTERIOR ? (
        <div role="alert" data-testid="nf-confirm-date" className="space-y-3 rounded-md border border-border/70 bg-card px-4 py-3">
          <p className="text-sm">{failure.message}</p>
          <Button type="button" variant="outline" disabled={pending} onClick={() => void submit(true)}>
            Confirmar data
          </Button>
        </div>
      ) : (
        failure && <ErrorNotice error={failure} />
      )}

      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? "Enviando..." : nf ? "Salvar" : "Registrar NF"}
        </Button>
        <Link href={back} className={buttonVariants({ variant: "outline" })}>
          Voltar
        </Link>
      </div>
    </form>
  );
}
