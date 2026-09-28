import { expect, test } from "@playwright/test";

import { asGestor, member, pathOf, signIn } from "./helpers";

const NEW_ONE = "SenhaNovaOSuficiente-2027";

async function resetLink(): Promise<{ email: string; link: string }> {
  const person = await member("servidor");
  const { status, body } = await asGestor("post", `/api/v1/usuarios/${person.id}/redefinir-senha`);
  expect(status).toBeLessThan(300);
  return { email: person.email, link: (body as { reset_link: string }).reset_link };
}

async function submit(page: import("@playwright/test").Page, value: string) {
  await page.getByLabel("Nova senha").fill(value);
  await page.getByLabel("Confirme a senha").fill(value);
  await page.getByRole("button", { name: "Redefinir senha" }).click();
}

test.describe("reset", () => {
  test("AC-0010-24 the reset token leaves the address bar as soon as it is read", async ({ page }) => {
    const { link } = await resetLink();
    const response = await page.goto(pathOf(link));
    expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
    await expect(page).toHaveURL(/\/redefinir-senha$/);
  });

  test("AC-0010-25 a confirmed reset returns to login, without a session", async ({ page }) => {
    const { email, link } = await resetLink();
    await page.goto(pathOf(link));
    await submit(page, NEW_ONE);

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("status")).toHaveText("Senha redefinida. Entre com a nova senha.");
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?next=/);

    await signIn(page, email, NEW_ONE);
  });

  test("AC-0010-26 a spent reset link says what to do", async ({ page }) => {
    const { link } = await resetLink();
    await page.goto(pathOf(link));
    await submit(page, NEW_ONE);
    await expect(page).toHaveURL(/\/login$/);

    await page.goto(pathOf(link));
    await submit(page, NEW_ONE);
    await expect(page.getByTestId("form-error")).toHaveText(
      "Este link de redefinição já foi usado. Solicite outro.",
    );
    await expect(page.getByLabel("Nova senha")).toHaveCount(0);
  });
});
