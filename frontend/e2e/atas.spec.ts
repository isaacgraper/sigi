import { expect, type Page, type Request, test } from "@playwright/test";

import {
  ataNumber,
  asGestor,
  createAta,
  GESTOR,
  isoDay,
  member,
  noSeriousViolations,
  openFromSidebar,
  signIn,
} from "./helpers";

// SPEC-0013. Each ATA is registered through the API with a unique number, so the
// suite runs again on the same database; the list puts the newest first.

async function asGestorOn(page: Page, path: string) {
  await signIn(page, GESTOR.email, GESTOR.password);
  await page.goto(path);
}

function row(page: Page, number: string) {
  return page.getByTestId("ata-row").filter({ hasText: number });
}

async function openAta(page: Page, id: string, number: string) {
  await page.goto(`/atas/${id}`);
  await expect(page.getByRole("heading", { level: 1, name: `ATA ${number}` })).toBeVisible();
}

function bodyOf(request: Request): Record<string, unknown> {
  return request.postDataJSON() as Record<string, unknown>;
}

async function fillRegistration(page: Page, values: Partial<Record<string, string>> = {}) {
  const v = {
    Número: ataNumber(),
    Objeto: "Luvas de procedimento, caixa com 100",
    Órgão: "Secretaria de Estado da Saúde",
    "CNPJ do fornecedor": "11444777000161",
    "Razão social": "Proteção Hospitalar S.A.",
    "Início da vigência": "2026-03-01",
    "Fim da vigência": "2027-02-28",
    "Valor total (R$)": "380.500,50",
    "Data do orçamento planilhado": "2026-02-10",
    ...values,
  };
  const form = page.locator("main form");
  for (const [label, value] of Object.entries(v)) {
    await form.getByLabel(label, { exact: true }).fill(value!);
  }
  return v.Número;
}

/** "Revisar cadastro", then "Confirmar cadastro": nothing is sent before the second (AC-0013-07). */
async function submitRegistration(page: Page) {
  await page.locator("main form").getByRole("button", { name: "Revisar cadastro" }).click();
  await page.getByRole("button", { name: "Confirmar cadastro" }).click();
}

