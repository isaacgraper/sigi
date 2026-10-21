"use client";

import { Download, FileUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ErrorNotice } from "@/components/error-notice";
import { useSession } from "@/components/session-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError, readError, unavailable } from "@/lib/errors";
import { HELP, IMPORT_ACCEPT, IMPORT_COLUMNS } from "@/lib/insumos/constants";
import { reportCounts, templateCsv } from "@/lib/insumos/template";
import type { CatalogueReport, ImportTarget, ItemsReport } from "@/lib/insumos/types";
import { apiFetch } from "@/lib/session";

type Report = CatalogueReport | ItemsReport;

/**
 * Choose a file, check it with `dry_run`, then import it (AC-0014-18 to -20).
 * The import is all or nothing (AC-0003-07), so a refused file offers only to
 * choose another, never to import the valid lines. The file goes as its bytes,
 * so a Windows-1252 file reaches the API as written (AC-0003-18).
 */
export function ImportFlow({
  target,
  path,
  done,
}: {
  target: ImportTarget;
  path: string;
  done: { href: string; label: string };
}) {
  const { handleSessionError } = useSession();
  const [file, setFile] = useState<File | null>(null);
  const [check, setCheck] = useState<Report | null>(null);
  const [result, setResult] = useState<Report | null>(null);
  const [refusal, setRefusal] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const outcome = useRef<HTMLHeadingElement>(null);
  const columns = IMPORT_COLUMNS[target];

  useEffect(() => {
    if (check || result || refusal) outcome.current?.focus();
  }, [check, result, refusal]);

  function restart() {
    setFile(null);
    setCheck(null);
    setResult(null);
    setRefusal(null);
    if (input.current) input.current.value = "";
    input.current?.focus();
  }

  async function send(dryRun: boolean) {
    if (!file) return;
    setPending(true);
    setRefusal(null);
    try {
      const response = await apiFetch(`${path}?dry_run=${dryRun}`, {
        method: "POST",
        headers: { "Content-Type": "text/csv" },
        body: file,
      });
      if (!response.ok) throw await readError(response);
      const report = (await response.json()) as Report;
      if (dryRun) setCheck(report);
      else setResult(report);
    } catch (err) {
      if (handleSessionError(err)) return;
      setCheck(null);
      setRefusal(err instanceof ApiError ? err : unavailable());
    } finally {
      setPending(false);
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([templateCsv(target)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = columns.filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (result) {
    return (
      <section aria-labelledby="import-outcome" className="space-y-4" data-testid="import-result">
        <h2 id="import-outcome" ref={outcome} tabIndex={-1} className="text-lg font-normal outline-none">
          Importação concluída
        </h2>
        <Counts report={result} />
        <Link href={done.href} className={buttonVariants()}>
          {done.label}
        </Link>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section aria-label="Colunas do arquivo" className="space-y-3 rounded-lg border bg-card p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <h2 className="text-base font-normal">Colunas do arquivo</h2>
            <p className="text-sm font-light text-muted-foreground">
              A primeira linha do arquivo traz os nomes das colunas. As obrigatórias estão marcadas.
            </p>
          </div>
          <Button type="button" variant="outline" onClick={download}>
            <Download aria-hidden />
            Baixar modelo
          </Button>
        </div>
        <ul aria-label="Colunas" className="flex flex-wrap gap-x-4 gap-y-1 text-sm" data-testid="import-columns">
          {columns.required.map((name) => (
            <li key={name}>
              <span className="font-mono text-xs">{name}</span> <span className="text-muted-foreground">(obrigatória)</span>
            </li>
          ))}
          {columns.optional.map((name) => (
            <li key={name} className="font-mono text-xs text-muted-foreground">
              {name}
            </li>
          ))}
        </ul>
      </section>

      <div className="space-y-4 rounded-lg border bg-card p-5 shadow-sm sm:p-6">
        <Field id="import-file" label="Arquivo CSV" help={HELP.file}>
          {(props) => (
            <Input
              {...props}
              ref={input}
              type="file"
              accept={IMPORT_ACCEPT}
              className="h-auto py-2"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setCheck(null);
                setRefusal(null);
              }}
            />
          )}
        </Field>
        {!check && !refusal && (
          <div className="flex justify-end">
            <Button type="button" disabled={!file || pending} onClick={() => void send(true)}>
              <FileUp aria-hidden />
              {pending ? "Conferindo..." : "Conferir arquivo"}
            </Button>
          </div>
        )}
      </div>

      {check && (
        <section aria-labelledby="import-outcome" className="space-y-4" data-testid="import-check">
          <h2 id="import-outcome" ref={outcome} tabIndex={-1} className="text-lg font-normal outline-none">
            O arquivo pode ser importado
          </h2>
          <Counts report={check} />
          {check.ignored_columns.length > 0 && (
            <div className="space-y-1 text-sm" data-testid="import-ignored">
              <p>Colunas ignoradas: {check.ignored_columns.join(", ")}</p>
              {"notes" in check &&
                check.notes.map((note) => (
                  <p key={note} className="font-light text-muted-foreground">
                    {note}
                  </p>
                ))}
            </div>
          )}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={restart}>
              Escolher outro arquivo
            </Button>
            <Button type="button" disabled={pending} onClick={() => void send(false)}>
              {pending ? "Importando..." : "Importar"}
            </Button>
          </div>
        </section>
      )}

      {refusal && (
        <section aria-labelledby="import-outcome" className="space-y-4" data-testid="import-refused">
          <h2 id="import-outcome" ref={outcome} tabIndex={-1} className="text-lg font-normal outline-none">
            O arquivo não pode ser importado
          </h2>
          <ErrorNotice error={refusal} />
          {refusal.rows.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Linha</TableHead>
                  <TableHead className="w-40">Coluna</TableHead>
                  <TableHead>Problema</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {refusal.rows.map((row, index) => (
                  <TableRow key={`${row.line}-${row.field}-${index}`} data-testid="import-row">
                    <TableCell className="tabular-nums">{row.line}</TableCell>
                    <TableCell className="font-mono text-xs">{row.field}</TableCell>
                    <TableCell>{row.message}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <div className="flex justify-end">
            <Button type="button" variant="outline" onClick={restart}>
              Escolher outro arquivo
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}

function Counts({ report }: { report: Report }) {
  return (
    <dl className="grid gap-4 rounded-lg border bg-card p-5 shadow-sm sm:grid-cols-4" data-testid="import-counts">
      {reportCounts(report).map(({ label, value }) => (
        <div key={label} className="space-y-1">
          <dt className="text-xs font-light text-muted-foreground">{label}</dt>
          <dd className="text-2xl font-normal tabular-nums">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
