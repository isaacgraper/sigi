import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { GESTOR, invite, LONG_ENOUGH, member, openFromSidebar, pathOf, signIn } from "./helpers";

async function noSeriousViolations(page: Page) {
  // Measure what settles on screen, not a frame of a fade: text halfway through
  // an opacity transition reads as low contrast. Endless ones (a skeleton's
  // pulse) are left alone, since they never finish.
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((a) => a.effect?.getComputedTiming().endTime !== Infinity)
        .map((a) => a.finished.catch(() => undefined)),
    ),
  );
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(", ")}`)).toEqual([]);
}

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
