import { expect, test } from "@playwright/test";

import { GESTOR, signIn } from "./helpers";

test.describe("session", () => {
  test("AC-0010-42 an API that does not answer on load is reported, not taken as a logout", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    // A reload restores the session through the refresh cookie; no answer comes.
    await page.route("**/api/v1/auth/refresh", (route) => route.abort());
    await page.reload();
    await expect(page.getByTestId("session-failure")).toContainText(
      "Não foi possível concluir. Tente novamente em instantes.",
    );
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("AC-0010-11 a reload keeps the session", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.reload();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByTestId("me-email")).toHaveText(GESTOR.email);
  });

  test("AC-0010-14 logout ends the session and leaves nothing behind", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Menu do usuário" }).click();
    await page.getByRole("menuitem", { name: "Sair" }).click();
    await expect(page).toHaveURL(/\/login$/);
    // Logout replaces the history entry, so Back cannot land on the dashboard.
    await page.goBack();
    await expect(page).not.toHaveURL(/\/dashboard/);
    await expect(page.getByTestId("me-email")).toHaveCount(0);
  });

  test("AC-0010-47 two tabs do not log each other out", async ({ context }) => {
    const first = await context.newPage();
    await signIn(first, GESTOR.email, GESTOR.password);
    const second = await context.newPage();
    await second.goto("/dashboard");
    await expect(second.getByTestId("me-email")).toHaveText(GESTOR.email);

    await Promise.all([first.reload(), second.reload()]);

    await expect(first.getByTestId("me-email")).toHaveText(GESTOR.email);
    await expect(second.getByTestId("me-email")).toHaveText(GESTOR.email);
  });
});
