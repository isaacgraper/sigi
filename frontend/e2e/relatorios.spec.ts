import { readFile } from "node:fs/promises";

import { expect, type Page, test } from "@playwright/test";

import { createAta, GESTOR, member, noSeriousViolations, openFromSidebar, signIn } from "./helpers";

// SPEC-0018. The figures are SPEC-0009's, proven by its backend tests; this
// screen names the reports and asks for the file.

const REPORT_NAMES = [
  "Execução orçamentária por ATA",
  "Posição de saldo consolidada",
  "Notas fiscais em conferência",
  "Indicadores de fornecedores",
];

function card(page: Page, relatorio: string) {
  return page.locator(`[data-testid="relatorio"][data-relatorio="${relatorio}"]`);
}

/** A CSV line's cells, by the label it starts with. */
function cells(text: string, first: string): string[] {
  const line = text.split(/\r?\n/).find((candidate) => candidate.replace(/^﻿/, "").startsWith(`${first};`));
  if (!line) throw new Error(`no line starting with ${first}`);
  return line.replace(/^﻿/, "").split(";");
}

test.describe("SPEC-0018 the Relatórios screen", () => {
  test("AC-0018-01 the four reports from the sidebar", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);

    await openFromSidebar(page, "Relatórios");

    await expect(page).toHaveURL(/\/relatorios$/);
    await expect(page.getByRole("heading", { level: 1, name: "Relatórios" })).toBeVisible();
    await expect(page.getByTestId("relatorio").getByRole("heading")).toHaveText(REPORT_NAMES);
    await noSeriousViolations(page);
  });

  test("AC-0018-02 AC-0018-03 a report of one ATA downloads", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/relatorios");

    await card(page, "execucao-orcamentaria").getByRole("button", { name: "Exportar" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("checkbox")).toHaveCount(8);
    await expect(dialog.getByLabel("Início do período")).toBeVisible();
    await dialog.locator("#exportar-ata").click();
    await page.getByRole("option", { name: `ATA ${ata.number}` }).click();
    const download = page.waitForEvent("download");
    await dialog.getByRole("button", { name: "Exportar", exact: true }).click();
    const file = await download;
    const text = await readFile(await file.path(), "utf-8");

    expect(file.suggestedFilename()).toMatch(/^sigi-execucao-orcamentaria-.*\.csv$/);
    expect(cells(text, "Relatório")[1]).toBe("Execução orçamentária por ATA");
    expect(cells(text, "Filtros")[1]).toBe(`ATA: ${ata.number}`);
  });

  test("AC-0018-04 the posição de saldo offers no period", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/relatorios");

    await card(page, "posicao-saldo").getByRole("button", { name: "Exportar" }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByLabel("Data de referência")).toBeVisible();
    await expect(dialog.getByLabel("Início do período")).toHaveCount(0);
  });

  test("AC-0018-05 a servidor has no Relatórios", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);

    await expect(page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: "Relatórios" })).toHaveCount(0);
    await page.goto("/relatorios");
    await expect(page.getByTestId("relatorios-negado")).toContainText("gestor e pelo auditor");
    await expect(page.getByTestId("relatorio")).toHaveCount(0);
  });
});
