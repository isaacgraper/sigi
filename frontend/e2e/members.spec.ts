import { expect, type Page, test } from "@playwright/test";

import { asGestor, GESTOR, invite, LONG_ENOUGH, member, openFromSidebar, signIn, uniqueEmail } from "./helpers";

function row(page: Page, email: string) {
  return page.getByTestId("member-row").filter({ hasText: email });
}

// The button is named after the person's name when there is one (C4), and every
// invited member in this suite has the same, so the row is found by its e-mail.
async function openRowMenu(page: Page, email: string) {
  await row(page, email).getByRole("button", { name: /^Ações para/ }).click();
}

async function rowAction(page: Page, email: string, action: string) {
  await openRowMenu(page, email);
  await page.getByRole("menuitem", { name: action }).click();
}

/** Opens the invite dialog and fills it as AC-0010-60 asks: e-mail, name and registration. */
async function fillInvite(page: Page, email: string, perfil?: string) {
  await page.getByRole("button", { name: "Convidar membro" }).click();
  await page.getByLabel("E-mail institucional").fill(email);
  await page.getByLabel("Nome completo").fill("Maria da Silva");
  await page.getByLabel("Registro na prefeitura").fill("REG-2026-001");
  if (perfil) {
    await page.getByLabel("Perfil").click();
    await page.getByRole("option", { name: perfil }).click();
  }
}

/** Every control is drawn inside the dialog, however long the link it shows. */
async function expectInsideDialog(page: Page, names: string[]) {
  const dialog = await page.getByRole("dialog").boundingBox();
  expect(dialog).not.toBeNull();
  for (const name of names) {
    const box = await page.getByRole("button", { name, exact: true }).boundingBox();
    expect(box, name).not.toBeNull();
    expect(box!.x, name).toBeGreaterThanOrEqual(dialog!.x);
    expect(box!.x + box!.width, name).toBeLessThanOrEqual(dialog!.x + dialog!.width);
  }
}

async function openMembers(page: Page) {
  await signIn(page, GESTOR.email, GESTOR.password);
  await openFromSidebar(page, "Membros");
  await expect(page.getByRole("heading", { name: "Membros" })).toBeVisible();
}

