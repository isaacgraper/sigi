import { expect, test } from "@playwright/test";

import { member, noSeriousViolations, signIn } from "./helpers";

// SPEC-0008 AC-0008-07: each member chooses their own e-mail summary.

test.describe("SPEC-0008 Configurações", () => {
  test("AC-0008-07 from the user menu, weekly on Mondays until changed", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);

    await page.getByRole("button", { name: "Menu do usuário" }).click();
    await page.getByRole("menuitem", { name: "Configurações" }).click();

    await expect(page).toHaveURL(/\/configuracoes$/);
    await expect(page.getByRole("heading", { level: 1, name: "Configurações" })).toBeVisible();
    await expect(page.getByRole("radio", { name: /Semanal/ })).toBeChecked();
    await expect(page.getByLabel("Dia da semana")).toHaveText("Segunda-feira");
    await noSeriousViolations(page);
  });

  test("AC-0008-07 a choice is saved and read back", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await page.goto("/configuracoes");

    await page.getByRole("radio", { name: /Semanal/ }).check();
    await page.getByLabel("Dia da semana").click();
    await page.getByRole("option", { name: "Sexta-feira" }).click();
    await page.getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByText("Preferência salva.")).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("Dia da semana")).toHaveText("Sexta-feira");

    await page.getByRole("radio", { name: /Nenhum/ }).check();
    await expect(page.getByLabel("Dia da semana")).toHaveCount(0);
    await page.getByRole("button", { name: "Salvar" }).click();
    await expect(page.getByText("Preferência salva.")).toBeVisible();
    await page.reload();
    await expect(page.getByRole("radio", { name: /Nenhum/ })).toBeChecked();
  });
});
