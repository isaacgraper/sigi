import { expect, test } from "@playwright/test";

import { GESTOR, invite, LONG_ENOUGH, member, noSeriousViolations, openFromSidebar, pathOf, signIn } from "./helpers";

test.describe("AC-0010-44 no serious accessibility violation", () => {
  test("login", async ({ page }) => {
    await page.goto("/login");
    await noSeriousViolations(page);
  });

  test("login with an error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill("senha-errada-mas-longa");
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page.getByTestId("form-error")).toBeVisible();
    await noSeriousViolations(page);
  });

  test("invitation, reset and callback", async ({ page }) => {
    const { link } = await invite("servidor");
    await page.goto(pathOf(link));
    await noSeriousViolations(page);
    await page.goto("/reset-password");
    await noSeriousViolations(page);
    await page.goto("/auth/callback?error=access_denied");
    await noSeriousViolations(page);
  });

  test("dashboard, members and the invite dialog", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await noSeriousViolations(page);
    await openFromSidebar(page, "Membros");
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await noSeriousViolations(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
    await noSeriousViolations(page);
  });
});

test.describe("AC-0011-24 no serious violation in the shell's states", () => {
  test("collapsed sidebar", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Recolher menu lateral" }).click();
    await noSeriousViolations(page);
  });

  test("open drawer", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Abrir menu" }).click();
    await expect(page.getByTestId("drawer")).toBeVisible();
    await noSeriousViolations(page);
  });

  test("user menu and the not-found page", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Menu do usuário" }).click();
    await noSeriousViolations(page);
    await page.goto("/nao-existe");
    await noSeriousViolations(page);
  });

  test("a servidor's dashboard, every section", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    for (const name of ["Atendimento por unidade", "Consumo", "Processos licitatórios", "Itens em falta"]) {
      await page.getByRole("tab", { name }).click();
      await expect(page.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
      await noSeriousViolations(page);
    }
  });

  test("empty table", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.route("**/api/v1/usuarios?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 20 }),
      }),
    );
    await openFromSidebar(page, "Membros");
    await expect(page.getByTestId("empty-state")).toBeVisible();
    await noSeriousViolations(page);
  });
});

test.describe("AC-0010-45 login and activation from the keyboard alone", () => {
  test("login", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").focus();
    await page.keyboard.type(GESTOR.email);
    await page.keyboard.press("Tab");
    await page.keyboard.type(GESTOR.password);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("activation", async ({ page }) => {
    const { link } = await invite("servidor");
    await page.goto(pathOf(link));
    await page.getByLabel("Nova senha").focus();
    await page.keyboard.type(LONG_ENOUGH);
    await page.keyboard.press("Tab"); // the show/hide toggle
    await page.keyboard.press("Tab");
    await page.keyboard.type(LONG_ENOUGH);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("the focused element is visibly marked", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    const outline = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      const style = getComputedStyle(el);
      return style.boxShadow !== "none" || style.outlineStyle !== "none";
    });
    expect(outline).toBe(true);
  });
});
