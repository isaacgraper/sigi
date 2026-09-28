import { expect, test } from "@playwright/test";

import { GESTOR, member, signIn } from "./helpers";

test.describe("login", () => {
  test("AC-0010-01 local login lands on the dashboard", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await expect(page.getByTestId("header-identity")).toHaveText(GESTOR.email);
    await expect(page.getByTestId("header-perfil")).toHaveText("Gestor");
  });

  test("AC-0010-02 a refused login shows the API's message", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill("senha-errada-mas-longa");
    await page.getByRole("button", { name: "Entrar", exact: true }).click();

    await expect(page.getByTestId("form-error")).toHaveText("E-mail ou senha inválidos.");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByLabel("Senha", { exact: true })).toHaveValue("");
    await expect(page.getByLabel("E-mail institucional")).toHaveValue(GESTOR.email);
  });

  test("AC-0010-04 an inactive account shows the API's message", async ({ page }) => {
    const blocked = await member("servidor");
    const { asGestor } = await import("./helpers");
    await asGestor("post", `/api/v1/usuarios/${blocked.id}/bloquear`);

    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(blocked.email);
    await page.getByLabel("Senha", { exact: true }).fill(blocked.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();

    await expect(page.getByTestId("form-error")).toHaveText(
      "Esta conta não está ativa. Procure o gestor da sua unidade.",
    );
  });

  test("AC-0010-07 no self-service reset or signup is offered", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByText("Esqueceu a senha? Procure o gestor da sua unidade.")).toBeVisible();
    await expect(page.getByRole("link", { name: /cadastr|redefinir|esqueci/i })).toHaveCount(0);
    const signup = await page.goto("/signup");
    expect(signup?.status()).toBe(404);
  });

  test("AC-0010-08 a submitting form cannot be submitted twice", async ({ page }) => {
    let logins = 0;
    await page.route("**/api/v1/auth/login", async (route) => {
      logins += 1;
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.continue();
    });
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    const submit = page.getByRole("button", { name: "Entrar", exact: true });
    await submit.click();

    await expect(page.getByRole("button", { name: "Entrando..." })).toBeDisabled();
    await expect(page).toHaveURL(/\/dashboard$/);
    expect(logins).toBe(1);
  });

  test("AC-0010-51 a signed-in user is not shown the login page", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/login");
    await expect(page).toHaveURL(/\/dashboard$/);
  });
});