/** "Cadastrar ATA" opens its own page (AC-0013-07). */
async function openRegistration(page: Page) {
  await page.getByRole("link", { name: "Cadastrar ATA" }).click();
  await expect(page).toHaveURL(/\/atas\/nova$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Nova ATA");
}

async function chooseFilter(page: Page, label: string, option: string) {
  await page.getByLabel(label, { exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

test.describe("SPEC-0013 the ATA screens", () => {
  test("AC-0013-01 every perfil finds ATAs in the sidebar", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    const nav = page.getByRole("navigation", { name: "Principal" });
    await expect(nav.getByRole("link")).toHaveText(["Painel", "ATAs", "Insumos", "Membros"]);
    await openFromSidebar(page, "ATAs");
    await expect(page).toHaveURL(/\/atas$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("ATAs");
    await expect(page).toHaveTitle("ATAs · SIGI");
  });

  test("AC-0013-02 vencimentos and reajustes come first, in one list", async ({ page }) => {
    // Lapses in 30 days, and its reajuste falls due in 20.
    const ata = await createAta({ vigencia_fim: isoDay(30), budget_date: isoDay(20 - 365) });
    await asGestorOn(page, "/atas");

    const list = page.getByTestId("due-list");
    await expect(list.getByRole("heading")).toHaveText("Vencimentos e reajustes");
    // The suite's other ATAs fall due too; this one may be past the first five.
    await expect(list.getByTestId("due-row").first()).toBeVisible();
    const more = list.getByRole("button", { name: /^Mostrar todos/ });
    if (await more.count()) await more.click();
    const rows = list.getByTestId("due-row").filter({ hasText: ata.number });
    await expect(rows).toHaveCount(2);
    const reajuste = rows.and(page.locator("[data-kind=reajuste]"));
    const vencimento = rows.and(page.locator("[data-kind=vencimento]"));
    await expect(reajuste).toContainText("Reajuste");
    await expect(reajuste).toContainText("Seringas descartáveis");
    await expect(reajuste).toContainText(/\d+ dias/);
    // 20 and 30 days are close: amber, not yet red.
    await expect(reajuste).toHaveAttribute("data-urgency", "soon");
    await expect(vencimento).toHaveAttribute("data-urgency", "soon");
    // The counts sit in their own cards above the list.
    await expect(page.getByTestId("due-soon")).toContainText("Em até 30 dias");
    await expect(page.getByTestId("due-soon")).toContainText(/[1-9]\d*/);
    await expect(vencimento).toContainText("Vencimento");
    await expect(vencimento).toContainText(isoDay(30).split("-").reverse().join("/"));

    // Ordered by days remaining: the reajuste, 20 days out, before the vencimento.
    const kinds = await list.getByTestId("due-row").evaluateAll((els) =>
      els.map((el) => [el.getAttribute("data-kind") ?? "", el.textContent ?? ""]),
    );
    const mine = kinds.filter(([, text]) => text.includes(ata.number)).map(([kind]) => kind);
    expect(mine).toEqual(["reajuste", "vencimento"]);

    await vencimento.getByRole("link").click();
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));
  });

  test("AC-0013-02 an overdue row says how long ago", async ({ page }) => {
    // A vigente ATA past its vigência, as the API reports it (AC-0002-09).
    const ata = await createAta();
    const real = ata;
    await page.route("**/api/v1/atas/alertas/renovacao", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ ata: real, days_remaining: -3 }]),
      }),
    );
    await page.route("**/api/v1/atas/alertas/reajuste", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );
    await asGestorOn(page, "/atas");
    await expect(page.getByTestId("due-row")).toHaveCount(1);
    const row = page.getByTestId("due-row");
    await expect(row).toContainText("há 3 dias");
    await expect(row).toContainText("em atraso");
    await expect(row).toHaveAttribute("data-urgency", "overdue");
    await expect(page.getByTestId("due-late")).toHaveText("Em atraso1");
    await expect(page.getByTestId("due-soon")).toHaveText("Em até 30 dias0");
  });

  test("AC-0013-02 more than five show the most urgent first", async ({ page }) => {
    const ata = await createAta();
    const real = ata;
    const rows = [40, 10, 70, 25, 55, 85, 5].map((days) => ({ ata: real, days_remaining: days }));
    await page.route("**/api/v1/atas/alertas/renovacao", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(rows) }),
    );
    await page.route("**/api/v1/atas/alertas/reajuste", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
    );
    await asGestorOn(page, "/atas");
    const due = page.getByTestId("due-row");
    await expect(due).toHaveCount(5);
    await expect(due.first()).toContainText("5 dias");
    await page.getByRole("button", { name: "Mostrar todos (7)" }).click();
    await expect(due).toHaveCount(7);
    await expect(due.last()).toContainText("85 dias");
    // Beyond 30 days there is time: no colour.
    await expect(due.last()).toHaveAttribute("data-urgency", "later");
    await expect(page.getByTestId("due-soon")).toHaveText("Em até 30 dias3");
    await expect(page.getByTestId("due-late")).toHaveText("Em atraso0");
  });

  test("AC-0013-02 nothing due is one line", async ({ page }) => {
    for (const kind of ["renovacao", "reajuste"]) {
      await page.route(`**/api/v1/atas/alertas/${kind}`, (route) =>
        route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
      );
    }
    await asGestorOn(page, "/atas");
    await expect(page.getByTestId("due-list")).toHaveText("Nenhum vencimento ou reajuste próximo.");
  });

  test("AC-0013-03 the list shows every ATA with its columns", async ({ page }) => {
    const ata = await createAta();
    await asGestorOn(page, "/atas");
    await expect(page.getByRole("columnheader")).toHaveText([
      "Número",
      "Objeto",
      "Fornecedor",
      "Vigência",
      "Valor contratado",
      "Status",
      "Reajuste em",
    ]);
    const cells = row(page, ata.number).getByRole("cell");
    await expect(cells.nth(0)).toHaveText(ata.number);
    await expect(cells.nth(2)).toHaveText("MedSul Distribuidora Ltda");
    await expect(cells.nth(3)).toHaveText("02/01/2026 a 01/12/2026");
    await expect(cells.nth(4)).toHaveText("R$ 1.234.567,89");
    await expect(cells.nth(5)).toContainText("Vigente");
    await expect(cells.nth(6)).toHaveText("10/02/2027");

    await row(page, ata.number).getByRole("link", { name: ata.number }).click();
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));
  });

  test("AC-0013-03 more than 25 ATAs come a page at a time", async ({ page }) => {
    const ata = await createAta();
    const real = ata;
    // The page envelope as the API sends it, with a total past one page.
    await page.route("**/api/v1/atas?*", async (route) => {
      const page2 = new URL(route.request().url()).searchParams.get("page");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [real], total: 60, page: Number(page2), size: 25 }),
      });
    });
    await asGestorOn(page, "/atas");
    const pages = page.getByRole("navigation", { name: "Paginação" });
    await expect(pages).toContainText("Página 1 de 3 · 60 ATAs");
    await expect(pages.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await pages.getByRole("button", { name: "Próxima" }).click();
    await expect(page).toHaveURL(/\/atas\?pagina=2$/);
    await expect(pages).toContainText("Página 2 de 3");
  });

  test("AC-0013-04 the list filters by status and situação, kept in the URL", async ({ page }) => {
    await createAta({}, ["suspender"]);
    await asGestorOn(page, "/atas");
    await expect(page.getByTestId("ata-row").first()).toBeVisible();

    const answered = page.waitForRequest((r) => r.url().includes("status=suspensa"));
    await chooseFilter(page, "Status", "Suspensa");
    await answered;
    await expect(page).toHaveURL(/\/atas\?status=suspensa$/);
    const statuses = page.getByTestId("ata-row").getByTestId("ata-status");
    await expect(statuses.first()).toHaveText("Suspensa");
    for (const text of await statuses.allTextContents()) expect(text).toBe("Suspensa");

    await chooseFilter(page, "Situação", "Vigente");
    await expect(page).toHaveURL(/\/atas\?status=suspensa&situacao=vigente$/);
    await page.reload();
    await expect(page.getByLabel("Status", { exact: true })).toHaveText("Suspensa");
    await expect(page.getByLabel("Situação", { exact: true })).toHaveText("Vigente");

    await page.getByRole("button", { name: "Limpar filtros" }).first().click();
    await expect(page).toHaveURL(/\/atas$/);
    await expect(page.getByLabel("Status", { exact: true })).toHaveText("Todos");
  });

  test("AC-0013-05 an empty list says why", async ({ page }) => {
    await page.route("**/api/v1/atas?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 25 }),
      }),
    );
    await asGestorOn(page, "/atas");
    const empty = page.getByTestId("empty-state");
    await expect(empty).toContainText("Nenhuma ATA cadastrada.");
    await expect(empty.getByRole("link", { name: "Cadastrar ATA" })).toBeVisible();

    await page.goto("/atas?status=cancelada");
    await expect(empty).toContainText("Nenhuma ATA com esses filtros.");
    await empty.getByRole("button", { name: "Limpar filtros" }).click();
    await expect(page).toHaveURL(/\/atas$/);
  });

  test("AC-0013-05 a reader's empty list offers no registration", async ({ page }) => {
    await page.route("**/api/v1/atas?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 25 }),
      }),
    );
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await page.goto("/atas");
    await expect(page.getByTestId("empty-state")).toContainText("Nenhuma ATA cadastrada.");
    await expect(page.getByRole("link", { name: "Cadastrar ATA" })).toHaveCount(0);
  });

  test("AC-0013-06 a skeleton covers the list while it loads", async ({ page }) => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route("**/api/v1/atas?*", async (route) => {
      await held;
      await route.continue();
    });
    await asGestorOn(page, "/atas");
    await expect(page.getByRole("status").filter({ hasText: "Carregando..." }).first()).toBeAttached();
    await expect(page.getByTestId("ata-row")).toHaveCount(0);
    release();
    await expect(page.getByTestId("ata-row").first()).toBeVisible();
  });

  test("AC-0013-06 a failed request does not pass for empty", async ({ page }) => {
    await page.route("**/api/v1/atas?*", (route) =>
      route.fulfill({ status: 500, contentType: "text/plain", body: "boom" }),
    );
    await asGestorOn(page, "/atas");
    await expect(page.getByTestId("form-error")).toHaveText(
      "Não foi possível concluir. Tente novamente em instantes.",
    );
    await expect(page.getByTestId("contact-gestor").first()).toBeVisible();
    await expect(page.getByText("Nenhuma ATA cadastrada.")).toHaveCount(0);
  });

  test("AC-0013-07 a gestor registers an ATA", async ({ page }) => {
    await asGestorOn(page, "/atas");
    await openRegistration(page);
    const number = await fillRegistration(page);
    let sent = false;
    page.on("request", (r) => {
      if (r.method() === "POST" && r.url().endsWith("/api/v1/atas")) sent = true;
    });
    await page.locator("main form").getByRole("button", { name: "Revisar cadastro" }).click();

    // Nothing is saved before the gestor confirms what will be saved.
    const review = page.getByTestId("ata-review");
    await expect(page.getByRole("heading", { name: "Confira os dados antes de cadastrar" })).toBeFocused();
    await expect(review).toContainText(number);
    await expect(review).toContainText("R$ 380.500,50");
    await expect(review).toContainText("28/02/2027");
    await expect(review).toContainText("11.444.777/0001-61");
    await expect(review).toContainText("Não informado");
    expect(sent).toBe(false);

    await page.getByRole("button", { name: "Voltar e corrigir" }).click();
    await expect(page.locator("main form").getByLabel("Número", { exact: true })).toHaveValue(number);
    expect(sent).toBe(false);

    const posted = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/api/v1/atas"));
    await submitRegistration(page);
    expect(bodyOf(await posted)).toMatchObject({ number, total_value: "380500.50" });

    await expect(page).toHaveURL(/\/atas\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`ATA ${number}`);
    await expect(page.getByTestId("ata-status")).toHaveText("Vigente");
    await expect(page.getByRole("button", { name: "Ativar" })).toHaveCount(0);
    // The page is the result: no banner says it again.
    await expect(page.getByText(/ATA cadastrada/)).toHaveCount(0);
  });

  test("AC-0013-07 a servidor and an auditor are not offered registration", async ({ page }) => {
    for (const perfil of ["servidor", "auditor"] as const) {
      const reader = await member(perfil);
      await signIn(page, reader.email, reader.password);
      await page.goto("/atas");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("ATAs");
      await expect(page.getByTestId("due-list")).toBeVisible();
      await expect(page.getByRole("link", { name: "Cadastrar ATA" })).toHaveCount(0);
      await page.goto("/atas/nova");
      await expect(page.getByTestId("empty-state")).toContainText("Seu perfil não permite esta ação.");
      await expect(page.locator("main form")).toHaveCount(0);
      // Signing the next perfil in starts from no session at all.
      await page.context().clearCookies();
    }
  });

  test("AC-0013-08 the API's refusal lands on the field it names", async ({ page }) => {
    await asGestorOn(page, "/atas");
    await openRegistration(page);
    const form = page.locator("main form");
    // Two refusals the API's schema reports in one answer: a número past 60
    // characters and a valor that is not a number.
    await fillRegistration(page, { Número: "N".repeat(61), "Valor total (R$)": "mil reais" });
    await submitRegistration(page);

    const numero = form.getByLabel("Número", { exact: true });
    await expect(numero).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByLabel("Valor total (R$)", { exact: true })).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByTestId("field-error")).toHaveCount(2);
    await expect(numero).toBeFocused();
    await expect(form.getByLabel("Objeto", { exact: true })).toHaveValue("Luvas de procedimento, caixa com 100");

    // A CNPJ with wrong check digits is the service's refusal, named on its field.
    await numero.fill(ataNumber());
    await form.getByLabel("Valor total (R$)", { exact: true }).fill("100,00");
    await form.getByLabel("CNPJ do fornecedor", { exact: true }).fill("11444777000162");
    await submitRegistration(page);
    const cnpj = form.getByLabel("CNPJ do fornecedor", { exact: true });
    await expect(cnpj).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByTestId("field-error")).toHaveCount(1);
    await expect(cnpj).toBeFocused();
    await expect(cnpj).toHaveValue("11.444.777/0001-62");
  });

  test("AC-0013-08 a duplicate número is named on Número", async ({ page }) => {
    const ata = await createAta();
    await asGestorOn(page, "/atas");
    await openRegistration(page);
    await fillRegistration(page, { Número: ata.number });
    const form = page.locator("main form");
    await submitRegistration(page);
    await expect(form.locator("#ata-number-error")).toHaveText(
      "Já existe uma ATA com este número. Confira o número ou abra a existente.",
    );
    await expect(form.getByLabel("Número", { exact: true })).toBeFocused();
  });

  test("AC-0013-09 money is typed in pt-BR and sent exactly", async ({ page }) => {
    await asGestorOn(page, "/atas");
    await openRegistration(page);
    const form = page.locator("main form");
    await fillRegistration(page, { "Valor total (R$)": "10,005" });
    await expect(form.getByLabel("CNPJ do fornecedor", { exact: true })).toHaveValue("11.444.777/0001-61");
    // The alphanumeric CNPJ keeps its letters, uppercased (AC-0002-25).
    await form.getByLabel("CNPJ do fornecedor", { exact: true }).fill("12abc34501de35");
    await expect(form.getByLabel("CNPJ do fornecedor", { exact: true })).toHaveValue("12.ABC.345/01DE-35");

    const posted = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/api/v1/atas"));
    await submitRegistration(page);
    expect(bodyOf(await posted).total_value).toBe("10.005");
    await expect(form.getByLabel("Valor total (R$)", { exact: true })).toHaveAttribute("aria-invalid", "true");

    await form.getByLabel("Valor total (R$)", { exact: true }).fill("1.234.567,89");
    const again = page.waitForRequest((r) => r.method() === "POST" && r.url().endsWith("/api/v1/atas"));
    await submitRegistration(page);
    expect(bodyOf(await again).total_value).toBe("1234567.89");
    await expect(page).toHaveURL(/\/atas\/[0-9a-f-]{36}$/);
  });
});

