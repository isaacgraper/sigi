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

test.describe("login refusals the API sends rarely", () => {
  function refuse(status: number, code: string, message: string, headers: Record<string, string> = {}) {
    return {
      status,
      contentType: "application/json",
      headers,
      body: JSON.stringify({ error: { code, message } }),
    };
  }

  test("AC-0010-03 a locked-out address shows the message and waits", async ({ page }) => {
    const message = "Muitas tentativas. Tente novamente em 15 minutos.";
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill(refuse(429, "ATTEMPTS_EXCEEDED", message, { "Retry-After": "900" })),
    );
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();

    await expect(page.getByTestId("form-error")).toHaveText(message);
    await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeDisabled();
  });

  test("AC-0010-50 the per-source ceiling is explained", async ({ page }) => {
    const message = "Muitas requisições. Tente novamente em instantes.";
    await page.route("**/api/v1/auth/login", (route) =>
      route.fulfill(refuse(429, "RATE_LIMITED", message, { "Retry-After": "30" })),
    );
    await page.goto("/login");
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();

    await expect(page.getByTestId("form-error")).toHaveText(message);
    await expect(page.getByLabel("E-mail institucional")).toHaveValue(GESTOR.email);
    await expect(page.getByLabel("Senha", { exact: true })).toHaveValue("");
  });
});

// A second frontend, started with LOCAL_LOGIN_ENABLED=false and
// OIDC_ENABLED=true, because the switches are read by the server (OQ-33).
const oidcOnly = process.env.PLAYWRIGHT_OIDC_ONLY_URL;

test.describe("an OIDC-only deployment", () => {
  test.skip(!oidcOnly, "PLAYWRIGHT_OIDC_ONLY_URL not set");

  test("AC-0010-05 a disabled local login is not offered", async ({ page }) => {
    await page.goto(`${oidcOnly}/login`);
    await expect(page.getByRole("button", { name: "Entrar com conta institucional" })).toBeVisible();
    await expect(page.getByLabel("Senha", { exact: true })).toHaveCount(0);
  });

  test("AC-0010-06 the institutional button starts the provider's flow", async ({ page }) => {
    await page.goto(`${oidcOnly}/login`);
    const started = page.waitForRequest((r) => r.url().endsWith("/api/v1/auth/oidc/authorize"));
    await page.getByRole("button", { name: "Entrar com conta institucional" }).click();
    expect((await started).isNavigationRequest()).toBe(true);
  });
});
