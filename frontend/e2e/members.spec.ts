import { expect, type Page, test } from "@playwright/test";

import { asGestor, GESTOR, invite, member, signIn, uniqueEmail } from "./helpers";

function row(page: Page, email: string) {
  return page.getByTestId("member-row").filter({ hasText: email });
}

async function rowAction(page: Page, email: string, action: string) {
  await page.getByRole("button", { name: `Ações para ${email}` }).click();
  await page.getByRole("menuitem", { name: action }).click();
}

async function openMembers(page: Page) {
  await signIn(page, GESTOR.email, GESTOR.password);
  await page.getByRole("link", { name: "Membros" }).click();
  await expect(page.getByRole("heading", { name: "Membros" })).toBeVisible();
}

test.describe("members", () => {
  test("AC-0010-29 the gestor sees the member list", async ({ page }) => {
    await openMembers(page);
    await expect(page.getByRole("columnheader")).toHaveText(
      ["Nome", "E-mail", "Perfil", "Status", "Criado em", "Ações"],
    );
    const first = page.getByTestId("member-row").first();
    await expect(first.getByRole("cell").nth(4)).toHaveText(/^\d{2}\/\d{2}\/\d{4}$/);
  });

  test("AC-0010-29 a null name shows a dash", async ({ page }) => {
    const invited = await invite("servidor");
    await openMembers(page);
    await expect(row(page, invited.email).getByTestId("cell-name")).toHaveText("—");
  });

  test("AC-0010-30 the list is paged by the API, and the address keeps the page", async ({ page }) => {
    for (let i = 0; i < 21; i += 1) await invite("servidor");
    await openMembers(page);
    await page.getByRole("button", { name: "Próxima" }).click();
    await expect(page).toHaveURL(/\/membros\?page=2$/);
    await page.reload();
    await expect(page.getByText(/^Página 2 de/)).toBeVisible();
  });

  test("AC-0010-31 a deactivated member shows the pseudonym", async ({ page }) => {
    const gone = await member("servidor");
    const { body } = await asGestor("post", `/api/v1/usuarios/${gone.id}/desativar`);
    const pseudonym = (body as { pseudonym: string }).pseudonym;
    await openMembers(page);
    const cells = page.locator(`[data-member-id="${gone.id}"]`);
    await expect(cells.getByTestId("cell-name")).toHaveText(pseudonym);
    await expect(cells.getByTestId("cell-email")).toHaveText("—");
  });

  test("AC-0010-32 the auditor reads without acting", async ({ page }) => {
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    await page.getByRole("link", { name: "Membros" }).click();
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Convidar membro" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^Ações para/ })).toHaveCount(0);
  });

  test("AC-0010-33 the servidor is told why, not shown an empty page", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await page.goto("/membros");
    await expect(page.getByText("Seu perfil não permite esta ação.")).toBeVisible();
    await expect(page.getByTestId("member-row")).toHaveCount(0);
  });

  test("AC-0010-34 an empty page is stated", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/membros?page=9999");
    await expect(page.getByRole("cell", { name: "Nenhum membro encontrado." })).toBeVisible();
  });

  test("AC-0010-35 inviting shows the link once", async ({ page }) => {
    const email = uniqueEmail("convidado");
    await openMembers(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
    await page.getByLabel("E-mail institucional").fill(email);
    await page.getByRole("button", { name: "Convidar", exact: true }).click();

    await expect(
      page.getByText("Este link não será mostrado de novo. Envie-o agora à pessoa convidada."),
    ).toBeVisible();
    await expect(page.getByTestId("one-time-link")).toContainText("/convite?token=");
    await expect(page.getByRole("button", { name: "Copiar" })).toBeVisible();
    await page.getByRole("button", { name: "Concluir" }).click();
    await expect(row(page, email).getByTestId("cell-status")).toHaveText("Pendente");
  });

  test("AC-0010-36 an address already registered is refused in the dialog", async ({ page }) => {
    await openMembers(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByRole("button", { name: "Convidar", exact: true }).click();
    await expect(page.getByRole("dialog").getByTestId("form-error")).toContainText(
      "Já existe uma conta para este e-mail.",
    );
  });

  test("AC-0010-36 an off-domain address is refused in the dialog", async ({ page }) => {
    await openMembers(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
    await page.getByLabel("E-mail institucional").fill("alguem@gmail.com");
    await page.getByRole("button", { name: "Convidar", exact: true }).click();
    await expect(page.getByRole("dialog")).toContainText("Use um e-mail institucional.");
  });

  test("AC-0010-49 a malformed field is marked where it is", async ({ page }) => {
    await openMembers(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
    await page.getByLabel("E-mail institucional").fill("nao-e-um-email");
    await page.getByRole("button", { name: "Convidar", exact: true }).click();
    await expect(page.getByTestId("field-error")).not.toBeEmpty();
    await expect(page.getByLabel("E-mail institucional")).toHaveValue("nao-e-um-email");
  });

  test("AC-0010-37 blocking asks first, and cancelling sends nothing", async ({ page }) => {
    const target = await member("servidor");
    await openMembers(page);
    let blocks = 0;
    await page.route("**/bloquear", async (route) => {
      blocks += 1;
      await route.continue();
    });

    await rowAction(page, target.email, "Bloquear");
    await page.getByRole("button", { name: "Cancelar" }).click();
    expect(blocks).toBe(0);

    await rowAction(page, target.email, "Bloquear");
    await page.getByRole("button", { name: "Bloquear" }).click();
    await expect(row(page, target.email).getByTestId("cell-status")).toHaveText("Bloqueado");
    expect(blocks).toBe(1);
  });

  test("AC-0010-38 deactivating says it cannot be undone", async ({ page }) => {
    const target = await member("servidor");
    await openMembers(page);
    await rowAction(page, target.email, "Desativar");
    await expect(page.getByRole("alertdialog")).toContainText("não pode ser desfeita");
    await page.getByRole("button", { name: "Desativar" }).click();
    const cells = page.locator(`[data-member-id="${target.id}"]`);
    await expect(cells.getByTestId("cell-email")).toHaveText("—");
  });

  test("AC-0010-39 the last gestor is protected, and says so", async ({ page }) => {
    await openMembers(page);
    // The seeded gestor is the oldest account, so it sits on the last page.
    const summary = await page.getByText(/^Página \d+ de \d+/).textContent();
    const last = summary?.match(/de (\d+)/)?.[1] ?? "1";
    await page.goto(`/membros?page=${last}`);
    await rowAction(page, GESTOR.email, "Bloquear");
    await page.getByRole("button", { name: "Bloquear" }).click();
    await expect(page.getByTestId("page-error")).toContainText("Esta é a única conta de gestor ativa.");
    await expect(row(page, GESTOR.email).getByTestId("cell-status")).toHaveText("Ativo");
  });

  test("AC-0010-40 triggering a reset shows the link once", async ({ page }) => {
    const target = await member("servidor");
    await openMembers(page);
    await rowAction(page, target.email, "Redefinir senha");
    await page.getByRole("button", { name: "Gerar link" }).click();
    await expect(page.getByText("Este link não será mostrado de novo e expira em 1 hora.")).toBeVisible();
    await expect(page.getByTestId("one-time-link")).toContainText("/redefinir-senha?token=");
  });

  test("AC-0010-41 a deactivated member offers no actions", async ({ page }) => {
    const gone = await member("servidor");
    await asGestor("post", `/api/v1/usuarios/${gone.id}/desativar`);
    await openMembers(page);
    await expect(page.locator(`[data-member-id="${gone.id}"]`).getByRole("button")).toHaveCount(0);
  });
});

test.describe("session, through the members page", () => {
  test("AC-0010-13 a dead session returns to login with the reason", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    // The refresh cookie is gone, and the access token has just expired.
    await page.context().clearCookies();
    await page.route("**/api/v1/usuarios?*", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "TOKEN_EXPIRED", message: "Sua sessão expirou." } }),
      }),
    );
    await page.getByRole("link", { name: "Membros" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("status")).toHaveText("Sua sessão não é mais válida. Entre novamente.");
  });

  test("AC-0010-15 a protected page asks for login and returns afterwards", async ({ page }) => {
    await page.goto("/membros?page=2");
    await expect(page).toHaveURL(/\/login\?next=/);
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page).toHaveURL(/\/membros\?page=2$/);
  });
});
