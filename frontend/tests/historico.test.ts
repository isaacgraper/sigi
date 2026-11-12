import { describe, expect, it } from "vitest";

import { formatDetalhe, formatMoment, formatValor, kindOf, matches } from "@/lib/historico/format";
import type { Alteracao, Evento } from "@/lib/historico/types";

// SPEC-0017: how a change's value reads on screen, by its tipo.

function change(tipo: Alteracao["tipo"], antes: Alteracao["antes"], depois: Alteracao["depois"]): Alteracao {
  return { campo: "x", rotulo: "X", tipo, antes, depois };
}

function event(alteracoes: Alteracao[]): Evento {
  return {
    entidade_tipo: "ata",
    entidade_id: "1",
    acao: "ata.editada",
    acao_rotulo: "ATA corrigida",
    usuario_id: null,
    ocorrido_em: "2026-11-10T15:00:00Z",
    justificativa: null,
    alteracoes,
    detalhes: [],
  };
}

describe("AC-0017-01 a value by its tipo", () => {
  it("writes a date dd/MM/yyyy, money in R$ and a quantity in pt-BR", () => {
    expect(formatValor("data", "2027-03-31")).toBe("31/03/2027");
    expect(formatValor("dinheiro", "105000.5")).toBe("R$ 105.000,50");
    expect(formatValor("quantidade", "1000.5")).toBe("1.000,5");
  });

  it("names a status and an etapa", () => {
    expect(formatValor("status", "vigente")).toBe("Vigente");
    expect(formatValor("status", "pre_empenho")).toBe("Pré-empenho");
    expect(formatValor("status", "em_conferencia")).toBe("Em conferência");
  });

  it("writes a flag as Sim or Não and nothing as a dash", () => {
    expect(formatValor("status", true)).toBe("Sim");
    expect(formatValor("status", false)).toBe("Não");
    expect(formatValor("texto", null)).toBe("—");
  });

  it("names a member a reference points to, when it is known", () => {
    expect(formatValor("referencia", "u1", { u1: "Ana Souza" })).toBe("Ana Souza");
    expect(formatValor("referencia", "u2", { u1: "Ana Souza" })).toBe("u2");
  });

  it("lists the quantities of the itens", () => {
    expect(formatValor("itens", [{ item_ata_id: "a", quantidade: "300" }, { item_ata_id: "b", quantidade: "2.5" }])).toBe(
      "300 · 2,5",
    );
  });

  it("writes a detail that is a date or a status as one", () => {
    expect(formatDetalhe("2026-12-31")).toBe("31/12/2026");
    expect(formatDetalhe("validacao_saldo")).toBe("Validação de saldo");
    expect(formatDetalhe("Caixa avariada.")).toBe("Caixa avariada.");
  });

  it("dates an event in São Paulo, with the time", () => {
    expect(formatMoment("2026-11-10T15:04:00Z")).toBe("10/11/2026, 12:04");
  });
});

describe("AC-0017-03 creation and removal", () => {
  it("reads a creation and a removal by what is missing", () => {
    expect(kindOf([change("texto", null, "A"), change("data", null, "2026-01-01")])).toBe("created");
    expect(kindOf([change("texto", "A", null), change("quantidade", "10", null)])).toBe("removed");
    expect(kindOf([change("status", "demanda", "validacao_saldo"), change("texto", null, "PE-1")])).toBe("changed");
  });
});

describe("AC-0017-11 only values, only statuses", () => {
  it("keeps the events that changed money or a quantity, or a status", () => {
    const valor = event([change("dinheiro", "1", "2")]);
    const status = event([change("status", "vigente", "suspensa")]);
    const texto = event([change("texto", "a", "b")]);

    expect([valor, status, texto].filter((e) => matches(e, "valor"))).toEqual([valor]);
    expect([valor, status, texto].filter((e) => matches(e, "status"))).toEqual([status]);
    expect([valor, status, texto].filter((e) => matches(e, null))).toHaveLength(3);
  });

  it("never counts a creation, which changes nothing", () => {
    const criada = event([change("status", null, "demanda"), change("texto", null, "SEI")]);

    expect(matches(criada, "status")).toBe(false);
  });
});
