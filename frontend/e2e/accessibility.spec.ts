import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { GESTOR, invite, LONG_ENOUGH, pathOf, signIn } from "./helpers";

async function noSeriousViolations(page: Page) {
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
    await page.getByRole("link", { name: "Membros" }).click();
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await noSeriousViolations(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
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
