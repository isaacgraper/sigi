import { expect, type Page, test } from "@playwright/test";

import { addItem, asGestor, createAta, createGrupo, createInsumo, GESTOR, member, openFromSidebar, signIn, uniqueSku } from "./helpers";

// SPEC-0015. Every ATA and insumo is made through the API with a unique name, so
// the suite runs again on the same database.

const PROCESSO = "00301.000451/2026-12";

async function ataWithItem(quantity = "1000", unitPrice = "1", total = "1234567.89") {
  const grupo = await createGrupo();
  const insumo = await createInsumo(grupo.id);
  const ata = await createAta({ total_value: total });
  const items = await addItem(ata.id, insumo.id, { quantity, unit_price: unitPrice });
  const item = items.items.find((candidate) => candidate.insumo.id === insumo.id);
  if (!item) throw new Error("item not added");
  return { ata, insumo, item };
}

async function openByApi(ataId: string, itemId: string, quantity: string) {
  const opened = await asGestor("post", "/api/v1/notas-empenho", {
    ata_id: ataId,
    processo_sei: PROCESSO,
    items: [{ item_ata_id: itemId, quantity }],
  });
  expect(opened.status, JSON.stringify(opened.body)).toBe(201);
  return opened.body as { id: string };
}

async function advanceInDialog(page: Page, next: string, numero?: string) {
  await page.getByRole("button", { name: `Avançar para ${next}` }).click();
  const dialog = page.getByRole("alertdialog");
  if (numero) await dialog.getByRole("textbox").fill(numero);
  await dialog.getByRole("button", { name: "Avançar", exact: true }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByTestId("ne-stage")).toHaveText(next);
}

