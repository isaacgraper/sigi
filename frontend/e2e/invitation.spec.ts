import { expect, test } from "@playwright/test";

import { invite, LONG_ENOUGH, pathOf } from "./helpers";

async function fillPasswords(page: import("@playwright/test").Page, first: string, second = first) {
  await page.getByLabel("Nova senha").fill(first);
  await page.getByLabel("Confirme a senha").fill(second);
  await page.getByRole("button", { name: "Ativar conta" }).click();
}

test.describe("invitation", () => {
  test("AC-0010-18 the token leaves the address bar as soon as it is read", async ({ page }) => {
    const { link } = await invite("servidor");
    const response = await page.goto(pathOf(link));
    expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
    await expect(page).toHaveURL(/\/convite$/);
  });

  test("AC-0010-19 activation opens a session", async ({ page }) => {
    const { link } = await invite("auditor");
    await page.goto(pathOf(link));
    await fillPasswords(page, LONG_ENOUGH);
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByTestId("header-perfil")).toHaveText("Auditor");
  });

  test("AC-0010-20 mismatched confirmation is caught before the API", async ({ page }) => {
    const { link } = await invite("servidor");
    let calls = 0;
    await page.route("**/api/v1/convites/ativar", async (route) => {
      calls += 1;
      await route.continue();
    });
    await page.goto(pathOf(link));
    await fillPasswords(page, LONG_ENOUGH, `${LONG_ENOUGH}x`);
    await expect(page.getByTestId("form-error")).toHaveText("As senhas não conferem.");
    expect(calls).toBe(0);
  });

  test("AC-0010-21 a weak password keeps the invitation usable", async ({ page }) => {
    const { link } = await invite("servidor");
    await page.goto(pathOf(link));
    await fillPasswords(page, "curta");
    await expect(page.getByTestId("form-error")).toHaveText(
      "A senha precisa ter ao menos 12 caracteres.",
    );
    await fillPasswords(page, LONG_ENOUGH);
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("AC-0010-22 a spent invitation says what to do", async ({ page, browser }) => {
    const { link } = await invite("servidor");
    const other = await browser.newPage();
    await other.goto(pathOf(link));
    await fillPasswords(other, LONG_ENOUGH);
    await expect(other).toHaveURL(/\/dashboard$/);
    await other.close();

    await page.goto(pathOf(link));
    await fillPasswords(page, LONG_ENOUGH);
    await expect(page.getByTestId("form-error")).toHaveText(
      "Este convite já foi utilizado. Peça um novo ao gestor.",
    );
    await expect(page.getByLabel("Nova senha")).toHaveCount(0);
  });

  test("AC-0010-23 a link without a token is explained", async ({ page }) => {
    await page.goto("/convite");
    await expect(page.getByTestId("form-error")).toHaveText(
      "Link de convite incompleto. Peça um novo ao gestor.",
    );
    await expect(page.getByLabel("Nova senha")).toHaveCount(0);
  });
});
