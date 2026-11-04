import { expect, type Page, test } from "@playwright/test";

import {
  addItem,
  asGestor,
  createAta,
  createGrupo,
  createInsumo,
  GESTOR,
  member,
  noSeriousViolations,
  openFromSidebar,
  signIn,
  uniqueSku,
} from "./helpers";

// SPEC-0014. Every grupo, insumo and ATA is created through the API with a unique
// name, so the suite runs again on the same database; each test looks only at
// what it made, searching for it when the catalogue is shared.

async function asGestorOn(page: Page, path: string) {
  await signIn(page, GESTOR.email, GESTOR.password);
  await page.goto(path);
}

async function openInsumo(page: Page, id: string, sku: string) {
  await page.goto(`/insumos/${id}`);
  await expect(page.getByRole("heading", { level: 1, name: sku })).toBeVisible();
}

async function openAta(page: Page, id: string, number: string) {
  await page.goto(`/atas/${id}`);
  await expect(page.getByRole("heading", { level: 1, name: `ATA ${number}` })).toBeVisible();
}

async function choose(page: Page, label: string, option: string) {
  await page.getByLabel(label, { exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

/** A servidor scoped to these grupos, signed in. */
async function servidorOf(page: Page, grupoIds: string[]) {
  const servidor = await member("servidor");
  if (grupoIds.length > 0) {
    const set = await asGestor("post", `/api/v1/usuarios/${servidor.id}/grupos-materiais`, { grupo_ids: grupoIds });
    expect(set.status, JSON.stringify(set.body)).toBe(200);
  }
  await signIn(page, servidor.email, servidor.password);
  return servidor;
}

function csvFile(name: string, lines: string[], encoding: "utf-8" | "latin1" = "utf-8") {
  return { name, mimeType: "text/csv", buffer: Buffer.from(`${lines.join("\r\n")}\r\n`, encoding) };
}

function itemRow(page: Page, sku: string) {
  return page.getByTestId("item-row").filter({ hasText: sku });
}

async function searchInsumo(page: Page, sku: string) {
  const dialog = page.getByRole("dialog");
  await dialog.getByPlaceholder("SKU ou descrição").fill(sku);
  await dialog.getByTestId("insumo-option").filter({ hasText: sku }).click();
  await expect(dialog.getByTestId("insumo-chosen")).toContainText(sku);
}

test.describe("SPEC-0014 the insumo screens", () => {
  test("AC-0014-01 every perfil finds Insumos in the sidebar", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    const nav = page.getByRole("navigation", { name: "Principal" });
    await expect(nav.getByRole("link")).toHaveText(["Painel", "ATAs", "Insumos", "Notas de empenho", "Membros"]);
    await openFromSidebar(page, "Insumos");
    await expect(page).toHaveURL(/\/insumos$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Insumos");
    await expect(page).toHaveTitle("Insumos · SIGI");
  });

  test("AC-0014-02 the catalogue is listed and searched", async ({ page }) => {
    const raiz = await createGrupo();
    const sub = await createGrupo(`RESTAURADORES ${uniqueSku()}`, raiz.id);
    const insumo = await createInsumo(sub.id, { codigo_doms: String(Date.now()).slice(-9) });
    await asGestorOn(page, "/insumos");
    await expect(page.getByTestId("insumo-row").first()).toBeVisible();

    await page.getByLabel("Buscar por SKU, código DOMS ou descrição", { exact: true }).fill(insumo.sku.toLowerCase());
    await expect(page).toHaveURL(new RegExp(`q=${insumo.sku.toLowerCase()}`));
    const rows = page.getByTestId("insumo-row");
    await expect(rows).toHaveCount(1);
    await expect(rows).toContainText(insumo.sku);
    await expect(rows).toContainText(`${raiz.name} › ${sub.name}`);
    await expect(rows).toContainText("Ativo");
    await expect(page.locator("main thead th")).toHaveText(["SKU", "Descrição", "Unidade", "Grupo", "Código DOMS", "Situação"]);

    await rows.getByRole("link", { name: insumo.sku }).click();
    await expect(page).toHaveURL(new RegExp(`/insumos/${insumo.id}$`));
  });

  test("AC-0014-02 more than 25 insumos are paged", async ({ page }) => {
    await asGestorOn(page, "/insumos");
    const nav = page.getByRole("navigation", { name: "Paginação" });
    await expect(nav).toContainText(/Página 1 de \d+ · \d+ insumos?/);
  });

  test("AC-0014-03 the catalogue filters by grupo and situação, in the URL", async ({ page }) => {
    const raiz = await createGrupo();
    const sub = await createGrupo(`SUB ${uniqueSku()}`, raiz.id);
    await createInsumo(sub.id);
    const gone = await createInsumo(raiz.id);
    await asGestor("post", `/api/v1/insumos/${gone.id}/descontinuar`, { justification: "Fora de linha." });
    await asGestorOn(page, "/insumos");

    await choose(page, "Grupo", raiz.name);
    await expect(page).toHaveURL(new RegExp(`grupo=${raiz.id}`));
    // The grupos below the chosen one are included.
    await expect(page.getByTestId("insumo-row")).toHaveCount(2);
    await choose(page, "Situação", "Descontinuado");
    await expect(page).toHaveURL(/situacao=descontinuado/);
    await expect(page.getByTestId("insumo-row")).toHaveCount(1);
    await expect(page.getByTestId("insumo-row")).toContainText(gone.sku);

    await page.reload();
    await expect(page.getByTestId("insumo-row")).toHaveCount(1);
    await page.getByRole("button", { name: "Limpar filtros" }).first().click();
    await expect(page).toHaveURL(/\/insumos$/);
    await expect(page.getByTestId("insumo-row").first()).toBeVisible();
  });

  test("AC-0014-04 situação reads as text", async ({ page }) => {
    const grupo = await createGrupo();
    const old = await createInsumo(grupo.id);
    const replacement = await createInsumo(grupo.id);
    const gone = await createInsumo(grupo.id);
    await asGestor("post", `/api/v1/insumos/${old.id}/substituir`, {
      substitute_id: replacement.id,
      justification: "Troca de fornecedor.",
    });
    await asGestor("post", `/api/v1/insumos/${gone.id}/descontinuar`, { justification: "Fora de linha." });
    await asGestorOn(page, `/insumos?grupo=${grupo.id}`);

    const situacao = (id: string) => page.locator(`[data-insumo-id="${id}"]`).getByTestId("insumo-situacao");
    await expect(situacao(old.id)).toHaveText(`Substituído por ${replacement.sku}`);
    await expect(situacao(gone.id)).toHaveText("Descontinuado");
    await expect(situacao(replacement.id)).toHaveText("Ativo");
    await expect(situacao(gone.id)).toHaveClass(/text-muted-foreground/);
  });

  test("AC-0014-05 an empty catalogue says why", async ({ page }) => {
    await page.route("**/api/v1/insumos?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 25 }),
      }),
    );
    await asGestorOn(page, "/insumos");
    const empty = page.getByTestId("empty-state");
    await expect(empty).toContainText("Nenhum insumo cadastrado.");
    await expect(empty.getByRole("link", { name: "Cadastrar insumo" })).toBeVisible();
    await expect(empty.getByRole("link", { name: "Importar catálogo" })).toBeVisible();

    await page.unroute("**/api/v1/insumos?*");
    await page.goto(`/insumos?q=${uniqueSku()}`);
    await expect(page.getByTestId("empty-state")).toContainText("Nenhum insumo com esses filtros.");
    await page.getByTestId("empty-state").getByRole("button", { name: "Limpar filtros" }).click();
    await expect(page).toHaveURL(/\/insumos$/);
  });

  test("AC-0014-05 a servidor with no grupos is told to ask a gestor", async ({ page }) => {
    await servidorOf(page, []);
    await page.goto("/insumos");
    await expect(page.getByTestId("empty-state")).toContainText(
      "Você ainda não tem grupos de materiais. Peça a um gestor para definir os seus.",
    );
    await expect(page.getByRole("link", { name: "Cadastrar insumo" })).toHaveCount(0);
  });

  test("AC-0014-06 a servidor is told what it sees", async ({ page }) => {
    const grupo = await createGrupo();
    const mine = await createInsumo(grupo.id);
    const other = await createInsumo((await createGrupo()).id);
    await servidorOf(page, [grupo.id]);
    await page.goto("/insumos");
    await expect(page.getByTestId("page-header")).toContainText(`Insumos dos seus grupos de materiais: ${grupo.name}`);
    await page.goto(`/insumos?q=${other.sku}`);
    await expect(page.getByTestId("empty-state")).toContainText("Nenhum insumo com esses filtros.");
    await page.goto(`/insumos?q=${mine.sku}`);
    await expect(page.getByTestId("insumo-row")).toHaveCount(1);
  });

  test("AC-0014-07 a skeleton covers the list while it loads", async ({ page }) => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route("**/api/v1/insumos?*", async (route) => {
      await held;
      await route.continue();
    });
    await asGestorOn(page, "/insumos");
    await expect(page.getByRole("status").filter({ hasText: "Carregando..." }).first()).toBeAttached();
    release();
    await expect(page.getByTestId("insumo-row").first()).toBeVisible();
  });

  test("AC-0014-07 a failed request does not pass for empty", async ({ page }) => {
    await page.route("**/api/v1/insumos?*", (route) => route.fulfill({ status: 500, contentType: "text/plain", body: "boom" }));
    await asGestorOn(page, "/insumos");
    await expect(page.getByTestId("form-error")).toHaveText("Não foi possível concluir. Tente novamente em instantes.");
    await expect(page.getByTestId("contact-gestor").first()).toBeVisible();
    await expect(page.getByText("Nenhum insumo cadastrado.")).toHaveCount(0);
  });

  test("AC-0014-08 a gestor registers an insumo on its own page", async ({ page }) => {
    const grupo = await createGrupo();
    await asGestorOn(page, "/insumos");
    await page.getByRole("link", { name: "Cadastrar insumo" }).first().click();
    await expect(page).toHaveURL(/\/insumos\/novo$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Novo insumo");

    const sku = uniqueSku();
    const form = page.locator("main form");
    await form.getByLabel("SKU", { exact: true }).fill(sku);
    await form.getByLabel("Unidade", { exact: true }).fill("CX");
    await form.getByLabel("Descrição", { exact: true }).fill("LUVA DE PROCEDIMENTO M");
    await choose(page, "Grupo", grupo.name);
    await form.getByLabel("Quantidade de referência (opcional)", { exact: true }).fill("1.000");
    const request = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/api/v1/insumos"));
    await form.getByRole("button", { name: "Cadastrar insumo" }).click();

    // AC-0014-11: the quantity typed in pt-BR reaches the API as decimal text.
    expect((await request).postDataJSON()).toMatchObject({ sku, unit: "CX", grupo_id: grupo.id, reference_quantity: "1000" });
    await expect(page.getByRole("heading", { level: 1, name: sku })).toBeVisible();
    await expect(page.getByTestId("insumo-dados")).toContainText("1.000");
    await expect(page.getByTestId("form-error")).toHaveCount(0);
  });

  test("AC-0014-08 an auditor is not offered registration", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    await page.goto("/insumos");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Insumos");
    await expect(page.getByRole("link", { name: "Cadastrar insumo" })).toHaveCount(0);
    await page.goto("/insumos/novo");
    await expect(page.getByTestId("empty-state")).toContainText("Seu perfil não permite esta ação.");
    await expect(page.locator("main form")).toHaveCount(0);
  });

  test("AC-0014-08 a servidor registers into its grupos", async ({ page }) => {
    const grupo = await createGrupo();
    await servidorOf(page, [grupo.id]);
    await page.goto("/insumos/novo");
    await page.getByLabel("Grupo", { exact: true }).click();
    // The servidor chooses only among its own grupos (AC-0003-29).
    await expect(page.getByRole("option")).toHaveText([grupo.name]);
  });

  test("AC-0014-09 the API's refusal lands on the field it names", async ({ page }) => {
    const grupo = await createGrupo();
    const taken = await createInsumo(grupo.id);
    await asGestorOn(page, "/insumos/novo");
    const form = page.locator("main form");
    await form.getByLabel("Unidade", { exact: true }).fill("UN");
    await form.getByLabel("Descrição", { exact: true }).fill("ÁLCOOL 70%");
    await choose(page, "Grupo", grupo.name);

    await form.getByLabel("SKU", { exact: true }).fill("com-hifen");
    await form.getByRole("button", { name: "Cadastrar insumo" }).click();
    const sku = form.getByLabel("SKU", { exact: true });
    await expect(sku).toHaveAttribute("aria-invalid", "true");
    await expect(sku).toBeFocused();
    await expect(form.getByTestId("field-error")).toContainText("SKU inválido");
    await expect(form.getByTestId("field-error")).toContainText("CLORDEG21");

    await sku.fill(taken.sku);
    await form.getByRole("button", { name: "Cadastrar insumo" }).click();
    await expect(form.getByTestId("field-error")).toContainText(`Já existe um insumo com este código: ${taken.sku}`);

    await sku.fill(uniqueSku());
    await form.getByLabel("Código DOMS (opcional)", { exact: true }).fill("2888.0");
    await form.getByRole("button", { name: "Cadastrar insumo" }).click();
    await expect(form.getByLabel("Código DOMS (opcional)", { exact: true })).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByTestId("field-error")).toContainText("Código DOMS inválido");
    // Every value typed is kept.
    await expect(form.getByLabel("Descrição", { exact: true })).toHaveValue("ÁLCOOL 70%");
  });

  test("AC-0014-10 a gestor corrects an insumo, sending only what changed", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id, { codigo_doms: String(Date.now()).slice(-8) });
    await asGestorOn(page, `/insumos/${insumo.id}`);
    await page.getByTestId("insumo-actions").getByRole("link", { name: "Editar" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Editar insumo ${insumo.sku}`);

    const form = page.locator("main form");
    await expect(form.getByLabel("SKU", { exact: true })).toHaveAttribute("readonly", "");
    await expect(form).toContainText("Para mudar o SKU, use Alterar SKU na página do insumo.");
    await form.getByLabel("Descrição", { exact: true }).fill("CLOREXIDINA 4% 1 L");
    await form.getByLabel("Código DOMS (opcional)", { exact: true }).fill("");
    const request = page.waitForRequest((r) => r.method() === "PATCH");
    await form.getByRole("button", { name: "Salvar" }).click();

    expect((await request).postDataJSON()).toEqual({ description: "CLOREXIDINA 4% 1 L", codigo_doms: null });
    await expect(page.getByRole("heading", { level: 1, name: insumo.sku })).toBeVisible();
    await expect(page.getByTestId("insumo-dados")).toContainText("CLOREXIDINA 4% 1 L");
    await expect(page.getByTestId("insumo-dados")).toContainText("—");
  });

  test("AC-0014-12 the insumo page shows the insumo as the API holds it", async ({ page }) => {
    const grupo = await createGrupo();
    const old = await createInsumo(grupo.id);
    const replacement = await createInsumo(grupo.id);
    await asGestor("post", `/api/v1/insumos/${old.id}/substituir`, {
      substitute_id: replacement.id,
      justification: "Troca de fornecedor.",
    });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openInsumo(page, old.id, old.sku);
    const dados = page.getByTestId("insumo-dados");
    for (const label of ["Descrição", "Unidade", "Grupo", "Código DOMS", "Código externo", "Quantidade de referência", "Cadastrado em", "Descontinuado em", "Substituído por"]) {
      await expect(dados.locator("dt", { hasText: label }).first()).toBeVisible();
    }
    await expect(page.getByTestId("page-header")).toContainText(`Substituído por ${replacement.sku}`);
    await dados.getByRole("link", { name: new RegExp(replacement.sku) }).click();
    await expect(page.getByRole("heading", { level: 1, name: replacement.sku })).toBeVisible();

    await page.goto("/insumos/00000000-0000-4000-8000-000000000000");
    await expect(page.getByTestId("empty-state")).toContainText("Insumo não encontrado.");
  });

  test("AC-0014-12 an insumo outside a servidor's grupos is not found", async ({ page }) => {
    const other = await createInsumo((await createGrupo()).id);
    await servidorOf(page, [(await createGrupo()).id]);
    await page.goto(`/insumos/${other.id}`);
    await expect(page.getByTestId("empty-state")).toContainText("Insumo não encontrado.");
  });

  test("AC-0014-13 the ATAs an insumo is an item of", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const lone = await createInsumo(grupo.id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id, { quantity: "1000", unit_price: "0.00599" });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openInsumo(page, insumo.id, insumo.sku);
    const row = page.getByTestId("insumo-ata-row");
    await expect(row).toHaveCount(1);
    await expect(row).toContainText(ata.number);
    await expect(row).toContainText("Vigente");
    await expect(row).toContainText("1.000");
    await expect(row).toContainText("R$ 0,00599");
    await row.getByRole("link", { name: ata.number }).click();
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));

    await openInsumo(page, lone.id, lone.sku);
    await expect(page.getByText("Este insumo não é item de nenhuma ATA.")).toBeVisible();
  });

  test("AC-0014-14 a gestor changes the SKU, with a justification", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const taken = await createInsumo(grupo.id);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openInsumo(page, insumo.id, insumo.sku);
    await page.getByRole("button", { name: "Alterar SKU" }).click();
    const dialog = page.getByRole("dialog");
    const confirm = dialog.getByRole("button", { name: "Alterar SKU" });
    await expect(confirm).toBeDisabled();

    await dialog.getByLabel("Novo SKU", { exact: true }).fill(taken.sku);
    await dialog.getByLabel("Justificativa", { exact: true }).fill("Código conhecido após a primeira compra.");
    await confirm.click();
    await expect(dialog.getByTestId("field-error")).toContainText("Já existe um insumo com este código");
    await expect(dialog).toBeVisible();

    const next = uniqueSku();
    await dialog.getByLabel("Novo SKU", { exact: true }).fill(next);
    await confirm.click();
    await expect(page.getByRole("heading", { level: 1, name: next })).toBeVisible();
    await expect(page.getByTestId("form-error")).toHaveCount(0);
  });

  test("AC-0014-15 a gestor discontinues, substitutes and reactivates", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const replacement = await createInsumo(grupo.id);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openInsumo(page, insumo.id, insumo.sku);
    const actions = page.getByTestId("insumo-actions");
    await expect(actions.getByRole("button", { name: "Reativar" })).toHaveCount(0);

    await actions.getByRole("button", { name: "Descontinuar" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("deixa de entrar em itens novos");
    await dialog.getByLabel("Justificativa", { exact: true }).fill("Fora de linha.");
    await dialog.getByRole("button", { name: "Descontinuar" }).click();
    await expect(page.getByTestId("page-header").getByTestId("insumo-situacao")).toHaveText("Descontinuado");

    await actions.getByRole("button", { name: "Reativar" }).click();
    await page.getByRole("dialog").getByLabel("Justificativa", { exact: true }).fill("Descontinuado por engano.");
    await page.getByRole("dialog").getByRole("button", { name: "Reativar" }).click();
    await expect(page.getByTestId("page-header").getByTestId("insumo-situacao")).toHaveText("Ativo");

    await actions.getByRole("button", { name: "Substituir" }).click();
    await searchInsumo(page, replacement.sku);
    await page.getByRole("dialog").getByLabel("Justificativa", { exact: true }).fill("Troca de fornecedor.");
    await page.getByRole("dialog").getByRole("button", { name: "Substituir" }).click();
    await expect(page.getByTestId("page-header").getByTestId("insumo-situacao")).toHaveText(
      `Substituído por ${replacement.sku}`,
    );
  });

  test("AC-0014-15 a servidor and an auditor are offered no gestor action", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    await servidorOf(page, [grupo.id]);
    await openInsumo(page, insumo.id, insumo.sku);
    // A servidor corrects; everything else is the gestor's.
    await expect(page.getByTestId("insumo-actions").getByRole("link", { name: "Editar" })).toBeVisible();
    for (const name of ["Alterar SKU", "Descontinuar", "Substituir", "Reativar"]) {
      await expect(page.getByRole("button", { name })).toHaveCount(0);
    }
    await page.context().clearCookies();
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    await openInsumo(page, insumo.id, insumo.sku);
    await expect(page.getByTestId("insumo-actions")).toHaveCount(0);
  });

  test("AC-0014-16 the grupos are shown as a tree", async ({ page }) => {
    const raiz = await createGrupo();
    const sub = await createGrupo(`SUB ${uniqueSku()}`, raiz.id);
    const leaf = await createGrupo(`CLASSE ${uniqueSku()}`, sub.id);
    await asGestorOn(page, "/insumos");
    await page.getByRole("link", { name: "Grupos de materiais" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Grupos de materiais");
    const row = (name: string) => page.getByTestId("grupo-row").filter({ hasText: name });
    await expect(row(raiz.name)).toHaveAttribute("data-level", "1");
    await expect(row(sub.name)).toHaveAttribute("data-level", "2");
    await expect(row(leaf.name)).toHaveAttribute("data-level", "3");
    const names = await page.getByTestId("grupo-row").allTextContents();
    const at = (name: string) => names.findIndex((text) => text.includes(name));
    expect(at(raiz.name)).toBeLessThan(at(sub.name));
    expect(at(sub.name)).toBeLessThan(at(leaf.name));
  });

  test("AC-0014-17 a gestor creates and renames grupos", async ({ page }) => {
    await asGestorOn(page, "/insumos/grupos");
    const name = `GRUPO ${uniqueSku()}`;
    await page.getByRole("button", { name: "Novo grupo" }).click();
    await page.getByRole("dialog").getByLabel("Nome", { exact: true }).fill(name);
    await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
    const raiz = page.getByTestId("grupo-row").filter({ hasText: name });
    await expect(raiz).toHaveAttribute("data-level", "1");

    const sub = `SUB ${uniqueSku()}`;
    await page.getByRole("button", { name: `Adicionar subgrupo em ${name}` }).click();
    await page.getByRole("dialog").getByLabel("Nome", { exact: true }).fill(sub);
    await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByTestId("grupo-row").filter({ hasText: sub })).toHaveAttribute("data-level", "2");

    const leaf = `CLASSE ${uniqueSku()}`;
    await page.getByRole("button", { name: `Adicionar subgrupo em ${sub}` }).click();
    await page.getByRole("dialog").getByLabel("Nome", { exact: true }).fill(leaf);
    await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByTestId("grupo-row").filter({ hasText: leaf })).toHaveAttribute("data-level", "3");
    // No fourth level is offered.
    await expect(page.getByRole("button", { name: `Adicionar subgrupo em ${leaf}` })).toHaveCount(0);

    // A sibling of the same name, ignoring case, is refused and the dialog stays.
    const other = await createGrupo();
    await page.reload();
    await page.getByRole("button", { name: `Renomear ${other.name}` }).click();
    await expect(page.getByRole("dialog").getByLabel("Nome", { exact: true })).toHaveValue(other.name);
    await page.getByRole("dialog").getByLabel("Nome", { exact: true }).fill(name.toLowerCase());
    await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByRole("dialog").getByTestId("field-error")).toHaveText("Já existe um grupo com este nome aqui.");
    const renamed = `RENOMEADO ${uniqueSku()}`;
    await page.getByRole("dialog").getByLabel("Nome", { exact: true }).fill(renamed);
    await page.getByRole("dialog").getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByTestId("grupo-row").filter({ hasText: renamed })).toBeVisible();
  });

  test("AC-0014-17 a servidor and an auditor see the tree without controls", async ({ page }) => {
    const grupo = await createGrupo();
    await servidorOf(page, [grupo.id]);
    await page.goto("/insumos/grupos");
    await expect(page.getByTestId("grupo-row")).toHaveText([grupo.name]);
    await expect(page.getByRole("button", { name: "Novo grupo" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^Renomear/ })).toHaveCount(0);
  });

  test("AC-0014-18 a gestor checks a catalogue file before importing it", async ({ page }) => {
    await asGestorOn(page, "/insumos");
    await page.getByRole("link", { name: "Importar catálogo" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Importar catálogo");
    await expect(page.getByTestId("import-columns")).toContainText("sku (obrigatória)");

    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Baixar modelo" }).click();
    const file = await download;
    expect(file.suggestedFilename()).toBe("modelo-catalogo.csv");
    const path = await file.path();
    const { readFile } = await import("node:fs/promises");
    expect(await readFile(path, "utf-8")).toBe(
      "sku;descricao;unidade;grupo;subgrupo;classificacao;codigo_doms;codigo_externo;quantidade_referencia\r\n",
    );

    // A Windows-1252 file goes as its bytes, and its accents arrive intact.
    const sku = uniqueSku();
    const grupo = `GRUPO ${uniqueSku()}`;
    // Choosing the file is the check: no other action is asked (AC-0014-18).
    const request = page.waitForRequest((r) => r.url().includes("/api/v1/insumos/importacao"));
    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles(
      csvFile("catalogo.csv", ["sku;descricao;unidade;grupo", `${sku};SOLUÇÃO FISIOLÓGICA 0,9%;UN;${grupo}`], "latin1"),
    );
    const sent = await request;
    expect(sent.url()).toContain("dry_run=true");
    expect(sent.headers()["content-type"]).toBe("text/csv");
    await expect(page.getByTestId("import-check")).toBeVisible();

    // Nothing was written by the check.
    const before = await asGestor("get", `/api/v1/insumos?q=${sku}`);
    expect((before.body as { total: number }).total).toBe(0);

    // Imported, the accents read as the file wrote them: the bytes went unchanged.
    await page.getByRole("button", { name: "Confirmar importação" }).click();
    await expect(page.getByTestId("import-result")).toBeVisible();
    const after = await asGestor("get", `/api/v1/insumos?q=${sku}`);
    expect((after.body as { items: { description: string }[] }).items[0].description).toBe("SOLUÇÃO FISIOLÓGICA 0,9%");
  });

  test("AC-0014-18 a file too large or not a .csv is not sent", async ({ page }) => {
    await asGestorOn(page, "/insumos/importar");
    let sent = 0;
    page.on("request", (r) => {
      if (r.url().includes("/importacao")) sent += 1;
    });
    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles({
      name: "planilha.xlsx",
      mimeType: "application/octet-stream",
      buffer: Buffer.from("PK"),
    });
    await expect(page.getByTestId("import-refused").getByTestId("form-error")).toHaveText("Escolha um arquivo .csv.");
    await page.getByRole("button", { name: "Escolher outro arquivo" }).click();
    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles({
      name: "grande.csv",
      mimeType: "text/csv",
      buffer: Buffer.alloc(5 * 1024 * 1024 + 1, "a"),
    });
    await expect(page.getByTestId("import-refused").getByTestId("form-error")).toHaveText("O arquivo passa de 5 MB.");
    expect(sent).toBe(0);
  });

  test("AC-0014-19 the check shows what the import will do, then imports", async ({ page }) => {
    await asGestorOn(page, "/insumos/importar");
    const sku = uniqueSku();
    // A DOMS code no earlier run imported, lifted out of the descrição (AC-0003-19).
    const code = String(Date.now()).slice(-9);
    const grupo = `GRUPO ${uniqueSku()}`;
    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles(
      csvFile("catalogo.csv", [
        "sku;descricao;unidade;grupo;estoque",
        `${sku};${code} - CLOREXIDINA 2% - 1 L;UN;${grupo};40`,
      ]),
    );
    const check = page.getByTestId("import-check");
    await expect(check.getByRole("heading")).toHaveText("Confira os dados antes de importar");
    await expect(check.getByTestId("import-counts")).toContainText("Serão criados1");
    await expect(check.getByTestId("import-counts")).toContainText("Descrições a corrigir1");
    await expect(check.getByTestId("import-ignored")).toContainText("estoque");
    // The lines as the API read them: the code lifted out, the action named (AC-0003-33).
    const line = check.getByTestId("import-line");
    await expect(line).toHaveCount(1);
    await expect(line).toContainText(sku);
    await expect(line).toContainText("CLOREXIDINA 2% - 1 L");
    await expect(line).toContainText(code);
    await expect(line).toContainText(grupo);
    await expect(line).toContainText("Novo");

    const request = page.waitForRequest((r) => r.url().includes("dry_run=false"));
    await check.getByRole("button", { name: "Confirmar importação" }).click();
    await request;
    const result = page.getByTestId("import-result");
    await expect(result.getByRole("heading")).toHaveText("Importação concluída");
    await expect(result.getByTestId("import-counts")).toContainText("Criados1");
    await expect(result.getByTestId("import-line")).toContainText(sku);
    await result.getByRole("link", { name: "Ver o catálogo" }).click();
    await page.goto(`/insumos?q=${sku}`);
    await expect(page.getByTestId("insumo-row")).toContainText("CLOREXIDINA 2% - 1 L");
  });

  test("AC-0014-19 a refused file lists its lines and offers no import", async ({ page }) => {
    await asGestorOn(page, "/insumos/importar");
    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles(
      csvFile("catalogo.csv", ["sku;descricao;unidade;grupo", `${uniqueSku()};;UN;G`, `com-hifen;ITEM;UN;G`]),
    );
    const refused = page.getByTestId("import-refused");
    await expect(refused.getByTestId("form-error")).toContainText("Nenhuma linha foi importada.");
    await expect(refused.getByTestId("import-row")).toHaveCount(2);
    await expect(refused.getByTestId("import-row").first()).toContainText("2");
    await expect(refused.getByTestId("import-row").first()).toContainText("descricao");
    await expect(page.getByRole("button", { name: "Confirmar importação" })).toHaveCount(0);

    await refused.getByRole("button", { name: "Escolher outro arquivo" }).click();
    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles(csvFile("vazio.csv", ["coluna;outra", "a;b"]));
    await expect(page.getByTestId("import-refused").getByTestId("form-error")).toContainText(
      "Não foi possível ler o arquivo",
    );
    await expect(page.getByRole("button", { name: "Confirmar importação" })).toHaveCount(0);
  });

  test("AC-0014-20 a gestor imports an ATA's items the same way", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await page.getByRole("link", { name: "Importar itens" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Importar itens da ATA ${ata.number}`);

    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Baixar modelo" }).click();
    expect((await download).suggestedFilename()).toBe("modelo-itens-ata.csv");

    await page.getByLabel("Arquivo CSV", { exact: true }).setInputFiles(
      csvFile("itens.csv", ["sku;quantidade;valor_unitario;numero_item", `${insumo.sku};1.000;0,00599;12`]),
    );
    const check = page.getByTestId("import-check");
    await expect(check.getByTestId("import-counts")).toContainText("Serão adicionados1");
    await expect(check.getByTestId("import-line")).toContainText("R$ 0,00599");
    await expect(check.getByTestId("import-line")).toContainText("1.000");
    await expect(check.getByTestId("import-line")).toContainText("Novo");
    await page.getByRole("button", { name: "Confirmar importação" }).click();
    await expect(page.getByTestId("import-result").getByTestId("import-counts")).toContainText("Adicionados1");
    await page.getByRole("link", { name: "Voltar para a ATA" }).click();
    await expect(itemRow(page, insumo.sku)).toContainText("R$ 0,00599");
    await expect(itemRow(page, insumo.sku)).toContainText("R$ 5,99");
  });

  test("AC-0014-20 readers and a closed ATA are not offered the items import", async ({ page }) => {
    const ata = await createAta({}, ["encerrar"]);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await expect(page.getByRole("link", { name: "Importar itens" })).toHaveCount(0);
    await page.goto(`/atas/${ata.id}/itens/importar`);
    await expect(page.getByTestId("empty-state")).toContainText("Uma ATA encerrada ou cancelada não pode ser editada.");

    await page.context().clearCookies();
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    const open = await createAta();
    await page.goto(`/atas/${open.id}/itens/importar`);
    await expect(page.getByTestId("empty-state")).toContainText("Seu perfil não permite esta ação.");
  });

  test("AC-0014-21 the ATA page lists its items", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const other = await createInsumo(grupo.id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id, { quantity: "1000", unit_price: "0.00599", item_number: "2" });
    await addItem(ata.id, other.id, {
      quantity: "3",
      unit_price: "1.5",
      item_number: "10",
      fornecedor: { cnpj: "11.444.777/0001-61", legal_name: "Proteção Hospitalar S.A." },
    });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);

    const section = page.getByRole("region", { name: "Itens" });
    await expect(section.locator("thead th").filter({ hasNotText: "Ações" })).toHaveText([
      "Nº",
      "SKU",
      "Descrição",
      "Unidade",
      "Quantidade",
      "Valor unitário",
      "Valor total",
      "Fornecedor",
    ]);
    // Ordered by the item's number, read as a number: 2 before 10.
    await expect(page.getByTestId("item-row").first()).toContainText(insumo.sku);
    const first = itemRow(page, insumo.sku);
    await expect(first.getByTestId("item-quantity")).toHaveText("1.000");
    await expect(first.getByTestId("item-unit-price")).toHaveText("R$ 0,00599");
    await expect(first.getByTestId("item-total")).toHaveText("R$ 5,99");
    await expect(first.getByTestId("item-fornecedor")).toHaveText("");
    await expect(itemRow(page, other.sku).getByTestId("item-unit-price")).toHaveText("R$ 1,50");
    await expect(itemRow(page, other.sku).getByTestId("item-fornecedor")).toHaveText("Proteção Hospitalar S.A.");
    await first.getByRole("link", { name: insumo.sku }).click();
    await expect(page).toHaveURL(new RegExp(`/insumos/${insumo.id}$`));

    const empty = await createAta();
    await openAta(page, empty.id, empty.number);
    await expect(page.getByRole("region", { name: "Itens" })).toContainText("Nenhum item cadastrado.");
    await expect(page.getByRole("button", { name: "Adicionar item" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Importar itens" })).toBeVisible();
  });

  test("AC-0014-22 the sum of the items is shown beside the ATA's value", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta({ total_value: "10000.00" });
    await addItem(ata.id, insumo.id, { quantity: "98", unit_price: "100" });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await expect(page.getByTestId("items-sum")).toContainText("Soma dos itens: R$ 9.800,00 · Valor total da ATA: R$ 10.000,00");
    await expect(page.getByTestId("items-differ")).toHaveText(
      "A soma dos itens difere do valor total da ATA. Confira os itens ou o valor da ATA.",
    );

    const equal = await createAta({ total_value: "150.00" });
    await addItem(equal.id, insumo.id);
    await openAta(page, equal.id, equal.number);
    await expect(page.getByTestId("items-sum")).toBeVisible();
    await expect(page.getByTestId("items-differ")).toHaveCount(0);

    await page.context().clearCookies();
    await servidorOf(page, [grupo.id]);
    await openAta(page, ata.id, ata.number);
    await expect(page.getByRole("region", { name: "Itens" })).toContainText("Itens dos seus grupos de materiais.");
    await expect(itemRow(page, insumo.sku)).toBeVisible();
    await expect(page.getByTestId("items-sum")).toHaveCount(0);
  });

  test("AC-0014-23 a gestor adds an item", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await page.getByRole("button", { name: "Adicionar item" }).click();
    const dialog = page.getByRole("dialog");
    await searchInsumo(page, insumo.sku);
    await dialog.getByLabel("Quantidade", { exact: true }).fill("1.000");
    await dialog.getByLabel("Valor unitário (R$)", { exact: true }).fill("0,00599");
    await dialog.getByLabel("Nº do item (opcional)", { exact: true }).fill("12");
    await dialog.getByLabel("Fornecedor diferente do da ATA", { exact: true }).check();
    await dialog.getByLabel("CNPJ do fornecedor", { exact: true }).fill("11444777000161");
    await dialog.getByLabel("Razão social", { exact: true }).fill("Proteção Hospitalar S.A.");
    const request = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/itens"));
    await dialog.getByRole("button", { name: "Adicionar item" }).click();

    // AC-0014-11: typed in pt-BR, sent exactly.
    expect((await request).postDataJSON()).toEqual({
      insumo_id: insumo.id,
      quantity: "1000",
      unit_price: "0.00599",
      item_number: "12",
      fornecedor: { cnpj: "11.444.777/0001-61", legal_name: "Proteção Hospitalar S.A." },
    });
    await expect(dialog).toHaveCount(0);
    await expect(itemRow(page, insumo.sku).getByTestId("item-total")).toHaveText("R$ 5,99");
    await expect(itemRow(page, insumo.sku).getByTestId("item-fornecedor")).toHaveText("Proteção Hospitalar S.A.");

    // The same insumo again is refused under Insumo, every value kept.
    await page.getByRole("button", { name: "Adicionar item" }).click();
    await searchInsumo(page, insumo.sku);
    await dialog.getByLabel("Quantidade", { exact: true }).fill("5");
    await dialog.getByLabel("Valor unitário (R$)", { exact: true }).fill("1,00");
    await dialog.getByRole("button", { name: "Adicionar item" }).click();
    await expect(dialog.getByTestId("field-error")).toHaveText("Este insumo já é um item desta ATA. Corrija o item existente.");
    await expect(dialog.getByLabel("Quantidade", { exact: true })).toHaveValue("5");
  });

  test("AC-0014-23 a discontinued insumo is refused, and a closed ATA takes no item", async ({ page }) => {
    const grupo = await createGrupo();
    const gone = await createInsumo(grupo.id);
    const ata = await createAta();
    await asGestor("post", `/api/v1/insumos/${gone.id}/descontinuar`, { justification: "Fora de linha." });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await page.getByRole("button", { name: "Adicionar item" }).click();
    // The search offers only ativos, so a discontinued insumo is not found there.
    await page.getByRole("dialog").getByPlaceholder("SKU ou descrição").fill(gone.sku);
    await expect(page.getByRole("dialog")).toContainText("Nenhum insumo ativo encontrado.");
    await page.keyboard.press("Escape");

    const closed = await createAta({}, ["encerrar"]);
    await openAta(page, closed.id, closed.number);
    await expect(page.getByRole("button", { name: "Adicionar item" })).toHaveCount(0);
  });

  test("AC-0014-24 a gestor corrects or removes an item", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id, {
      fornecedor: { cnpj: "11.444.777/0001-61", legal_name: "Proteção Hospitalar S.A." },
    });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);

    await page.getByRole("button", { name: `Ações para ${insumo.sku}` }).click();
    await expect(page.getByRole("menuitem")).toHaveText(["Corrigir", "Aditivo de quantidade", "Remover"]);
    await page.getByRole("menuitem", { name: "Corrigir" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByLabel("Quantidade", { exact: true })).toHaveValue("100");
    await dialog.getByLabel("Quantidade", { exact: true }).fill("80");
    await dialog.getByLabel("Fornecedor diferente do da ATA", { exact: true }).uncheck();
    const request = page.waitForRequest((r) => r.method() === "PATCH");
    await dialog.getByRole("button", { name: "Salvar" }).click();
    expect((await request).postDataJSON()).toEqual({ quantity: "80", fornecedor: null });
    await expect(itemRow(page, insumo.sku).getByTestId("item-quantity")).toHaveText("80");
    await expect(itemRow(page, insumo.sku).getByTestId("item-fornecedor")).toHaveText("");

    await page.getByRole("button", { name: `Ações para ${insumo.sku}` }).click();
    await page.getByRole("menuitem", { name: "Remover" }).click();
    const confirm = page.getByRole("alertdialog");
    await expect(confirm).toContainText(`O item ${insumo.sku} sai da ATA`);
    await confirm.getByRole("button", { name: "Remover item" }).click();
    await expect(itemRow(page, insumo.sku)).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Itens" })).toContainText("Nenhum item cadastrado.");
  });

  test("AC-0014-24 a refusal for a closed ATA reloads it", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    // Closed behind the page's back.
    await asGestor("post", `/api/v1/atas/${ata.id}/encerrar`);
    await page.getByRole("button", { name: `Ações para ${insumo.sku}` }).click();
    await page.getByRole("menuitem", { name: "Remover" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Remover item" }).click();
    await expect(page.getByTestId("remove-error")).toHaveText("Uma ATA encerrada ou cancelada não pode ser editada.");
    await page.getByRole("alertdialog").getByRole("button", { name: "Voltar" }).click();
    await expect(page.getByTestId("ata-status")).toHaveText("Encerrada");
    await expect(page.getByRole("button", { name: `Ações para ${insumo.sku}` })).toHaveCount(0);
  });

  test("AC-0014-25 and -26 a gestor records an aditivo de quantidade on an item", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    const items = await addItem(ata.id, insumo.id);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);

    await page.getByRole("button", { name: `Ações para ${insumo.sku}` }).click();
    await page.getByRole("menuitem", { name: "Aditivo de quantidade" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText(`Item ${insumo.sku}, quantidade contratada 100 UN.`);
    await dialog.getByLabel("Quantidade acrescida", { exact: true }).fill("30");
    await dialog.getByLabel("Justificativa", { exact: true }).fill("Demanda maior.");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    await expect(dialog.getByTestId("field-error")).toHaveText("O aditivo passa de 25% da quantidade do item. Reduza a quantidade.");

    const request = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/aditivos"));
    await dialog.getByLabel("Quantidade acrescida", { exact: true }).fill("20");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    expect((await request).postDataJSON()).toEqual({
      kind: "quantidade",
      item_id: items.items[0].id,
      quantity: "20",
      justification: "Demanda maior.",
    });
    await expect(itemRow(page, insumo.sku).getByTestId("item-quantity")).toHaveText("120 (100 + 20)");
    await expect(itemRow(page, insumo.sku).getByTestId("item-total")).toHaveText("R$ 180,00");
    const aditivo = page.getByTestId("aditivo-row").filter({ hasText: "Quantidade" });
    await expect(aditivo).toContainText(`+20 UN · ${insumo.sku}`);
    await expect(aditivo).toContainText("Demanda maior.");
  });

  test("AC-0014-25 the aditivo de quantidade is offered only on a vigente ATA", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta({}, ["suspender"]);
    await addItem(ata.id, insumo.id);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await page.getByRole("button", { name: `Ações para ${insumo.sku}` }).click();
    await expect(page.getByRole("menuitem")).toHaveText(["Corrigir", "Remover"]);
  });

  test("AC-0014-26 a quantity aditivo outside a servidor's grupos shows no SKU", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    const items = await addItem(ata.id, insumo.id);
    await asGestor("post", `/api/v1/atas/${ata.id}/aditivos`, {
      kind: "quantidade",
      item_id: items.items[0].id,
      quantity: "20",
      justification: "Demanda maior.",
    });
    await servidorOf(page, [(await createGrupo()).id]);
    await openAta(page, ata.id, ata.number);
    const aditivo = page.getByTestId("aditivo-row").filter({ hasText: "Quantidade" });
    await expect(aditivo.locator("td").nth(1)).toHaveText("+20");
  });

  test("AC-0014-27 readers read the items", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id);
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    await openAta(page, ata.id, ata.number);
    await expect(itemRow(page, insumo.sku)).toBeVisible();
    await expect(page.getByTestId("items-sum")).toBeVisible();
    await expect(page.getByRole("button", { name: "Adicionar item" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Importar itens" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: `Ações para ${insumo.sku}` })).toHaveCount(0);
  });

  test("AC-0014-28 a gestor sets a servidor's grupos from the member list", async ({ page }) => {
    const raiz = await createGrupo();
    const sub = await createGrupo(`SUB ${uniqueSku()}`, raiz.id);
    const other = await createGrupo();
    const servidor = await member("servidor");
    await asGestor("post", `/api/v1/usuarios/${servidor.id}/grupos-materiais`, { grupo_ids: [other.id] });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/members");
    // The newest member is on the first page.
    const row = page.locator(`[data-member-id="${servidor.id}"]`);
    await row.getByRole("button", { name: /^Ações para/ }).click();
    await page.getByRole("menuitem", { name: "Grupos de materiais" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("O servidor vê os insumos dos grupos marcados e dos grupos abaixo deles.");
    await expect(dialog.getByLabel(other.name, { exact: true })).toBeChecked();

    await dialog.getByLabel(raiz.name, { exact: true }).check();
    const child = dialog.getByLabel(sub.name, { exact: true });
    await expect(child).toBeChecked();
    await expect(child).toBeDisabled();
    await expect(dialog).toContainText(`Incluído por ${raiz.name}`);
    await dialog.getByLabel(other.name, { exact: true }).uncheck();
    const request = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/grupos-materiais"));
    await dialog.getByRole("button", { name: "Salvar grupos" }).click();
    expect((await request).postDataJSON()).toEqual({ grupo_ids: [raiz.id] });
    await expect(dialog).toHaveCount(0);

    // Nothing ticked asks first.
    await row.getByRole("button", { name: /^Ações para/ }).click();
    await page.getByRole("menuitem", { name: "Grupos de materiais" }).click();
    await expect(dialog.getByLabel(raiz.name, { exact: true })).toBeChecked();
    await dialog.getByLabel(raiz.name, { exact: true }).uncheck();
    await dialog.getByRole("button", { name: "Salvar grupos" }).click();
    await expect(dialog.getByTestId("grupos-empty")).toContainText("Sem grupos, o servidor não vê nenhum insumo.");
    await expect(dialog).toBeVisible();
  });

  test("AC-0014-28 only a servidor has grupos de materiais", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/members");
    await page.locator(`[data-member-id="${auditor.id}"]`).getByRole("button", { name: /^Ações para/ }).click();
    await expect(page.getByRole("menuitem", { name: "Grupos de materiais" })).toHaveCount(0);
  });

  test("AC-0014-29 every field says what it is", async ({ page }) => {
    await asGestorOn(page, "/insumos/novo");
    const form = page.locator("main form");
    await expect(form.getByTestId("info-tip")).toHaveCount(7);
    const about = form.getByRole("button", { name: "Sobre SKU" });
    await about.click();
    await expect(form).toContainText("Código do item no CAME, letras e números com ao menos uma letra");
    await page.keyboard.press("Escape");
    await expect(about).toHaveAttribute("aria-expanded", "false");
    await expect(about).toBeFocused();
  });

  for (const width of [360, 768, 1440]) {
    test(`AC-0014-30 every page holds at ${width}px`, async ({ page }) => {
      const grupo = await createGrupo();
      const insumo = await createInsumo(grupo.id);
      const ata = await createAta();
      await addItem(ata.id, insumo.id, { unit_price: "0.00599" });
      await page.setViewportSize({ width, height: 900 });
      await signIn(page, GESTOR.email, GESTOR.password);
      const overflow = () =>
        page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

      for (const path of ["/insumos", "/insumos/novo", "/insumos/grupos", "/insumos/importar", `/atas/${ata.id}/itens/importar`]) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.getByTestId("page-skeleton")).toHaveCount(0);
        expect(await overflow(), path).toBeLessThanOrEqual(0);
      }
      await openInsumo(page, insumo.id, insumo.sku);
      expect(await overflow()).toBeLessThanOrEqual(0);
      await openAta(page, ata.id, ata.number);
      await expect(itemRow(page, insumo.sku)).toBeVisible();
      expect(await overflow()).toBeLessThanOrEqual(0);
      await page.getByRole("button", { name: "Adicionar item" }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      expect(await overflow()).toBeLessThanOrEqual(0);
    });
  }

  test("AC-0014-30 every page passes the accessibility check", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await addItem(ata.id, insumo.id);
    await signIn(page, GESTOR.email, GESTOR.password);
    for (const path of ["/insumos", "/insumos/novo", "/insumos/grupos", "/insumos/importar"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByTestId("page-skeleton")).toHaveCount(0);
      await noSeriousViolations(page);
    }
    await openInsumo(page, insumo.id, insumo.sku);
    await noSeriousViolations(page);
    await page.getByRole("button", { name: "Substituir" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await noSeriousViolations(page);
    await page.keyboard.press("Escape");

    await openAta(page, ata.id, ata.number);
    await expect(itemRow(page, insumo.sku)).toBeVisible();
    await noSeriousViolations(page);
    await page.getByRole("button", { name: "Adicionar item" }).click();
    await page.getByRole("dialog").getByPlaceholder("SKU ou descrição").fill(insumo.sku);
    await expect(page.getByRole("dialog").getByTestId("insumo-option").first()).toBeVisible();
    await noSeriousViolations(page);
  });

  test("AC-0014-30 an item is added with the keyboard alone", async ({ page }) => {
    const grupo = await createGrupo();
    const insumo = await createInsumo(grupo.id);
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await page.getByRole("button", { name: "Adicionar item" }).focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await dialog.getByPlaceholder("SKU ou descrição").focus();
    await page.keyboard.type(insumo.sku);
    await expect(dialog.getByTestId("insumo-option").first()).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(dialog.getByTestId("insumo-option").first()).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(dialog.getByTestId("insumo-chosen")).toContainText(insumo.sku);
    await dialog.getByLabel("Quantidade", { exact: true }).focus();
    await page.keyboard.type("10");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.type("2,5");
    await page.keyboard.press("Enter");
    await expect(itemRow(page, insumo.sku).getByTestId("item-total")).toHaveText("R$ 25,00");
  });
});
