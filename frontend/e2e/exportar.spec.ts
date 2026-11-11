import { readFile } from "node:fs/promises";

import { expect, type Page, test } from "@playwright/test";

import { addItem, asGestor, createAta, createGrupo, createInsumo, GESTOR, isoDay, member, noSeriousViolations, signIn } from "./helpers";

// SPEC-0009 v1.2: "Exportar" on every list, through one dialog. Every record is
// created through the API with unique numbers, so the suite runs again on the
// same database.

/** Open the dialog, press "Exportar" in it, and read the file it downloads. */
async function exported(page: Page, setUp?: (dialog: ReturnType<Page["getByRole"]>) => Promise<void>) {
  await page.getByRole("button", { name: "Exportar", exact: true }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  if (setUp) await setUp(dialog);
  const download = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Exportar", exact: true }).click();
  const file = await download;
  await expect(dialog).toBeHidden();
  return { name: file.suggestedFilename(), text: await readFile(await file.path(), "utf-8") };
}

/** A CSV line as its cells. */
function cells(text: string, first: string): string[] {
  const line = text.split(/\r?\n/).find((candidate) => candidate.replace(/^﻿/, "").startsWith(`${first};`));
  if (!line) throw new Error(`no line starting with ${first}`);
  return line.replace(/^﻿/, "").split(";");
}

test.describe("SPEC-0009 v1.2 the list exports", () => {
  test("AC-0009-13 the dialog offers format, columns, reference and period", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/atas");

    await page.getByRole("button", { name: "Exportar", exact: true }).click();
    const dialog = page.getByRole("dialog");

    await expect(dialog.getByRole("radio", { name: "CSV (planilha)" })).toBeChecked();
    await expect(dialog.getByRole("radio", { name: "PDF" })).not.toBeChecked();
    const boxes = dialog.getByRole("checkbox");
    await expect(boxes).toHaveCount(8);
    for (const box of await boxes.all()) await expect(box).toBeChecked();
    await expect(dialog.getByLabel("Data de referência")).toHaveValue(isoDay(0));
    await expect(dialog.getByLabel("Início do período")).toHaveValue("");
    await noSeriousViolations(page);

    for (const box of await boxes.all()) await box.uncheck();
    await expect(dialog.getByTestId("field-error")).toHaveText("Escolha ao menos uma coluna.");
    await expect(dialog.getByRole("button", { name: "Exportar", exact: true })).toBeDisabled();
  });

  test("AC-0009-10 AC-0009-13 the ATAs with their filter and the columns chosen", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/atas?status=vigente");

    const file = await exported(page, async (dialog) => {
      await dialog.getByRole("checkbox", { name: "Objeto" }).uncheck();
    });

    expect(file.name).toMatch(/^sigi-atas-\d{8}-\d{6}\.csv$/);
    expect(cells(file.text, "Relatório")[1]).toBe("ATAs");
    expect(cells(file.text, "Filtros")[1]).toBe("Status: Vigente");
    const header = cells(file.text, "Número");
    expect(header).not.toContain("Objeto");
    expect(header).toContain("Fornecedor");
    expect(cells(file.text, ata.number)[header.indexOf("Status")]).toBe("Vigente");
  });

  test("AC-0009-10 the itens of an ATA from its page", async ({ page }) => {
    const insumo = await createInsumo((await createGrupo()).id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id, { quantity: "1000", unit_price: "2.5" });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/atas/${ata.id}`);

    await page.getByRole("region", { name: "Itens" }).getByRole("button", { name: "Exportar", exact: true }).click();
    const dialog = page.getByRole("dialog");
    const download = page.waitForEvent("download");
    await dialog.getByRole("button", { name: "Exportar", exact: true }).click();
    const text = await readFile(await (await download).path(), "utf-8");

    expect(cells(text, "Filtros")[1]).toBe(`ATA: ${ata.number}`);
    expect(cells(text, "Item")).toEqual(["Item", "SKU", "Descrição", "Unidade", "Quantidade", "Valor unitário", "Valor total"]);
    expect(text).toContain(insumo.sku);
  });

  test("AC-0009-10 the NFs in quarantine keep the list's filter", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/notas-fiscais?status=quarentena");

    const file = await exported(page, async (dialog) => {
      await dialog.getByRole("radio", { name: "PDF" }).check();
    });

    expect(file.name).toMatch(/^sigi-notas-fiscais-.*\.pdf$/);
    expect(file.text.startsWith("%PDF")).toBe(true);
  });

  test("AC-0009-12 the Histórico writes what changed", async ({ page }) => {
    const ata = await createAta({ vigencia_fim: "2027-06-30" });
    const aditivo = await asGestor("post", `/api/v1/atas/${ata.id}/aditivos`, {
      kind: "prazo",
      nova_vigencia_fim: "2028-06-30",
      justification: "Prorrogada.",
    });
    expect(aditivo.status, JSON.stringify(aditivo.body)).toBe(201);
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/historico?entidade=ata&id=${ata.id}`);
    await expect(page.getByTestId("historico-row")).toHaveCount(2);

    const file = await exported(page);

    expect(cells(file.text, "Relatório")[1]).toBe("Histórico");
    const header = cells(file.text, "Quando");
    const line = file.text.split(/\r?\n/).find((candidate) => candidate.includes("Aditivo registrado"));
    expect(line?.split(";")[header.indexOf("Alterações")]).toBe("Fim da vigência: 30/06/2027 → 30/06/2028");
  });

  test("AC-0009-13 a refusal lands under the field it names", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/notas-empenho");

    await page.getByRole("button", { name: "Exportar", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Data de referência").fill(isoDay(-10));
    await dialog.getByLabel("Início do período").fill(isoDay(-5));
    await dialog.getByRole("button", { name: "Exportar", exact: true }).click();

    await expect(dialog.getByText("O início não pode ser posterior à data de referência.")).toBeVisible();
    await expect(dialog.getByLabel("Início do período")).toHaveAttribute("aria-invalid", "true");
  });

  test("AC-0009-11 a servidor exports the insumos it sees", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await page.goto("/insumos");

    const file = await exported(page);

    expect(cells(file.text, "Relatório")[1]).toBe("Insumos");
  });
});