test.describe("SPEC-0013 the ATA page", () => {
  // A zone behind UTC: a date taken for an instant would show the day before.
  test.use({ timezoneId: "America/Los_Angeles" });

  test("AC-0013-10 the ATA page shows the ATA as the API holds it", async ({ page }) => {
    const ata = await createAta({ issued_on: "2026-01-01" });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await expect(page.getByTestId("ata-status")).toHaveText("Vigente");
    const dados = page.getByTestId("ata-dados");
    for (const [label, value] of [
      ["Objeto", "Seringas descartáveis com dispositivo de segurança"],
      ["Órgão", "Secretaria de Estado da Saúde"],
      ["Data de emissão", "01/01/2026"],
      ["Vigência", "02/01/2026 a 01/12/2026"],
      ["Valor total", "R$ 1.234.567,89"],
      ["Valor contratado", "R$ 1.234.567,89"],
      ["Data do orçamento planilhado", "10/02/2026"],
      ["Data de reajuste", "10/02/2027"],
    ]) {
      await expect(dados.locator("div").filter({ has: page.getByText(label, { exact: true }) }).locator("dd")).toHaveText(value);
    }
    await expect(dados).toContainText("MedSul Distribuidora Ltda");
    await expect(dados).toContainText("CNPJ 11.222.333/0001-81");
  });

  test("AC-0013-10 an ATA that does not exist says so", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/atas/00000000-0000-4000-8000-000000000000");
    await expect(page.getByTestId("empty-state")).toContainText("ATA não encontrada.");
    await page.getByRole("link", { name: "Voltar para ATAs" }).click();
    await expect(page).toHaveURL(/\/atas$/);
  });

  test("AC-0013-11 aditivos and reajuste requests are listed", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    const aditivos = page.getByRole("region", { name: "Aditivos" });
    await expect(aditivos.getByRole("columnheader")).toHaveText([
      "Tipo",
      "Acréscimo ou novo fim",
      "Justificativa",
      "Registrado em",
    ]);
    await expect(aditivos).toContainText("Nenhum aditivo registrado.");
    const reajustes = page.getByRole("region", { name: "Pedidos de reajuste" });
    await expect(reajustes.getByRole("columnheader")).toHaveText(["Processo SEI", "Data do pedido", "Registrado em"]);
    await expect(reajustes).toContainText("Nenhum pedido de reajuste registrado.");
  });

  test("AC-0013-12 the moves offered follow the status", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    const actions = page.getByTestId("ata-actions");
    const moves = async (names: string[]) => {
      for (const name of ["Ativar", "Suspender", "Retomar", "Encerrar", "Cancelar"]) {
        await expect(actions.getByRole("button", { name, exact: true })).toHaveCount(names.includes(name) ? 1 : 0);
      }
    };

    await moves(["Suspender", "Encerrar", "Cancelar"]);
    await actions.getByRole("button", { name: "Suspender", exact: true }).click();
    const confirm = page.getByRole("alertdialog");
    await expect(confirm).toContainText(`ATA ${ata.number}.`);
    await confirm.getByRole("button", { name: "Suspender" }).click();
    await expect(page.getByTestId("ata-status")).toHaveText("Suspensa");
    // Announced to assistive technology, never shown as a banner.
    await expect(page.getByRole("status").filter({ hasText: "ATA suspensa." })).toHaveClass(/sr-only/);

    await moves(["Retomar", "Encerrar", "Cancelar"]);
    await actions.getByRole("button", { name: "Encerrar", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Encerrar" }).click();
    await expect(page.getByTestId("ata-status")).toHaveText("Encerrada");
    await moves([]);
  });

  test("AC-0013-12 a move the API refuses is shown and the ATA reloaded", async ({ page }) => {
    const ata = await createAta({});
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    // Someone else suspends it while this page still shows it vigente.
    await asGestor("post", `/api/v1/atas/${ata.id}/suspender`);

    await page.getByTestId("ata-actions").getByRole("button", { name: "Suspender", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Suspender" }).click();
    await expect(page.getByTestId("move-error")).toContainText("Esta ATA não pode passar de");
    await expect(page.getByTestId("ata-status")).toHaveText("Suspensa");
  });

  test("AC-0013-13 cancelling asks why", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await page.getByTestId("ata-actions").getByRole("button", { name: "Cancelar", exact: true }).click();
    const confirm = page.getByRole("alertdialog");
    const submit = confirm.getByRole("button", { name: "Cancelar ATA" });
    await expect(submit).toBeDisabled();
    await confirm.getByLabel("Justificativa", { exact: true }).fill("Registrada em duplicidade.");
    const posted = page.waitForRequest((r) => r.url().endsWith("/cancelar"));
    await submit.click();
    expect(bodyOf(await posted)).toEqual({ justification: "Registrada em duplicidade." });
    await expect(page.getByTestId("ata-status")).toHaveText("Cancelada");
  });

  test("AC-0013-14 a gestor corrects any field, on its own page", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);

    await page.getByRole("link", { name: "Editar" }).click();
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}/editar$`));
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Editar ATA ${ata.number}`);
    let form = page.locator("main form");
    for (const label of ["Número", "CNPJ do fornecedor", "Fim da vigência", "Valor total (R$)"]) {
      await expect(form.getByLabel(label, { exact: true })).toBeEditable();
    }
    await expect(form.getByLabel("Valor total (R$)", { exact: true })).toHaveValue("1.234.567,89");
    await form.getByLabel("Objeto", { exact: true }).fill("Seringas de 10 ml");
    await form.getByLabel("Valor total (R$)", { exact: true }).fill("1.300.000,00");
    const patched = page.waitForRequest((r) => r.method() === "PATCH");
    await form.getByRole("button", { name: "Salvar" }).click();
    expect(bodyOf(await patched)).toEqual({ subject: "Seringas de 10 ml", total_value: "1300000.00" });
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));
    await expect(page.getByTestId("ata-dados")).toContainText("Seringas de 10 ml");
    await expect(page.getByTestId("ata-dados")).toContainText("R$ 1.300.000,00");
    await expect(page.getByText("ATA atualizada.")).toHaveCount(0);

    // "Voltar" returns to the ATA and sends nothing.
    await page.getByRole("link", { name: "Editar" }).click();
    form = page.locator("main form");
    let sent = false;
    page.on("request", (r) => {
      if (r.method() === "PATCH") sent = true;
    });
    await form.getByLabel("Objeto", { exact: true }).fill("Não salvar");
    await form.getByRole("link", { name: "Voltar" }).click();
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));
    await expect(page.getByTestId("ata-dados")).toContainText("Seringas de 10 ml");
    expect(sent).toBe(false);

    // A cancelled ATA is history: no "Editar", and its address says why.
    await asGestor("post", `/api/v1/atas/${ata.id}/cancelar`, { justification: "Teste." });
    await page.reload();
    await expect(page.getByTestId("ata-status")).toHaveText("Cancelada");
    await expect(page.getByRole("link", { name: "Editar" })).toHaveCount(0);
    await page.goto(`/atas/${ata.id}/editar`);
    await expect(page.getByTestId("empty-state")).toContainText("Uma ATA encerrada ou cancelada não pode ser editada.");
  });

  test("AC-0013-15 a gestor records an aditivo", async ({ page }) => {
    const ata = await createAta({ total_value: "100000.00" });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    const aditivos = page.getByRole("region", { name: "Aditivos" });

    await aditivos.getByRole("button", { name: "Registrar aditivo" }).click();
    let dialog = page.getByRole("dialog");
    await dialog.getByLabel("Acréscimo (R$)", { exact: true }).fill("26.000,00");
    await dialog.getByLabel("Justificativa", { exact: true }).fill("Demanda acima do previsto.");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    await expect(dialog.locator("#aditivo-valor_acrescimo-error")).toHaveText(
      "O aditivo passa de 25% do valor original da ATA. Reduza o valor.",
    );

    await dialog.getByLabel("Acréscimo (R$)", { exact: true }).fill("20.000,00");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    await expect(aditivos.getByTestId("aditivo-row")).toHaveCount(1);
    await expect(aditivos.getByTestId("aditivo-row")).toContainText("R$ 20.000,00");
    await expect(page.getByTestId("ata-dados")).toContainText("R$ 120.000,00");

    await aditivos.getByRole("button", { name: "Registrar aditivo" }).click();
    dialog = page.getByRole("dialog");
    await dialog.getByLabel("Prazo").check();
    await dialog.getByLabel("Novo fim da vigência", { exact: true }).fill("2027-06-30");
    await dialog.getByLabel("Justificativa", { exact: true }).fill("Prorrogação.");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    await expect(aditivos.getByTestId("aditivo-row")).toHaveCount(2);
    await expect(page.getByTestId("ata-dados")).toContainText("02/01/2026 a 30/06/2027");
  });

  test("AC-0013-15 an ATA that is not vigente offers no aditivo", async ({ page }) => {
    const ata = await createAta({}, ["suspender"]);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    await expect(page.getByRole("button", { name: "Registrar aditivo" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Registrar pedido de reajuste" })).toHaveCount(0);
  });

  test("AC-0013-16 a gestor records a reajuste request", async ({ page }) => {
    const ata = await createAta({});
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    const reajustes = page.getByRole("region", { name: "Pedidos de reajuste" });

    await reajustes.getByRole("button", { name: "Registrar pedido de reajuste" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("Formato NNNNN.NNNNNN/AAAA-DD");
    await dialog.getByLabel("Processo SEI", { exact: true }).fill("123/2026");
    await dialog.getByLabel("Data do pedido", { exact: true }).fill("2026-10-01");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    await expect(dialog.locator("#reajuste-processo_sei-error")).toHaveText(
      "Número de processo SEI inválido. Use o formato NNNNN.NNNNNN/AAAA-DD.",
    );

    await dialog.getByLabel("Processo SEI", { exact: true }).fill("12345.123456/2026-12");
    await dialog.getByRole("button", { name: "Registrar" }).click();
    await expect(reajustes.getByTestId("reajuste-row")).toContainText("12345.123456/2026-12");
    await expect(reajustes.getByTestId("reajuste-row")).toContainText("01/10/2026");
  });

  test("AC-0013-17 readers read", async ({ page }) => {
    const ata = await createAta({});
    await asGestor("post", `/api/v1/atas/${ata.id}/reajustes`, {
      processo_sei: "12345.123456/2026-12",
      requested_on: "2026-10-01",
    });
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    await openAta(page, ata.id, ata.number);
    await expect(page.getByTestId("ata-dados")).toContainText("Secretaria de Estado da Saúde");
    await expect(page.getByTestId("reajuste-row")).toHaveCount(1);
    await expect(page.getByTestId("ata-actions")).toHaveCount(0);
    await expect(page.getByRole("button", { name: /Registrar|Suspender|Encerrar|Cancelar/ })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Editar" })).toHaveCount(0);
  });
});

test.describe("SPEC-0013 layout", () => {
  for (const width of [360, 768, 1440]) {
    test(`AC-0013-18 every page holds at ${width}px`, async ({ page }) => {
      const ata = await createAta({});
      await page.setViewportSize({ width, height: 900 });
      await signIn(page, GESTOR.email, GESTOR.password);
      const overflow = () =>
        page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

      await page.goto("/atas");
      await expect(page.getByTestId("ata-row").first()).toBeVisible();
      expect(await overflow()).toBeLessThanOrEqual(0);
      await openRegistration(page);
      expect(await overflow()).toBeLessThanOrEqual(0);
      await page.goto(`/atas/${ata.id}/editar`);
      await expect(page.locator("main form")).toBeVisible();
      expect(await overflow()).toBeLessThanOrEqual(0);

      await openAta(page, ata.id, ata.number);
      expect(await overflow()).toBeLessThanOrEqual(0);
      await page.getByRole("button", { name: "Registrar aditivo" }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      expect(await overflow()).toBeLessThanOrEqual(0);
    });
  }

  test("AC-0013-18 every page passes the accessibility check", async ({ page }) => {
    const ata = await createAta({ vigencia_fim: isoDay(30) });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/atas");
    await expect(page.getByTestId("ata-row").first()).toBeVisible();
    await expect(page.getByTestId("due-row").first()).toBeVisible();
    await noSeriousViolations(page);
    await openRegistration(page);
    await noSeriousViolations(page);
    await page.goto(`/atas/${ata.id}/editar`);
    await expect(page.locator("main form")).toBeVisible();
    await noSeriousViolations(page);

    await openAta(page, ata.id, ata.number);
    await noSeriousViolations(page);
    await page.getByTestId("ata-actions").getByRole("button", { name: "Cancelar", exact: true }).click();
    await expect(page.getByRole("alertdialog")).toBeVisible();
    await noSeriousViolations(page);
  });

  test("AC-0013-19 every field says what it is", async ({ page }) => {
    await asGestorOn(page, "/atas/nova");
    const form = page.locator("main form");
    const about = form.getByRole("button", { name: "Sobre CNPJ do fornecedor" });
    await expect(form.getByTestId("info-tip")).toHaveCount(10);
    await expect(about).toHaveAttribute("aria-expanded", "false");

    await about.click();
    await expect(about).toHaveAttribute("aria-expanded", "true");
    await expect(form).toContainText("desde 2026 pode ter letras nos 12 primeiros");
    await page.keyboard.press("Escape");
    await expect(about).toHaveAttribute("aria-expanded", "false");
    await expect(about).toBeFocused();

    // By keyboard, and closed by a choice anywhere else.
    await page.keyboard.press("Enter");
    await expect(form).toContainText("dígitos verificadores");
    await page.getByRole("heading", { level: 1 }).click();
    await expect(about).toHaveAttribute("aria-expanded", "false");

    // The dialogs explain theirs too, and Escape closes the explanation, not the dialog.
    const ata = await createAta();
    await openAta(page, ata.id, ata.number);
    await page.getByRole("button", { name: "Registrar aditivo" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Sobre Justificativa" }).click();
    await expect(dialog).toContainText("Fica no histórico da ATA.");
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();
  });

  test("AC-0013-18 every action can be reached and confirmed with the keyboard", async ({ page }) => {
    const ata = await createAta();
    await signIn(page, GESTOR.email, GESTOR.password);
    await openAta(page, ata.id, ata.number);
    const suspender = page.getByTestId("ata-actions").getByRole("button", { name: "Suspender", exact: true });
    await suspender.focus();
    await page.keyboard.press("Enter");
    const confirm = page.getByRole("alertdialog").getByRole("button", { name: "Suspender" });
    await expect(page.getByRole("alertdialog")).toBeVisible();
    // Focus starts on "Voltar"; Tab reaches the confirmation.
    await page.keyboard.press("Tab");
    await expect(confirm).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("ata-status")).toHaveText("Suspensa");
  });
});
