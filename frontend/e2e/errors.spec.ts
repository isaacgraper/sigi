import { expect, type Page, test } from "@playwright/test";

import { GESTOR, openFromSidebar, signIn } from "./helpers";

// The test frontend runs with SUPPORT_CONTACT_EMAIL=suporte@sc.gov.br; the
// OIDC-only one has none, which is the fallback case.
const CONTACT = "suporte@sc.gov.br";
const oidcOnly = process.env.PLAYWRIGHT_OIDC_ONLY_URL;

async function expectContact(page: Page, reference?: string) {
  const contact = page.getByTestId("contact-gestor");
  await expect(contact).toContainText(`Fale com o gestor: ${CONTACT}`);
  const href = await contact.getByRole("link").getAttribute("href");
  expect(href).toMatch(new RegExp(`^mailto:${CONTACT}\\?`));
  if (reference) expect(decodeURIComponent(href ?? "")).toContain(reference);
}

test.describe("when something goes wrong", () => {
  test("AC-0010-55 an unknown address has a page in pt-BR", async ({ page }) => {
    const response = await page.goto("/nao-existe");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "Página não encontrada" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ir para o painel" })).toHaveAttribute("href", "/dashboard");
    await expectContact(page);
  });

  test("AC-0010-56 a page that fails shows a way out, not a crash", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    // A body the page cannot render: `items` must be a list.
    await page.route("**/api/v1/usuarios?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: null, total: 0, page: 1, size: 20 }),
      }),
    );
    await openFromSidebar(page, "Membros");

    await expect(page.getByRole("heading", { name: "Algo deu errado" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Tentar novamente" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ir para o painel" })).toBeVisible();
    await expectContact(page);
    await expect(page.getByText(/Application error|client-side exception|TypeError/)).toHaveCount(0);
  });

  test("AC-0010-57 a server failure names the gestor and carries the reference", async ({ page }) => {
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "INTERNAL", message: "x", correlation_id: "ref-5xx-123" } }),
      }),
    );
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();

    await expect(page.getByTestId("form-error")).toHaveText(
      "Não foi possível concluir. Tente novamente em instantes.",
    );
    await expectContact(page, "ref-5xx-123");
  });

  test("AC-0010-57 an inactive account names the gestor", async ({ page }) => {
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "USUARIO_INATIVO", message: "Esta conta não está ativa. Procure o gestor da sua unidade." },
        }),
      }),
    );
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expectContact(page);
  });

  test("AC-0010-57 a wrong password does not", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill("senha-errada-mas-longa");
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page.getByTestId("form-error")).toBeVisible();
    await expect(page.getByTestId("contact-gestor")).toHaveCount(0);
  });

  test("AC-0010-57 a link without a token names the gestor", async ({ page }) => {
    await page.goto("/invite");
    await expectContact(page);
  });

  test("AC-0010-57 without a configured contact it points to the gestor", async ({ page }) => {
    test.skip(!oidcOnly, "PLAYWRIGHT_OIDC_ONLY_URL not set");
    await page.goto(`${oidcOnly}/nao-existe`);
    await expect(page.getByTestId("contact-gestor")).toHaveText("Procure o gestor da sua unidade.");
  });

  test("AC-0010-58 copying works without the clipboard API", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openFromSidebar(page, "Membros");
    await page.getByRole("button", { name: "Convidar membro" }).click();
    await page.getByLabel("E-mail institucional").fill(`copia${Date.now().toString(36)}@sc.gov.br`);
    // The invitation asks for the name and the registration too (AC-0010-60).
    await page.getByLabel("Nome completo").fill("Maria da Silva");
    await page.getByLabel("Registro na prefeitura").fill("REG-2026-002");
    await page.getByRole("button", { name: "Convidar", exact: true }).click();
    await page.getByRole("button", { name: "Copiar" }).click();

    await expect(
      page.getByRole("button", { name: "Copiado" }).or(page.getByText("Selecione o link e copie com Ctrl+C.")),
    ).toBeVisible();
  });
});
