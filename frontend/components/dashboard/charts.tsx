"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartBlock } from "@/lib/dashboard";

// Categorical slots in fixed order (dataviz reference palette), validated on
// SIGI's white card: CVD ΔE 9.1 at worst, normal vision 22.9. Two slots sit
// under 3:1 against white, so every chart keeps its text legend and a table
// for assistive technology rather than letting colour carry identity.
const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"];

// Disponibilidade is a status, not a category, so it takes SIGI's status
// colours (DESIGN.md: green success, red danger, amber attention).
const STATUS: Record<string, string> = {
  Disponível: "var(--success)",
  "Em falta": "var(--danger)",
  "Baixo estoque": "var(--attention)",
};

const INK = "var(--muted-foreground)";
const GRID = "var(--border)";

const integer = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

const tooltipStyle = {
  contentStyle: { borderRadius: 8, borderColor: "var(--border)", fontSize: 12 },
  labelStyle: { color: "var(--foreground)" },
};

/** Chart rows carry raw numbers as text (SPEC-0012 §7). */
const num = (value: string | undefined) => Number(value ?? 0);

function Legend({ items }: { items: { name: string; color: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map((item) => (
        <li key={item.name} className="flex items-center gap-1.5">
          <span aria-hidden className="size-2.5 rounded-sm" style={{ background: item.color }} />
          {item.name}
        </li>
      ))}
    </ul>
  );
}

