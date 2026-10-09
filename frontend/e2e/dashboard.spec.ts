import { expect, type Page, test } from "@playwright/test";

import { GESTOR, member, signIn } from "./helpers";

// SPEC-0012: the dashboard is the stakeholders' RELATÓRIO GERAL CAME report.
// SIGI holds none of its data yet, so every block reads "Sem dados".

const TABS = ["Atendimento por unidade", "Consumo", "Processos licitatórios", "Itens em falta"];

const panel = (page: Page) => page.getByRole("tabpanel");

async function open(page: Page, name: string) {
  await page.getByRole("tab", { name }).click();
  await expect(page.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
}

/** Every block of the open section keeps its title and reads "Sem dados" (AC-0012-04). */
async function everyBlockEmpty(page: Page, count: number) {
  const blocks = panel(page).getByTestId("dashboard-block");
  await expect(blocks).toHaveCount(count);
  for (const block of await blocks.all()) {
    await expect(block.getByTestId("sem-dados")).toHaveText("Sem dados");
  }
}

async function headings(page: Page, names: string[]) {
  for (const name of names) {
    await expect(panel(page).getByRole("heading", { name, exact: true })).toBeVisible();
  }
}

async function columns(page: Page, table: string, names: string[]) {
  const block = panel(page).getByTestId("dashboard-block").filter({ has: page.getByRole("heading", { name: table, exact: true }) });
  await expect(block.getByRole("columnheader")).toHaveText(names);
}

async function filters(page: Page, labels: string[]) {
  const panelFilters = panel(page).getByTestId("dashboard-filters");
  for (const label of labels) {
    const control = panelFilters.getByLabel(label, { exact: true });
    // A checklist is a group named by its legend; the others are single controls.
    const group = panelFilters.getByRole("group", { name: label, exact: true });
    if ((await group.count()) > 0) {
      for (const box of await group.getByRole("checkbox").all()) await expect(box).toBeDisabled();
    } else {
      await expect(control).toBeDisabled();
    }
  }
}

test.describe("SPEC-0012 the dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
  });

  test("AC-0012-01 the dashboard opens on the report's four sections", async ({ page }) => {
    await expect(page.getByRole("heading", { level: 1, name: "Painel" })).toBeVisible();
    await expect(page.getByRole("tab")).toHaveText(TABS);
    await expect(page.getByRole("tab", { name: TABS[0] })).toHaveAttribute("aria-selected", "true");
  });

  test("AC-0012-02 the tabs follow the keyboard pattern for tabs", async ({ page }) => {
    await page.getByRole("tab", { name: TABS[0] }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: TABS[1] })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("tab", { name: TABS[1] })).toBeFocused();
    await expect(panel(page)).toHaveAccessibleName(TABS[1]);
    await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: TABS[3] })).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: TABS[0] })).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowLeft");
    await expect(page.getByRole("tab", { name: TABS[3] })).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("Home");
    await expect(page.getByRole("tab", { name: TABS[0] })).toHaveAttribute("aria-selected", "true");
    // One tab stop: Tab leaves the tab list for the panel.
    await page.keyboard.press("Tab");
    await expect(panel(page)).toBeFocused();
  });

  test("AC-0012-03 the selected tab survives a reload", async ({ page }) => {
    await open(page, "Itens em falta");
    await expect(page).toHaveURL(/\/dashboard\?aba=itens-em-falta$/);
    await page.reload();
    await expect(page.getByRole("tab", { name: "Itens em falta" })).toHaveAttribute("aria-selected", "true");
    await open(page, TABS[0]);
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("AC-0012-04 a block with no data says so, and its filters are off", async ({ page }) => {
    for (const name of TABS) {
      await open(page, name);
      const blocks = panel(page).getByTestId("dashboard-block");
      for (const block of await blocks.all()) {
        await expect(block.getByRole("heading").first()).not.toBeEmpty();
        await expect(block.getByTestId("sem-dados")).toHaveText("Sem dados");
      }
      await expect(panel(page).getByRole("button", { name: "Limpar filtros" })).toBeDisabled();
    }
  });

  test("AC-0012-06 atendimento por unidade", async ({ page }) => {
    await filters(page, ["Unidade", "ESF", "ESB", "Pesquisa de mercadorias", "Data"]);
    await columns(page, "Mercadorias", ["Mercadorias", "Autorizado", "Atendido", "V.T atendido"]);
    await columns(page, "Unidades", [
      "Unidade",
      "ESF",
      "ESB",
      "EMULTI",
      "EMAP",
      "EAPP",
      "EMAD Multi Prof I",
      "População",
      "Atendido",
    ]);
    await headings(page, ["Atendido e valor total atendido por unidade"]);
    await everyBlockEmpty(page, 3);
  });

  test("AC-0012-07 consumo", async ({ page }) => {
    await open(page, "Consumo");
    await filters(page, ["Mercadorias", "Unidade"]);
    await headings(page, ["Estoque", "Solicitado, autorizado, atendido e média atual por mês"]);
    await expect(panel(page).getByRole("list", { name: "Legenda" })).toHaveText(
      /Solicitado.*Autorizado.*Atendido.*Média atual/,
    );
    await everyBlockEmpty(page, 2);
  });

  test("AC-0012-08 processos licitatórios", async ({ page }) => {
    await open(page, "Processos licitatórios");
    await filters(page, ["Ano processo", "Objeto", "SKU"]);
    await headings(page, [
      "Abertura",
      "Novo processo",
      "Previsão",
      "Status",
      "Nova data projetada",
      "Progresso",
      "Vigente",
      "Vencimento",
      "Previsão de tempo sem processo vigente",
      "Etapas: planejado e real",
    ]);
    await expect(panel(page).getByRole("list", { name: "Legenda" })).toHaveText(
      /Comunicado.*ACP.*SAP-ARC.*PGM.*LCT construção de edital.*Publicação do edital.*Pregão.*Propostas \/ amostras.*Homologação/,
    );
    await columns(page, "Itens do processo", ["Ano processo", "Nº item", "Item", "Objeto", "Acompanhamento"]);
    await everyBlockEmpty(page, 11);
  });

  test("AC-0012-09 itens em falta", async ({ page }) => {
    await open(page, "Itens em falta");
    await filters(page, [
      "Impacto",
      "Grupo",
      "Aquisição",
      "Grupo de compras",
      "Movimento",
      "SKU",
      "Pregão",
      "Comprador",
      "Material",
    ]);
    await headings(page, [
      "SKU",
      "Estoque",
      "Consumo mês",
      "Informações extras",
      "Sugestões de troca",
      "Curva ABC",
      "Disponibilidade",
    ]);
    await columns(page, "Processos por grupo", ["Grupo", "Ano", "Processo", "Data projetada", "Dias sem processo"]);
    await columns(page, "Materiais", [
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
    ]);
    await everyBlockEmpty(page, 9);
  });
});

test("AC-0012-01 every perfil sees the dashboard", async ({ page }) => {
  const servidor = await member("servidor");
  await signIn(page, servidor.email, servidor.password);
  await expect(page.getByRole("tab")).toHaveText(TABS);
});

for (const width of [360, 768, 1440]) {
  test(`AC-0012-10 the dashboard holds at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await signIn(page, GESTOR.email, GESTOR.password);
    for (const name of TABS) {
      await open(page, name);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, name).toBeLessThanOrEqual(0);
    }
  });
}
