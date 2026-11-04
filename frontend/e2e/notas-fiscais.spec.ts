import { expect, type Page, test } from "@playwright/test";

import {
  addItem,
  asGestor,
  createAta,
  createGrupo,
  createInsumo,
  GESTOR,
  isoDay,
  member,
  openFromSidebar,
  signIn,
  uniqueSku,
} from "./helpers";

// SPEC-0016. Every NE is opened and issued through the API with a unique number,
// so the suite runs again on the same database.

const PROCESSO = "00301.000451/2026-12";
// The fornecedor of every ATA createAta registers.
const CNPJ = "11.222.333/0001-81";

async function issuedNe() {
  const grupo = await createGrupo();
  const insumo = await createInsumo(grupo.id);
  const ata = await createAta({ total_value: "1234567.89" });
  const items = await addItem(ata.id, insumo.id, { quantity: "1000", unit_price: "1" });
  const item = items.items.find((candidate) => candidate.insumo.id === insumo.id);
  if (!item) throw new Error("item not added");
  const opened = await asGestor("post", "/api/v1/notas-empenho", {
    ata_id: ata.id,
    processo_sei: PROCESSO,
    items: [{ item_ata_id: item.id, quantity: "100" }],
  });
  expect(opened.status, JSON.stringify(opened.body)).toBe(201);
  const id = (opened.body as { id: string }).id;
  for (const body of [
    {},
    { numero_pre_empenho: `PE${uniqueSku()}`.slice(0, 20) },
    {},
    { number: `NE${uniqueSku()}`.slice(0, 20) },
  ]) {
    const moved = await asGestor("post", `/api/v1/notas-empenho/${id}/avancar`, body);
    expect(moved.status, JSON.stringify(moved.body)).toBe(200);
  }
  const ne = await asGestor("get", `/api/v1/notas-empenho/${id}`);
  const lineId = (ne.body as { items: { id: string }[] }).items[0].id;
  return { id, lineId, insumo };
}

async function nfByApi(neId: string, lineId: string, quantidade: string, valor = quantidade) {
  const numero = `NF${uniqueSku()}`.slice(0, 40);
  const created = await asGestor("post", "/api/v1/notas-fiscais", {
    nota_empenho_id: neId,
    numero,
    data_emissao: isoDay(0),
    valor,
    fornecedor_cnpj: CNPJ,
    itens: [{ item_nota_empenho_id: lineId, quantidade }],
    confirmar_data_anterior: false,
  });
  expect(created.status, JSON.stringify(created.body)).toBe(201);
  return { ...(created.body as { id: string }), numero };
}

async function move(nfId: string, action: string, body: Record<string, unknown> = {}) {
  const moved = await asGestor("post", `/api/v1/notas-fiscais/${nfId}/${action}`, body);
  expect(moved.status, JSON.stringify(moved.body)).toBe(200);
}

async function inDialog(page: Page, action: string, text?: { label: string; value: string }) {
  await page.getByTestId("nf-actions").getByRole("button", { name: action, exact: true }).click();
  const dialog = page.getByRole("alertdialog");
  if (text) await dialog.getByLabel(text.label).fill(text.value);
  await dialog.getByRole("button", { name: action, exact: true }).click();
  await expect(dialog).toBeHidden();
}

async function fillHeader(page: Page, numero: string, data: string, valor: string) {
  await page.getByLabel("Número da NF").fill(numero);
  await page.getByLabel("Data de emissão").fill(data);
  await page.getByLabel("Valor (R$)").fill(valor);
}

