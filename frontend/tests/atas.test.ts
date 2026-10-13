import { describe, expect, it } from "vitest";

import { type AlertRow, type Ata, dueRows, dueText, MOVES } from "@/lib/atas";
import { formatBRL, formatCnpj, formatDay, parseMoney } from "@/lib/format";

describe("AC-0013-09 money typed in pt-BR", () => {
  it("is sent as decimal text", () => {
    expect(parseMoney("1.234.567,89")).toBe("1234567.89");
    expect(parseMoney("R$ 100,00")).toBe("100.00");
  });

  it("is never rounded", () => {
    expect(parseMoney("10,005")).toBe("10.005");
  });
});

describe("AC-0013-03 money shown in pt-BR", () => {
  it("groups thousands and keeps the cents", () => {
    expect(formatBRL("1234567.89")).toBe("R$ 1.234.567,89");
    expect(formatBRL("100.00")).toBe("R$ 100,00");
    expect(formatBRL("0.5")).toBe("R$ 0,50");
  });

  it("does not lose a cent on the largest NUMERIC(15,2)", () => {
    expect(formatBRL("9999999999999.99")).toBe("R$ 9.999.999.999.999,99");
  });
});

describe("AC-0013-10 a calendar date", () => {
  it("reads as typed, on any time zone", () => {
    expect(formatDay("2026-12-31")).toBe("31/12/2026");
    expect(formatDay("2026-01-01")).toBe("01/01/2026");
  });
});

describe("AC-0013-09 the CNPJ", () => {
  it("is shown formatted as it is typed", () => {
    expect(formatCnpj("11222333000181")).toBe("11.222.333/0001-81");
    expect(formatCnpj("11.222.333/0001-81")).toBe("11.222.333/0001-81");
    expect(formatCnpj("11222")).toBe("11.222");
    expect(formatCnpj("112223330001811234")).toBe("11.222.333/0001-81");
  });
});

describe("AC-0013-12 the moves offered per status", () => {
  it("mirrors AC-0002-22", () => {
    expect(MOVES.rascunho).toEqual(["ativar", "cancelar"]);
    expect(MOVES.vigente).toEqual(["suspender", "encerrar", "cancelar"]);
    expect(MOVES.suspensa).toEqual(["retomar", "encerrar", "cancelar"]);
    expect(MOVES.encerrada).toEqual([]);
    expect(MOVES.cancelada).toEqual([]);
  });
});

describe("AC-0013-02 days remaining in words", () => {
  it("counts down, then says how long ago", () => {
    expect(dueText(45)).toBe("45 dias");
    expect(dueText(1)).toBe("1 dia");
    expect(dueText(0)).toBe("hoje");
    expect(dueText(-1)).toBe("há 1 dia");
    expect(dueText(-3)).toBe("há 3 dias");
  });
});

describe("AC-0013-02 vencimentos and reajustes in one list", () => {
  const ata = (number: string): Ata =>
    ({ number, vigencia_fim: `fim-${number}`, data_reajuste: `reajuste-${number}` }) as Ata;
  const alert = (number: string, days: number): AlertRow => ({ ata: ata(number), days_remaining: days });

  it("orders both alerts by days remaining, overdue first", () => {
    const rows = dueRows([alert("012", 45), alert("014", -2)], [alert("012", 25)]);
    expect(rows.map((r) => [r.kind, r.ata.number, r.remaining])).toEqual([
      ["vencimento", "014", -2],
      ["reajuste", "012", 25],
      ["vencimento", "012", 45],
    ]);
  });

  it("dates a vencimento by its vigência and a reajuste by its reajuste date", () => {
    const [reajuste, vencimento] = dueRows([alert("012", 45)], [alert("012", 25)]);
    expect(reajuste.date).toBe("reajuste-012");
    expect(vencimento.date).toBe("fim-012");
  });
});
