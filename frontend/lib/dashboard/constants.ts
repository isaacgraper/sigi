/**
 * The dashboard is the stakeholders' RELATÓRIO GERAL CAME report (SPEC-0012),
 * declared here block by block so the screen is a rendering of this file. The
 * keys of `blocks` are the block ids GET /api/v1/painel/{section} answers with
 * (§7); a block whose rows come back empty reads "Sem dados" (AC-0012-04).
 */
import { search, select } from "@/lib/dashboard/filters";
import type { Section } from "@/lib/dashboard/types";

export const ATENDIMENTO: Section = {
  id: "atendimento",
  title: "Atendimento por unidade",
  description: "O que cada unidade pediu e recebeu, por mercadoria.",
  filters: [select("Unidade"), select("ESF"), select("ESB"), search("Pesquisa de mercadorias"), select("Data")],
  blocks: {
    mercadorias: {
      kind: "table",
      title: "Mercadorias",
      columns: ["Mercadorias", "Autorizado", "Atendido", "V.T atendido"],
    },
    unidades: {
      kind: "table",
      title: "Unidades",
      columns: ["Unidade", "ESF", "ESB", "EMULTI", "EMAP", "EAPP", "EMAD Multi Prof I", "População", "Atendido"],
    },
    grafico: {
      kind: "chart",
      title: "Atendido e valor total atendido por unidade",
      series: ["Atendido", "Valor total atendido"],
    },
  },
};

export const CONSUMO: Section = {
  id: "consumo",
  title: "Consumo",
  description: "Solicitado, autorizado e atendido mês a mês.",
  filters: [select("Mercadorias"), select("Unidade")],
  blocks: {
    estoque: { kind: "stat", title: "Estoque" },
    grafico: {
      kind: "chart",
      title: "Solicitado, autorizado, atendido e média atual por mês",
      series: ["Solicitado", "Autorizado", "Atendido", "Média atual"],
    },
  },
};

export const PROCESSOS: Section = {
  id: "processos",
  title: "Processos licitatórios",
  description: "Onde está cada processo e o que ele compra.",
  filters: [select("Ano processo"), select("Objeto"), search("SKU")],
  blocks: {
    abertura: { kind: "stat", title: "Abertura" },
    novo_processo: { kind: "stat", title: "Novo processo" },
    previsao: { kind: "stat", title: "Previsão" },
    status: { kind: "stat", title: "Status" },
    nova_data: { kind: "stat", title: "Nova data projetada" },
    progresso: { kind: "stat", title: "Progresso" },
    vigente: { kind: "stat", title: "Vigente" },
    vencimento: { kind: "stat", title: "Vencimento" },
    sem_processo: { kind: "stat", title: "Previsão de tempo sem processo vigente" },
    etapas: {
      kind: "chart",
      title: "Etapas: planejado e real",
      series: [
        "Comunicado",
        "ACP",
        "SAP-ARC",
        "PGM",
        "LCT construção de edital",
        "Publicação do edital",
        "Pregão",
        "Propostas / amostras",
        "Homologação",
      ],
    },
    itens: {
      kind: "table",
      title: "Itens do processo",
      columns: ["Ano processo", "Nº item", "Item", "Objeto", "Acompanhamento"],
    },
  },
};

export const ITENS_EM_FALTA: Section = {
  id: "itens-em-falta",
  title: "Itens em falta",
  description: "O que está acabando, o que já está a caminho e o que falta comprar.",
  filters: [
    { kind: "checklist", label: "Impacto", options: ["1 - Baixo", "2 - Médio", "3 - Alto", "4 - Crítico"] },
    select("Grupo"),
    select("Aquisição"),
    select("Grupo de compras"),
    { kind: "checklist", label: "Movimento", options: ["Demanda recorrente", "Sem giro"] },
    search("SKU"),
    search("Pregão"),
    select("Comprador"),
    select("Material"),
  ],
  blocks: {
    sku: { kind: "stat", title: "SKU" },
    estoque: { kind: "stat", title: "Estoque" },
    consumo_mes: { kind: "stat", title: "Consumo mês" },
    informacoes: { kind: "note", title: "Informações extras" },
    sugestoes: { kind: "note", title: "Sugestões de troca" },
    grupos: {
      kind: "table",
      title: "Processos por grupo",
      columns: ["Grupo", "Ano", "Processo", "Data projetada", "Dias sem processo"],
    },
    curva_abc: { kind: "chart", title: "Curva ABC", series: ["A", "B", "C"] },
    disponibilidade: {
      kind: "chart",
      title: "Disponibilidade",
      series: ["Disponível", "Em falta", "Baixo estoque"],
    },
    materiais: {
      kind: "table",
      title: "Materiais",
      // Saldo and Estoque ideal are separate columns and never one figure (invariant 5).
      columns: [
        "Material",
        "Emp. abertos",
        "Dias estoque",
        "Status item",
        "Pregão",
        "SEI",
        "Validade",
        "Saldo",
        "Status do pregão",
        "Status da ATA",
        "Classif.",
        "Estoque ideal",
      ],
    },
  },
};

/** The four tabs, in the report's order (AC-0012-01). */
export const SECTIONS: Section[] = [ATENDIMENTO, CONSUMO, PROCESSOS, ITENS_EM_FALTA];