test.describe("SPEC-0016 the NF screens", () => {
  test("AC-0016-01 the list from the sidebar, newest first", async ({ page }) => {
    const ne = await issuedNe();
    const older = await nfByApi(ne.id, ne.lineId, "1");
    const newer = await nfByApi(ne.id, ne.lineId, "2");
    await signIn(page, GESTOR.email, GESTOR.password);
    await openFromSidebar(page, "Notas fiscais");
    await expect(page).toHaveURL(/\/notas-fiscais$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Notas fiscais");

    const ids = await page.getByTestId("nf-row").evaluateAll((rows) => rows.map((row) => row.getAttribute("data-nf-id")));
    expect(ids).toContain(newer.id);
    expect(ids).toContain(older.id);
    expect(ids.indexOf(newer.id)).toBeLessThan(ids.indexOf(older.id));
  });

  test("AC-0016-02 the quarantine filter is kept in the URL", async ({ page }) => {
    const ne = await issuedNe();
    const held = await nfByApi(ne.id, ne.lineId, "1");
    const free = await nfByApi(ne.id, ne.lineId, "1");
    await move(held.id, "quarentena", { motivo: "Lote sem laudo." });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/notas-fiscais");
    await page.getByLabel("Status", { exact: true }).click();
    await page.getByRole("option", { name: "Em quarentena", exact: true }).click();
    await expect(page).toHaveURL(/status=quarentena/);
    await expect(page.locator(`[data-nf-id="${held.id}"]`)).toBeVisible();
    await expect(page.locator(`[data-nf-id="${free.id}"]`)).toHaveCount(0);

    await page.reload();
    await expect(page.locator(`[data-nf-id="${held.id}"]`)).toBeVisible();
    await expect(page.locator(`[data-nf-id="${free.id}"]`)).toHaveCount(0);
  });

  test("AC-0016-03 an NF registered from the NE page", async ({ page }) => {
    const ne = await issuedNe();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-empenho/${ne.id}`);
    await expect(page.getByTestId("ne-nfs-empty")).toBeVisible();
    await page.getByRole("link", { name: "Registrar NF" }).click();

    await expect(page).toHaveURL(/\/notas-fiscais\/nova\?ne=/);
    await expect(page.getByLabel("CNPJ do fornecedor", { exact: true })).toHaveValue(CNPJ);
    await expect(page.getByTestId("nf-form-faltante")).toHaveText("100");
    const numero = `NF${uniqueSku()}`;
    await fillHeader(page, numero, isoDay(0), "60,00");
    await page.getByLabel(`Quantidade de ${ne.insumo.description}`).fill("60");
    await page.getByRole("button", { name: "Registrar NF" }).click();

    await expect(page).toHaveURL(/\/notas-fiscais\/[0-9a-f-]{36}$/);
    await expect(page.getByTestId("nf-status")).toHaveText("Aguardando");
    await expect(page.getByTestId("nf-numero")).toHaveText(numero);
    await expect(page.getByTestId("nf-valor")).toHaveText("R$ 60,00");
    await expect(page.getByTestId("nf-item")).toHaveCount(1);
  });

  test("AC-0016-04 a CNPJ that is not the fornecedor's is refused under its field", async ({ page }) => {
    const ne = await issuedNe();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-fiscais/nova?ne=${ne.id}`);
    await fillHeader(page, `NF${uniqueSku()}`, isoDay(0), "10,00");
    await page.getByLabel("CNPJ do fornecedor", { exact: true }).fill("11.444.777/0001-61");
    await page.getByLabel(`Quantidade de ${ne.insumo.description}`).fill("10");
    await page.getByRole("button", { name: "Registrar NF" }).click();
    await expect(page.getByTestId("field-error")).toContainText("não é o do fornecedor");
    await expect(page).toHaveURL(/\/notas-fiscais\/nova/);
  });

  test("AC-0016-05 a date before the NE is confirmed before it is kept", async ({ page }) => {
    const ne = await issuedNe();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-fiscais/nova?ne=${ne.id}`);
    await fillHeader(page, `NF${uniqueSku()}`, isoDay(-1), "10,00");
    await page.getByLabel(`Quantidade de ${ne.insumo.description}`).fill("10");
    await page.getByRole("button", { name: "Registrar NF" }).click();

    const confirm = page.getByTestId("nf-confirm-date");
    await expect(confirm).toBeVisible();
    await expect(page).toHaveURL(/\/notas-fiscais\/nova/);
    await confirm.getByRole("button", { name: "Confirmar data" }).click();
    await expect(page).toHaveURL(/\/notas-fiscais\/[0-9a-f-]{36}$/);
    await expect(page.getByTestId("nf-status")).toHaveText("Aguardando");
  });

  test("AC-0016-06 AC-0016-07 sent for conferência, then approved or returned", async ({ page }) => {
    const ne = await issuedNe();
    const approved = await nfByApi(ne.id, ne.lineId, "10");
    const returned = await nfByApi(ne.id, ne.lineId, "10");
    await signIn(page, GESTOR.email, GESTOR.password);

    await page.goto(`/notas-fiscais/${approved.id}`);
    await inDialog(page, "Enviar para conferência");
    await expect(page.getByTestId("nf-status")).toHaveText("Em conferência");
    await inDialog(page, "Aprovar");
    await expect(page.getByTestId("nf-status")).toHaveText("Aprovada");
    await expect(page.getByTestId("nf-actions")).toHaveCount(0);

    await page.goto(`/notas-fiscais/${returned.id}`);
    await inDialog(page, "Enviar para conferência");
    await inDialog(page, "Devolver", { label: "Justificativa", value: "Valor diverge do empenho." });
    await expect(page.getByTestId("nf-status")).toHaveText("Devolvida");
    await expect(page.getByTestId("nf-justificativa")).toContainText("Valor diverge do empenho.");
    await expect(page.getByRole("link", { name: "Corrigir" })).toBeVisible();
  });

  test("AC-0016-08 a quarantine holds the approval until it is released", async ({ page }) => {
    const ne = await issuedNe();
    const nf = await nfByApi(ne.id, ne.lineId, "10");
    await move(nf.id, "enviar");
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-fiscais/${nf.id}`);
    await inDialog(page, "Quarentena", { label: "Motivo", value: "Lote sem laudo." });

    await expect(page.getByTestId("nf-quarentena")).toHaveText("Em quarentena");
    await expect(page.getByTestId("nf-motivo")).toContainText("Lote sem laudo.");
    await expect(page.getByRole("button", { name: "Aprovar", exact: true })).toHaveCount(0);

    await inDialog(page, "Liberar");
    await expect(page.getByTestId("nf-quarentena")).toHaveCount(0);
    await expect(page.getByTestId("nf-status")).toHaveText("Em conferência");
    await expect(page.getByRole("button", { name: "Aprovar", exact: true })).toBeVisible();
  });

  test("AC-0016-09 a returned NF is corrected", async ({ page }) => {
    const ne = await issuedNe();
    const nf = await nfByApi(ne.id, ne.lineId, "60");
    await move(nf.id, "enviar");
    await move(nf.id, "devolver", { justificativa: "Quantidade errada." });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-fiscais/${nf.id}`);
    await page.getByRole("link", { name: "Corrigir" }).click();

    await expect(page).toHaveURL(/\/corrigir$/);
    await expect(page.getByLabel("Número da NF")).toHaveValue(nf.numero);
    await page.getByLabel("Valor (R$)").fill("50,00");
    await page.getByLabel(`Quantidade de ${ne.insumo.description}`).fill("50");
    await page.getByRole("button", { name: "Salvar" }).click();

    await expect(page).toHaveURL(new RegExp(`/notas-fiscais/${nf.id}$`));
    await expect(page.getByTestId("nf-valor")).toHaveText("R$ 50,00");
    await expect(page.getByTestId("nf-item")).toContainText("50");
  });

  test("AC-0016-10 what each perfil may do", async ({ browser }) => {
    const ne = await issuedNe();
    const nf = await nfByApi(ne.id, ne.lineId, "10");
    await move(nf.id, "enviar");

    const servidor = await member("servidor");
    const asServidor = await (await browser.newContext()).newPage();
    await signIn(asServidor, servidor.email, servidor.password);
    await asServidor.goto(`/notas-fiscais/${nf.id}`);
    const actions = asServidor.getByTestId("nf-actions");
    await expect(actions.getByRole("button", { name: "Quarentena", exact: true })).toBeVisible();
    for (const name of ["Aprovar", "Devolver", "Liberar"]) {
      await expect(actions.getByRole("button", { name, exact: true })).toHaveCount(0);
    }

    const auditor = await member("auditor");
    const asAuditor = await (await browser.newContext()).newPage();
    await signIn(asAuditor, auditor.email, auditor.password);
    await asAuditor.goto(`/notas-fiscais/${nf.id}`);
    await expect(asAuditor.getByTestId("nf-status")).toHaveText("Em conferência");
    await expect(asAuditor.getByTestId("nf-actions")).toHaveCount(0);
    await asAuditor.goto(`/notas-empenho/${ne.id}`);
    await expect(asAuditor.getByTestId("ne-nf")).toHaveCount(1);
    await expect(asAuditor.getByRole("link", { name: "Registrar NF" })).toHaveCount(0);
  });

  test("AC-0016-11 the NE page counts what its NFs delivered", async ({ page }) => {
    const ne = await issuedNe();
    const approved = await nfByApi(ne.id, ne.lineId, "60");
    await move(approved.id, "enviar");
    await move(approved.id, "aprovar");
    const held = await nfByApi(ne.id, ne.lineId, "10");
    await move(held.id, "quarentena", { motivo: "Lote sem laudo." });

    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/notas-empenho/${ne.id}`);
    await expect(page.getByTestId("ne-item-recebida")).toHaveText("60");
    await expect(page.getByTestId("ne-item-quarentena")).toHaveText("10");
    await expect(page.getByTestId("ne-item-faltante")).toHaveText("40");
    await expect(page.getByTestId("ne-nf")).toHaveCount(2);
    await page.getByTestId("ne-nf").getByRole("link", { name: approved.numero }).click();
    await expect(page).toHaveURL(new RegExp(`/notas-fiscais/${approved.id}$`));
  });
});
