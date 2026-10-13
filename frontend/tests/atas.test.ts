import { describe, expect, it } from "vitest";

import { daysText, MOVES } from "@/lib/atas";
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
  it("reads the renewal alert", () => {
    expect(daysText("renovacao", 12)).toBe("Vence em 12 dias");
    expect(daysText("renovacao", 1)).toBe("Vence em 1 dia");
    expect(daysText("renovacao", 0)).toBe("Vence hoje");
    expect(daysText("renovacao", -3)).toBe("Venceu há 3 dias");
  });

  it("reads the reajuste alert", () => {
    expect(daysText("reajuste", 20)).toBe("Reajuste em 20 dias");
    expect(daysText("reajuste", 0)).toBe("Reajuste hoje");
    expect(daysText("reajuste", -5)).toBe("Reajuste vencido há 5 dias");
  });
});
