import { expect, request, test } from "@playwright/test";

import { GESTOR } from "./helpers";

// The provider handshake itself is covered by the backend suite
// (test_auth_oidc.py). Here the API's callback answer is stood in for, so the
// page's behaviour can be checked without an identity provider.
const CALLBACK = "**/api/v1/auth/oidc/callback?*";

test.describe("institutional callback", () => {
  test("AC-0010-09 a provisioned account lands on the dashboard", async ({ page, baseURL }) => {
    const api = await request.newContext({ baseURL });
    const login = await api.post("/api/v1/auth/login", { data: GESTOR });
    const session = await login.json();
    await api.dispose();

    await page.route(CALLBACK, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(session) }),
    );
    await page.goto("/auth/callback?code=abc&state=xyz");
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByTestId("me-email")).toHaveText(GESTOR.email);
  });

  for (const [code, message] of [
    ["USUARIO_NAO_PROVISIONADO", "Seu acesso ainda não foi liberado. Procure o gestor da sua unidade."],
    ["INVALID_STATE", "A tentativa de entrada expirou. Comece novamente."],
    ["INVALID_ASSERTION", "Não foi possível validar a resposta do provedor."],
  ] as const) {
    test(`AC-0010-10 ${code} shows its message and a way back`, async ({ page }) => {
      await page.route(CALLBACK, (route) =>
        route.fulfill({
          status: code === "USUARIO_NAO_PROVISIONADO" ? 403 : 401,
          contentType: "application/json",
          body: JSON.stringify({ error: { code, message } }),
        }),
      );
      await page.goto("/auth/callback?code=abc&state=xyz");
      await expect(page.getByTestId("form-error")).toHaveText(message);
      await expect(page).toHaveURL(/\/auth\/callback$/);
      await page.getByRole("link", { name: "Tentar novamente" }).click();
      await expect(page).toHaveURL(/\/login$/);
    });
  }

  test("AC-0010-48 a cancelled institutional login is explained", async ({ page }) => {
    let called = false;
    await page.route(CALLBACK, (route) => {
      called = true;
      return route.abort();
    });
    await page.goto("/auth/callback?error=access_denied&state=xyz");
    await expect(page.getByTestId("form-error")).toHaveText(
      "A entrada institucional foi cancelada ou não foi autorizada. Tente novamente.",
    );
    await expect(page.getByRole("link", { name: "Tentar novamente" })).toBeVisible();
    expect(called).toBe(false);
  });
});
