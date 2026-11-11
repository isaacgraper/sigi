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
  noSeriousViolations,
  openFromSidebar,
  signIn,
  uniqueSku,
} from "./helpers";

// SPEC-0017. Every record is created through the API with unique numbers, so the
// suite runs again on the same database.

const PROCESSO = "00301.000451/2026-12";
// The fornecedor of every ATA createAta registers.
const CNPJ = "11.222.333/0001-81";

async function ok(method: "get" | "post", path: string, data?: Record<string, unknown>) {
  const answer = await asGestor(method, path, data);
  expect([200, 201], JSON.stringify(answer.body)).toContain(answer.status);
  return answer.body as Record<string, unknown>;
}

/** An insumo that is an item of a fresh ATA; the ATA, the insumo and the item. */
async function itemOfAta() {
  const grupo = await createGrupo();
  const insumo = await createInsumo(grupo.id);
  const ata = await createAta({ total_value: "1234567.89" });
  const items = await addItem(ata.id, insumo.id, { quantity: "1000", unit_price: "1" });
  const item = items.items.find((candidate) => candidate.insumo.id === insumo.id);
  if (!item) throw new Error("item not added");
  return { ata, insumo, item };
}

/** An NE of 100 on the item, advanced to `until` (the number of advances). */
async function ne(ataId: string, itemId: string, until: number) {
  const opened = await ok("post", "/api/v1/notas-empenho", {
    ata_id: ataId,
    processo_sei: PROCESSO,
    items: [{ item_ata_id: itemId, quantity: "100" }],
  });
  const id = opened.id as string;
  const bodies = [{}, { numero_pre_empenho: `PE${uniqueSku()}`.slice(0, 20) }, {}, { number: `NE${uniqueSku()}`.slice(0, 20) }];
  for (const body of bodies.slice(0, until)) await ok("post", `/api/v1/notas-empenho/${id}/avancar`, body);
  const detail = await ok("get", `/api/v1/notas-empenho/${id}`);
  return { id, number: detail.number as string | null, lineId: (detail.items as { id: string }[])[0].id };
}

async function nf(neId: string, lineId: string) {
  const numero = `NF${uniqueSku()}`.slice(0, 40);
  const created = await ok("post", "/api/v1/notas-fiscais", {
    nota_empenho_id: neId,
    numero,
    data_emissao: isoDay(0),
    valor: "10",
    fornecedor_cnpj: CNPJ,
    itens: [{ item_nota_empenho_id: lineId, quantidade: "10" }],
    confirmar_data_anterior: false,
  });
  return { id: created.id as string, numero };
}

async function openAcompanhamento(page: Page, path: string) {
  await page.goto(path);
  await page.getByRole("tab", { name: "Acompanhamento" }).click();
  await expect(page).toHaveURL(/aba=acompanhamento/);
  await expect(page.getByTestId("evento").first()).toBeVisible();
}

function evento(page: Page, acao: string) {
  return page.locator(`[data-testid="evento"][data-acao="${acao}"]`);
}

function alteracao(scope: ReturnType<typeof evento>, campo: string) {
  return scope.locator(`[data-testid="alteracao"][data-campo="${campo}"]`);
}