/** The figures behind a chart, for assistive technology (dataviz: a table view exists). */
function ScreenReaderTable({ block, header, rows }: { block: ChartBlock; header: string[]; rows: string[][] }) {
  return (
    <table className="sr-only">
      <caption>{block.title}</caption>
      <thead>
        <tr>
          {header.map((cell) => (
            <th key={cell} scope="col">
              {cell}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            {row.map((cell, i) => (i === 0 ? <th key={i} scope="row">{cell}</th> : <td key={i}>{cell}</td>))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Atendido is a count and the valor is money: two scales, so two panels side by
// side rather than one chart with two y-axes.
function UnidadeBars({ block, rows }: { block: ChartBlock; rows: string[][] }) {
  const data = rows.map((row) => ({ unidade: row[0], atendido: num(row[1]), valor: num(row[2]) }));
  const height = Math.max(220, data.length * 34);
  const panel = (key: "atendido" | "valor", color: string, format: (n: number) => string) => (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }} barCategoryGap={6}>
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" tickFormatter={format} tick={{ fill: INK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="unidade" width={150} tick={{ fill: INK, fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip {...tooltipStyle} isAnimationActive={false} formatter={(value) => format(Number(value))} cursor={{ fill: "var(--muted)" }} />
        <Bar dataKey={key} name={key === "atendido" ? block.series[0] : block.series[1]} fill={color} radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <figure className="min-w-0 space-y-2">
        <figcaption className="text-xs text-muted-foreground">{block.series[0]}</figcaption>
        {panel("atendido", SERIES[0], (n) => compact.format(n))}
      </figure>
      <figure className="min-w-0 space-y-2">
        <figcaption className="text-xs text-muted-foreground">{block.series[1]} (R$)</figcaption>
        {panel("valor", SERIES[1], (n) => money.format(n))}
      </figure>
      <ScreenReaderTable block={block} header={["Unidade", ...block.series]} rows={rows} />
    </div>
  );
}

function MonthLines({ block, rows }: { block: ChartBlock; rows: string[][] }) {
  const data = rows.map((row) => Object.fromEntries([["mes", row[0]], ...block.series.map((name, i) => [name, num(row[i + 1])])]));
  return (
    <div className="space-y-3">
      <Legend items={block.series.map((name, i) => ({ name, color: SERIES[i] }))} />
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ left: 8, right: 16, top: 8 }}>
          <CartesianGrid vertical={false} stroke={GRID} />
          <XAxis dataKey="mes" tick={{ fill: INK, fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tickFormatter={(n: number) => compact.format(n)} tick={{ fill: INK, fontSize: 11 }} axisLine={false} tickLine={false} width={56} />
          <Tooltip {...tooltipStyle} isAnimationActive={false} formatter={(value) => integer.format(Number(value))} />
          {block.series.map((name, i) => (
            <Line key={name} type="monotone" dataKey={name} stroke={SERIES[i]} strokeWidth={2} dot={i === 1 ? { r: 3 } : false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <ScreenReaderTable block={block} header={["Mês", ...block.series]} rows={rows} />
    </div>
  );
}

// The report stacks nine coloured stages on two bars; nine hues is past what a
// categorical palette can keep apart, so each stage is a row instead, with its
// planned and real days side by side.
function StageBars({ block, rows }: { block: ChartBlock; rows: string[][] }) {
  const data = rows.map((row) => ({ etapa: row[0], planejado: num(row[1]), real: num(row[2]) }));
  const total = (key: "planejado" | "real") => data.reduce((sum, row) => sum + row[key], 0);
  return (
    <div className="space-y-3">
      <Legend
        items={[
          { name: `Planejado (${integer.format(total("planejado"))} dias)`, color: SERIES[0] },
          { name: `Real (${integer.format(total("real"))} dias)`, color: SERIES[1] },
        ]}
      />
      <ResponsiveContainer width="100%" height={Math.max(260, data.length * 40)}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }} barGap={2} barCategoryGap={8}>
          <CartesianGrid horizontal={false} stroke={GRID} />
          <XAxis type="number" unit=" d" tick={{ fill: INK, fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="etapa" width={170} tick={{ fill: INK, fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip {...tooltipStyle} isAnimationActive={false} formatter={(value) => `${integer.format(Number(value))} dias`} cursor={{ fill: "var(--muted)" }} />
          <Bar dataKey="planejado" name="Planejado" fill={SERIES[0]} radius={[0, 4, 4, 0]} maxBarSize={12} isAnimationActive={false} />
          <Bar dataKey="real" name="Real" fill={SERIES[1]} radius={[0, 4, 4, 0]} maxBarSize={12} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
      <ScreenReaderTable block={block} header={["Etapa", "Planejado (dias)", "Real (dias)"]} rows={rows} />
    </div>
  );
}

// Its labels list every share in text, which doubles as the table view.
function PartOfWhole({ rows }: { rows: string[][] }) {
  const data = rows.map((row, i) => ({ name: row[0], value: num(row[1]), color: STATUS[row[0]] ?? SERIES[i % SERIES.length] }));
  const sum = data.reduce((total, row) => total + row.value, 0) || 1;
  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" stroke="var(--card)" strokeWidth={2} isAnimationActive={false}>
            {data.map((row) => (
              <Cell key={row.name} fill={row.color} />
            ))}
          </Pie>
          <Tooltip {...tooltipStyle} isAnimationActive={false} formatter={(value) => `${percent.format((Number(value) / sum) * 100)}%`} />
        </PieChart>
      </ResponsiveContainer>
      {/* Direct labels with the share, so no slice depends on its colour. */}
      <ul className="space-y-1 text-sm">
        {data.map((row) => (
          <li key={row.name} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <span aria-hidden className="size-2.5 rounded-sm" style={{ background: row.color }} />
              {row.name}
            </span>
            <span className="tabular-nums text-muted-foreground">{percent.format((row.value / sum) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** A chart block with data, in the form the registry names (SPEC-0012 AC-0012-13). */
export function DashChart({ block, rows }: { block: ChartBlock; rows: string[][] }) {
  switch (block.chart) {
    case "bar":
      return <UnidadeBars block={block} rows={rows} />;
    case "line":
      return <MonthLines block={block} rows={rows} />;
    case "stages":
      return <StageBars block={block} rows={rows} />;
    case "pie":
      return <PartOfWhole rows={rows} />;
  }
}
