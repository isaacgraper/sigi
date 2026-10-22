import { describe, expect, it } from "vitest";

import { formatQuantity, formatUnitPrice, parseMoney, parseQuantity } from "@/lib/format";
import { ACTIONS, IMPORT_COLUMNS } from "@/lib/insumos/constants";
import { flatten, grupoSelection, includedBy, pathText } from "@/lib/insumos/grupos";
import { reportCounts, templateCsv } from "@/lib/insumos/template";
import type { GrupoNode } from "@/lib/insumos/types";

function node(id: string, level: number, children: GrupoNode[] = [], parent: string | null = null): GrupoNode {
  return { id, name: id.toUpperCase(), level, parent_id: parent, children };
}

// MATERIAL ODONTOLÓGICO › RESTAURADORES › RESINAS, and MATERIAL DE EXPEDIENTE.
const tree: GrupoNode[] = [
  node("odonto", 1, [node("restauradores", 2, [node("resinas", 3, [], "restauradores")], "odonto")]),
  node("expediente", 1),
];

describe("AC-0014-11 quantities and unit prices typed in pt-BR", () => {
  it("are sent as decimal text", () => {
    expect(parseQuantity("1.000")).toBe("1000");
    expect(parseQuantity("2,5")).toBe("2.5");
    expect(parseMoney("0,00599")).toBe("0.00599");
  });

  it("are never rounded", () => {
    expect(parseMoney("1,23456789")).toBe("1.23456789");
  });
});

describe("AC-0014-21 figures shown in pt-BR", () => {
  it("a quantity drops trailing zeros and groups thousands", () => {
    expect(formatQuantity("1000.000")).toBe("1.000");
    expect(formatQuantity("2.500")).toBe("2,5");
    expect(formatQuantity("120")).toBe("120");
  });

  it("a unit price keeps from 2 to 5 decimals", () => {
    expect(formatUnitPrice("0.00599")).toBe("R$ 0,00599");
    expect(formatUnitPrice("1.50000")).toBe("R$ 1,50");
    expect(formatUnitPrice("1234.10000")).toBe("R$ 1.234,10");
  });
});

describe("AC-0014-02 the grupo path", () => {
  it("reads from the root down", () => {
    const resinas = flatten(tree).find(({ grupo }) => grupo.id === "resinas");
    expect(pathText(resinas!.path)).toBe("ODONTO › RESTAURADORES › RESINAS");
  });

  it("lays the tree flat, parents first, in the API's order", () => {
    expect(flatten(tree).map(({ grupo }) => grupo.id)).toEqual(["odonto", "restauradores", "resinas", "expediente"]);
  });
});

describe("AC-0014-28 a servidor's grupos", () => {
  it("shows what a ticked grupo includes, by the highest ticked one", () => {
    const included = includedBy(tree, new Set(["odonto", "restauradores"]));
    expect(included.get("restauradores")?.id).toBe("odonto");
    expect(included.get("resinas")?.id).toBe("odonto");
    expect(included.has("odonto")).toBe(false);
    expect(included.has("expediente")).toBe(false);
  });

  it("sends the ticked grupos, never those they include", () => {
    expect(grupoSelection(tree, new Set(["odonto", "resinas", "expediente"]))).toEqual(["odonto", "expediente"]);
    expect(grupoSelection(tree, new Set())).toEqual([]);
  });
});

describe("AC-0014-15 the actions offered per situação", () => {
  it("mirror AC-0003-14 to -16", () => {
    expect(ACTIONS.ativo).toEqual(["descontinuar", "substituir"]);
    expect(ACTIONS.descontinuado).toEqual(["reativar"]);
    expect(ACTIONS.substituido).toEqual(["reativar"]);
  });
});

describe("AC-0014-18, -20 the model files", () => {
  it("carry the columns of AC-0003-06 and -26, separated by ;", () => {
    expect(templateCsv("catalogue")).toBe(
      "sku;descricao;unidade;grupo;subgrupo;classificacao;codigo_doms;codigo_externo;quantidade_referencia\r\n",
    );
    expect(templateCsv("items")).toBe(
      "sku;quantidade;valor_unitario;numero_item;cnpj_fornecedor;razao_social_fornecedor\r\n",
    );
    expect(IMPORT_COLUMNS.items.required).toEqual(["sku", "quantidade", "valor_unitario"]);
  });
});

describe("AC-0014-19 the report's counts", () => {
  it("are worded for a check and for the import done", () => {
    const check = reportCounts({
      lines: [],
      created: 2,
      updated: 1,
      unchanged: 0,
      corrected_descriptions: 1,
      ignored_columns: [],
      notes: [],
      dry_run: true,
    });
    expect(check[0]).toEqual({ label: "Serão criados", value: 2 });
    const done = reportCounts({ lines: [], added: 3, corrected: 0, unchanged: 1, ignored_columns: [], dry_run: false });
    expect(done.map((count) => count.label)).toEqual(["Adicionados", "Corrigidos", "Sem alteração"]);
  });
});