test.describe("SPEC-0015 the NE screens", () => {
  test("AC-0015-01 the list and its counters, from the sidebar", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await openFromSidebar(page, "Notas de empenho");
    await expect(page).toHaveURL(/\/notas-empenho$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Notas de empenho");
    await expect(page.getByTestId("ne-total")).not.toContainText("—");
    await expect(page.getByTestId("page-header").getByRole("link", { name: "Abrir NE" })).toBeVisible();
  });

  test("AC-0015-03 AC-0015-05 AC-0015-06 AC-0015-07 AC-0015-10 an NE from demanda to emitida", async ({ page }) => {
    const { ata, insumo } = await ataWithItem();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-empenho/nova?ata=${ata.id}`);
    await page.getByLabel("Processo SEI").fill(PROCESSO);
    await page.getByLabel(`Quantidade de ${insumo.description}`).fill("300");
    await page.getByRole("button", { name: "Abrir NE" }).click();

    await expect(page).toHaveURL(/\/notas-empenho\/[0-9a-f-]{36}$/);
    await expect(page.getByTestId("ne-stage")).toHaveText("Demanda");
    await expect(page.getByTestId("ne-steps").getByRole("listitem")).toHaveCount(5);
    await expect(page.getByTestId("ne-valor")).toHaveText("R$ 300,00");

    await advanceInDialog(page, "Validação de saldo");
    const preEmpenho = `PE${uniqueSku()}`.slice(0, 20);
    await advanceInDialog(page, "Pré-empenho", preEmpenho);
    await expect(page.getByTestId("ne-pre-empenho")).toHaveText(preEmpenho);
    const neUrl = page.url();

    await page.goto(`/atas/${ata.id}`);
    const row = page.getByTestId("saldo-item").filter({ hasText: insumo.sku });
    await expect(row.getByTestId("saldo-item-disponivel")).toHaveText("700 (300)");

    await page.goto(neUrl);
    await advanceInDialog(page, "Envio ao fornecedor");
    const numero = `NE${uniqueSku()}`.slice(0, 20);
    await advanceInDialog(page, "NE emitida", numero);
    await expect(page.getByTestId("ne-numero")).toHaveText(numero);
    await expect(page.getByTestId("ne-actions")).toHaveCount(0);

    await page.goto(`/atas/${ata.id}`);
    await expect(row.getByTestId("saldo-item-disponivel")).toHaveText("700");
  });

  test("AC-0015-04 a malformed Processo SEI is refused under its field", async ({ page }) => {
    const { ata, insumo } = await ataWithItem();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-empenho/nova?ata=${ata.id}`);
    await page.getByLabel("Processo SEI").fill("12345");
    await page.getByLabel(`Quantidade de ${insumo.description}`).fill("1");
    await page.getByRole("button", { name: "Abrir NE" }).click();
    await expect(page.getByTestId("field-error")).toContainText("NNNNN.NNNNNN/AAAA-DD");
    await expect(page).toHaveURL(/\/notas-empenho\/nova/);
  });

  test("AC-0015-08 a refused advance is read in the dialog", async ({ page }) => {
    const { ata, item } = await ataWithItem("10", "1000", "5000.00");
    const ne = await openByApi(ata.id, item.id, "10");
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-empenho/${ne.id}`);
    await advanceInDialog(page, "Validação de saldo");

    await page.getByRole("button", { name: "Avançar para Pré-empenho" }).click();
    const dialog = page.getByRole("alertdialog");
    await dialog.getByRole("textbox").fill(`PE${uniqueSku()}`.slice(0, 20));
    await dialog.getByRole("button", { name: "Avançar", exact: true }).click();
    await expect(dialog.getByTestId("ne-action-error")).toContainText("Saldo insuficiente");
    await expect(dialog.getByTestId("ne-action-error")).toContainText("R$ 5.000,00");
    await dialog.getByRole("button", { name: "Voltar" }).click();
    await expect(page.getByTestId("ne-stage")).toHaveText("Validação de saldo");
  });

  test("AC-0015-09 reverting and cancelling are the gestor's", async ({ browser }) => {
    const { ata, item } = await ataWithItem();
    const ne = await openByApi(ata.id, item.id, "1");
    await asGestor("post", `/api/v1/notas-empenho/${ne.id}/avancar`, {});

    const servidor = await member("servidor");
    const asServidor = await (await browser.newContext()).newPage();
    await signIn(asServidor, servidor.email, servidor.password);
    await asServidor.goto(`/notas-empenho/${ne.id}`);
    await expect(asServidor.getByRole("button", { name: "Avançar para Pré-empenho" })).toBeVisible();
    await expect(asServidor.getByRole("button", { name: "Reverter etapa" })).toHaveCount(0);
    await expect(asServidor.getByRole("button", { name: "Cancelar NE" })).toHaveCount(0);

    const auditor = await member("auditor");
    const asAuditor = await (await browser.newContext()).newPage();
    await signIn(asAuditor, auditor.email, auditor.password);
    await asAuditor.goto(`/notas-empenho/${ne.id}`);
    await expect(asAuditor.getByTestId("ne-stage")).toHaveText("Validação de saldo");
    await expect(asAuditor.getByTestId("ne-actions")).toHaveCount(0);

    const page = await (await browser.newContext()).newPage();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-empenho/${ne.id}`);
    await page.getByRole("button", { name: "Reverter etapa" }).click();
    const dialog = page.getByRole("alertdialog");
    await dialog.getByLabel("Justificativa").fill("Processo devolvido.");
    await dialog.getByRole("button", { name: "Reverter", exact: true }).click();
    await expect(page.getByTestId("ne-stage")).toHaveText("Demanda");

    await page.getByRole("button", { name: "Cancelar NE" }).click();
    await dialog.getByLabel("Justificativa").fill("Aberta por engano.");
    await dialog.getByRole("button", { name: "Cancelar NE" }).click();
    await expect(page.getByTestId("ne-stage")).toHaveText("Cancelada");
    await expect(page.getByTestId("ne-cancelada")).toBeVisible();
  });
});