test.describe("SPEC-0017 acompanhamento, rastreio and histórico", () => {
  test("AC-0017-01 an ATA reads what its aditivo moved", async ({ page }) => {
    const ata = await createAta({ vigencia_fim: "2027-06-30" });
    await ok("post", `/api/v1/atas/${ata.id}/aditivos`, {
      kind: "prazo",
      nova_vigencia_fim: "2028-06-30",
      justification: "Prorrogada.",
    });
    await signIn(page, GESTOR.email, GESTOR.password);

    await openAcompanhamento(page, `/atas/${ata.id}`);

    const aditivo = evento(page, "ata.aditivo_registrado");
    await expect(aditivo).toContainText("Aditivo registrado");
    const fim = alteracao(aditivo, "vigencia_fim");
    await expect(fim).toContainText("Fim da vigência");
    await expect(fim.getByTestId("antes")).toHaveText("30/06/2027");
    await expect(fim.getByTestId("depois")).toHaveText("30/06/2028");
    await expect(aditivo.getByTestId("detalhe")).toContainText("Prorrogada.");
    await noSeriousViolations(page);
  });

  test("AC-0017-02 an NE's advance and an NF's quarantine", async ({ page }) => {
    const { ata, item } = await itemOfAta();
    const issued = await ne(ata.id, item.id, 4);
    const held = await nf(issued.id, issued.lineId);
    await ok("post", `/api/v1/notas-fiscais/${held.id}/quarentena`, { motivo: "Caixa avariada." });
    await signIn(page, GESTOR.email, GESTOR.password);

    await openAcompanhamento(page, `/notas-empenho/${issued.id}`);
    const etapa = alteracao(evento(page, "ne.avancada").first(), "status");
    await expect(etapa.getByTestId("antes")).toHaveText("Envio ao fornecedor");
    await expect(etapa.getByTestId("depois")).toHaveText("NE emitida");

    await openAcompanhamento(page, `/notas-fiscais/${held.id}`);
    const quarentena = evento(page, "nf.quarentena_iniciada");
    await expect(quarentena).toContainText("NF em quarentena");
    await expect(alteracao(quarentena, "quarentena").getByTestId("depois")).toHaveText("Sim");
    await expect(alteracao(quarentena, "motivo_quarentena").getByTestId("depois")).toHaveText("Caixa avariada.");
  });

  test("AC-0017-03 a creation reads its first values, a removal the ones it had", async ({ page }) => {
    const { ata, item } = await itemOfAta();
    await ok("post", `/api/v1/atas/${ata.id}/itens/${item.id}/remover`);
    await signIn(page, GESTOR.email, GESTOR.password);

    await openAcompanhamento(page, `/atas/${ata.id}`);

    const criada = evento(page, "ata.criada");
    await expect(criada).toContainText("Criado com");
    await expect(alteracao(criada, "numero").getByTestId("depois")).toHaveText(ata.number);
    const removido = evento(page, "ata.item_removido");
    await expect(removido).toContainText("Removido");
    await expect(alteracao(removido, "quantidade").getByTestId("antes")).toHaveText("1.000");
  });

  test("AC-0017-04 a servidor has no Acompanhamento", async ({ page }) => {
    const ata = await createAta();
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);

    await page.goto(`/atas/${ata.id}`);

    await expect(page.getByRole("heading", { level: 1 })).toContainText(ata.number);
    await expect(page.getByRole("tab", { name: "Acompanhamento" })).toHaveCount(0);
  });

  test("AC-0017-05 AC-0017-06 the rastreio from the ATA to the NF", async ({ page, browser }) => {
    const { ata, insumo, item } = await itemOfAta();
    const pending = await ne(ata.id, item.id, 2);
    const issued = await ne(ata.id, item.id, 4);
    const delivered = await nf(issued.id, issued.lineId);
    await signIn(page, GESTOR.email, GESTOR.password);

    await page.goto(`/insumos/${insumo.id}`);

    const rastreio = page.getByRole("region", { name: "Rastreio" });
    const etapas = rastreio.getByTestId("rastreio-etapa");
    await expect(etapas).toHaveCount(5);
    await expect(etapas.nth(0)).toHaveAttribute("data-etapa", "ata");
    await expect(etapas.nth(1)).toHaveAttribute("data-etapa", "item_ata");
    await expect(rastreio.getByRole("link", { name: `ATA ${ata.number}` })).toHaveAttribute("href", `/atas/${ata.id}`);
    await expect(rastreio.getByRole("link", { name: `NF ${delivered.numero}` })).toHaveAttribute(
      "href",
      `/notas-fiscais/${delivered.id}`,
    );
    const pendingStep = etapas.filter({ has: page.locator(`a[href="/notas-empenho/${pending.id}"]`) });
    await expect(pendingStep.locator('[aria-current="step"]')).toHaveText(/Pré-empenho/);
    await expect(pendingStep.getByTestId("ne-faltam")).toHaveText("Faltam: Envio ao fornecedor, NE emitida");
    const issuedStep = etapas.filter({ has: page.locator(`a[href="/notas-empenho/${issued.id}"]`) });
    await expect(issuedStep.getByTestId("ne-faltam")).toHaveCount(0);

    await pendingStep.getByRole("button", { name: /Ver acompanhamento/ }).click();
    await expect(pendingStep.getByTestId("evento").first()).toContainText("NE criada");
    await expect(pendingStep.locator('[data-acao="ne.avancada"]')).toHaveCount(2);

    const auditor = await member("auditor");
    const other = await browser.newPage();
    await signIn(other, auditor.email, auditor.password);
    await other.goto(`/insumos/${insumo.id}`);
    await expect(other.getByRole("region", { name: "Rastreio" }).getByTestId("rastreio-etapa")).toHaveCount(5);
    await other.close();
  });

  test("AC-0017-07 an insumo with no ATA has no rastreio yet", async ({ page }) => {
    const insumo = await createInsumo((await createGrupo()).id);
    await signIn(page, GESTOR.email, GESTOR.password);

    await page.goto(`/insumos/${insumo.id}`);

    await expect(page.getByRole("region", { name: "Rastreio" })).toContainText("ainda não começou");
  });

  test("AC-0017-08 AC-0017-10 the Histórico from the sidebar, a row opened", async ({ page }) => {
    const ata = await createAta();
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);

    await openFromSidebar(page, "Histórico");
    await expect(page).toHaveURL(/\/historico$/);
    await expect(page.getByRole("heading", { level: 1, name: "Histórico" })).toBeVisible();
    await expect(page.getByTestId("historico-row").first()).toBeVisible();

    await page.goto(`/historico?entidade=ata&id=${ata.id}`);
    const row = page.locator('[data-testid="historico-row"][data-acao="ata.criada"]');
    await expect(row).toContainText("ATA registrada");
    await expect(row.getByRole("link", { name: "ATA" })).toHaveAttribute("href", `/atas/${ata.id}`);
    await row.getByRole("button", { name: "Detalhes de ATA registrada" }).click();
    await expect(page.getByTestId("historico-detalhe")).toContainText("Criado com");
    await expect(page.getByTestId("historico-detalhe")).toContainText(ata.number);
    await noSeriousViolations(page);
  });

  test("AC-0017-09 a filter and a period that ends before it starts", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/historico");

    await page.getByLabel("Entidade").click();
    await page.getByRole("option", { name: "ATA", exact: true }).click();
    await expect(page).toHaveURL(/entidade=ata/);
    await expect(page.getByTestId("historico-row").first()).toBeVisible();
    await page.goto(`/historico?entidade=ata&id=${ata.id}`);
    await expect(page.getByTestId("historico-row")).toHaveCount(1);

    await page.getByLabel("Até", { exact: true }).fill(isoDay(0));
    await expect(page).toHaveURL(/ate=/);
    await expect(page.getByTestId("historico-row")).toHaveCount(1);
    await page.getByLabel("De", { exact: true }).fill(isoDay(1));

    await expect(page.getByTestId("field-error")).toHaveText("A data inicial deve ser anterior ou igual à final.");
    await expect(page.getByTestId("historico-row")).toHaveCount(1);
  });

  test("AC-0017-11 only the status changes of the page", async ({ page }) => {
    const { ata, item } = await itemOfAta();
    const advanced = await ne(ata.id, item.id, 2);
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto(`/historico?entidade=nota_empenho&id=${advanced.id}`);
    await expect(page.getByTestId("historico-row")).toHaveCount(3);

    await page.getByRole("button", { name: "Só mudanças de status" }).click();

    await expect(page).toHaveURL(/so=status/);
    await expect(page.getByTestId("historico-row")).toHaveCount(2);
    await expect(page.locator('[data-testid="historico-row"][data-acao="ne.criada"]')).toHaveCount(0);
    await expect(page.getByTestId("atalho-nota")).toHaveText("2 de 3 eventos desta página.");
  });

  test("AC-0017-12 a servidor has no Histórico", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);

    await expect(page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: "Histórico" })).toHaveCount(0);
    await page.goto("/historico");
    await expect(page.getByTestId("historico-negado")).toContainText("gestor e pelo auditor");
  });
});