test.describe("members", () => {
  test("AC-0010-29 the gestor sees the member list", async ({ page }) => {
    await openMembers(page);
    await expect(page.getByRole("columnheader")).toHaveText(
      ["Nome", "E-mail", "Registro", "Perfil", "Status", "Criado em", "Ações"],
    );
    const first = page.getByTestId("member-row").first();
    await expect(first.getByRole("cell").nth(5)).toHaveText(/^\d{2}\/\d{2}\/\d{4}$/);
  });

  test("AC-0010-29 a null name and a null registration show a dash", async ({ page }) => {
    // The seeded gestor predates SPEC-0001 v1.7, so it has neither.
    await openMembers(page);
    const summary = await page.getByText(/^Página \d+ de \d+/).textContent();
    await page.goto(`/members?page=${summary?.match(/de (\d+)/)?.[1] ?? "1"}`);
    const seeded = row(page, GESTOR.email);
    await expect(seeded.getByTestId("cell-name")).toHaveText("—");
    await expect(seeded.getByTestId("cell-registration")).toHaveText("—");
  });

  test("AC-0010-29 an invited member shows the name and the registration", async ({ page }) => {
    const invited = await invite("servidor");
    await openMembers(page);
    const shown = row(page, invited.email);
    await expect(shown.getByTestId("cell-name")).toHaveText("Pessoa Convidada");
    await expect(shown.getByTestId("cell-registration")).toHaveText(/^REG-\d+$/);
  });

  test("AC-0010-30 the list is paged by the API, and the address keeps the page", async ({ page }) => {
    for (let i = 0; i < 21; i += 1) await invite("servidor");
    await openMembers(page);
    await page.getByRole("button", { name: "Próxima" }).click();
    await expect(page).toHaveURL(/\/members\?page=2$/);
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
    await openFromSidebar(page, "Membros");
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Convidar membro" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^Ações para/ })).toHaveCount(0);
  });

  test("AC-0010-33 the servidor is told why, not shown an empty page", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await page.goto("/members");
    await expect(page.getByText("Seu perfil não permite esta ação.")).toBeVisible();
    await expect(page.getByTestId("member-row")).toHaveCount(0);
  });

  test("AC-0010-34 an empty page is stated", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/members?page=9999");
    await expect(page.getByRole("cell", { name: "Nenhum membro encontrado." })).toBeVisible();
  });

  test("AC-0010-35 inviting shows the link once", async ({ page }) => {
    const email = uniqueEmail("convidado");
    await openMembers(page);
    await fillInvite(page, email);
    await page.getByRole("button", { name: "Convidar", exact: true }).click();

    await expect(
      page.getByText("Este link não será mostrado de novo. Envie-o agora à pessoa convidada."),
    ).toBeVisible();
    await expect(page.getByTestId("one-time-link")).toContainText("/invite?token=");
    await expect(page.getByRole("button", { name: "Copiar" })).toBeVisible();
    await expectInsideDialog(page, ["Copiar", "Concluir"]);
    await page.getByRole("button", { name: "Concluir" }).click();
    await expect(row(page, email).getByTestId("cell-status")).toHaveText("Pendente");
  });

  test("AC-0010-36 an address already registered is refused in the dialog", async ({ page }) => {
    await openMembers(page);
    await fillInvite(page, GESTOR.email);
    await page.getByRole("button", { name: "Convidar", exact: true }).click();
    await expect(page.getByRole("dialog").getByTestId("form-error")).toContainText(
      "Já existe uma conta para este e-mail.",
    );
  });

  test("AC-0010-36 an off-domain address is refused in the dialog", async ({ page }) => {
    await openMembers(page);
    await fillInvite(page, "alguem@gmail.com");
    await page.getByRole("button", { name: "Convidar", exact: true }).click();
    await expect(page.getByRole("dialog")).toContainText("Use um e-mail institucional.");
  });

  test("AC-0010-49 a malformed field is marked where it is", async ({ page }) => {
    await openMembers(page);
    await fillInvite(page, "nao-e-um-email");
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
    await page.goto(`/members?page=${last}`);
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
    await expect(page.getByTestId("one-time-link")).toContainText("/reset-password?token=");
    await expectInsideDialog(page, ["Copiar"]);
  });

  test("AC-0010-61 a pending member can be given a new invitation link", async ({ page }) => {
    const invited = await invite("servidor");
    await openMembers(page);
    let reissues = 0;
    await page.route("**/reemitir-convite", async (route) => {
      reissues += 1;
      await route.continue();
    });

    await openRowMenu(page, invited.email);
    await expect(page.getByRole("menuitem")).toHaveText(["Gerar novo convite", "Desativar"]);
    await page.getByRole("menuitem", { name: "Gerar novo convite" }).click();
    await page.getByRole("button", { name: "Cancelar" }).click();
    expect(reissues).toBe(0);

    await rowAction(page, invited.email, "Gerar novo convite");
    await page.getByRole("button", { name: "Gerar link" }).click();
    await expect(
      page.getByText("Este link não será mostrado de novo. O link anterior deixa de funcionar."),
    ).toBeVisible();
    const fresh = await page.getByTestId("one-time-link").textContent();
    expect(fresh).toContain("/invite?token=");
    expect(fresh).not.toBe(invited.link);
    await expectInsideDialog(page, ["Copiar"]);
    expect(reissues).toBe(1);

    // The first link no longer activates; the new one does.
    const stale = await page.request.post("/api/v1/convites/ativar", {
      data: { token: new URL(invited.link).searchParams.get("token"), password: LONG_ENOUGH },
    });
    expect(stale.status()).toBe(409);
    const works = await page.request.post("/api/v1/convites/ativar", {
      data: { token: new URL(fresh!).searchParams.get("token"), password: LONG_ENOUGH },
    });
    expect(works.status()).toBe(200);
  });

  test("AC-0010-60 the invite dialog asks for the name and the registration", async ({ page }) => {
    await openMembers(page);
    await page.getByRole("button", { name: "Convidar membro" }).click();
    let invites = 0;
    await page.route("**/api/v1/usuarios", async (route) => {
      if (route.request().method() === "POST") invites += 1;
      await route.continue();
    });
    for (const label of ["E-mail institucional", "Nome completo", "Registro na prefeitura", "Perfil"]) {
      await expect(page.getByLabel(label)).toBeVisible();
    }

    await page.getByRole("button", { name: "Convidar", exact: true }).click();

    await expect(page.getByTestId("field-error")).toHaveText([
      "Campo obrigatório.",
      "Campo obrigatório.",
      "Campo obrigatório.",
    ]);
    expect(invites).toBe(0);
  });

  test("AC-0010-59 unblocking asks for a justification, and cancelling sends nothing", async ({ page }) => {
    const target = await member("servidor");
    await asGestor("post", `/api/v1/usuarios/${target.id}/bloquear`);
    await openMembers(page);
    let unblocks = 0;
    await page.route("**/desbloquear", async (route) => {
      unblocks += 1;
      await route.continue();
    });
    await expect(row(page, target.email).getByTestId("cell-status")).toHaveText("Bloqueado");
    // A blocked member offers no block and no reset (AC-0010-41).
    await openRowMenu(page, target.email);
    await expect(page.getByRole("menuitem", { name: "Bloquear", exact: true })).toHaveCount(0);
    await expect(page.getByRole("menuitem", { name: "Redefinir senha" })).toHaveCount(0);
    await page.getByRole("menuitem", { name: "Desbloquear" }).click();

    await page.getByRole("button", { name: "Cancelar" }).click();
    expect(unblocks).toBe(0);

    await rowAction(page, target.email, "Desbloquear");
    await page.getByRole("button", { name: "Desbloquear", exact: true }).click();
    // The API's own refusal is shown beside the field.
    await expect(page.getByTestId("field-error")).not.toBeEmpty();
    await expect(row(page, target.email).getByTestId("cell-status")).toHaveText("Bloqueado");

    await page.getByLabel("Justificativa").fill("Bloqueio feito por engano.");
    await page.getByRole("button", { name: "Desbloquear", exact: true }).click();
    await expect(row(page, target.email).getByTestId("cell-status")).toHaveText("Ativo");
    expect(unblocks).toBe(2);
  });

  test("AC-0010-59 an account that is no longer blocked is explained", async ({ page }) => {
    const target = await member("servidor");
    await asGestor("post", `/api/v1/usuarios/${target.id}/bloquear`);
    await openMembers(page);
    await rowAction(page, target.email, "Desbloquear");
    // Someone else unblocks it first.
    await asGestor("post", `/api/v1/usuarios/${target.id}/desbloquear`, { justification: "Outro gestor." });
    await page.getByLabel("Justificativa").fill("Tarde demais.");
    await page.getByRole("button", { name: "Desbloquear", exact: true }).click();
    await expect(page.getByTestId("unblock-error")).toHaveText("Esta conta não está bloqueada.");
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
    await openFromSidebar(page, "Membros");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("status")).toHaveText("Sua sessão não é mais válida. Entre novamente.");
  });

  test("AC-0010-15 a protected page asks for login and returns afterwards", async ({ page }) => {
    await page.goto("/members?page=2");
    await expect(page).toHaveURL(/\/login\?next=/);
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page).toHaveURL(/\/members\?page=2$/);
  });
});
