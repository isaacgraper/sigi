import { expect, test } from "@playwright/test";

import { GESTOR, member, signIn } from "./helpers";

test.describe("shell", () => {
  test("AC-0010-52 the root always leads to the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login\?next=%2Fdashboard$/);
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/");
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test("AC-0010-27 a gestor's navigation lists Painel and Membros", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    const nav = page.getByRole("navigation", { name: "Principal" });
    await expect(nav.getByRole("link")).toHaveText(["Painel", "Membros"]);
  });

  test("AC-0010-27 a servidor's navigation lists only Painel", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    const nav = page.getByRole("navigation", { name: "Principal" });
    await expect(nav.getByRole("link")).toHaveText(["Painel"]);
  });

  test("AC-0010-28 the dashboard states who is signed in", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await expect(page.getByTestId("me-email")).toHaveText(GESTOR.email);
    await expect(page.getByTestId("me-perfil")).toHaveText("Gestor");
  });
});
