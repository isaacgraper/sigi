import { execFileSync } from "node:child_process";
import path from "node:path";

import { expect, type Page, test } from "@playwright/test";

import { createAta, GESTOR, isoDay, member, noSeriousViolations, signIn } from "./helpers";

// SPEC-0008. The daily check is the operator's command, run here as the
// scheduler would; every perfil then reads the same notices under the bell.

const BACKEND = path.resolve(__dirname, "../../backend");

function notificar() {
  execFileSync("poetry", ["run", "python", "-m", "app.cli", "notificar"], { cwd: BACKEND, stdio: "pipe" });
}

async function openBell(page: Page) {
  await page.getByTestId("bell").click();
  await expect(page.getByRole("menu")).toBeVisible();
}

function aviso(page: Page, number: string) {
  return page.locator('[data-testid="aviso"][data-motivo="vai_vencer"]').filter({ hasText: `ATA ${number}` });
}

/** An ATA ending in `days`, raised alone: what was pending is raised first, so this one is the newest. */
async function endingIn(days: number) {
  notificar();
  // A recent orçamento keeps "reajuste a pedir" out of the way.
  const ata = await createAta({ vigencia_fim: isoDay(days), budget_date: isoDay(-10) });
  notificar();
  return ata;
}

test.describe("SPEC-0008 the ATA notices", () => {
  test("AC-0008-04 the bell counts, lists and opens the ATA", async ({ page }) => {
    const ata = await endingIn(30);
    await signIn(page, GESTOR.email, GESTOR.password);

    await expect(page.getByTestId("bell-count")).toBeVisible();
    await openBell(page);
    const item = aviso(page, ata.number);
    await expect(item).toContainText("Vai vencer");
    await expect(item).toHaveAttribute("data-lida", "false");
    await noSeriousViolations(page);
    await item.click();

    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));
    await openBell(page);
    await expect(aviso(page, ata.number)).toHaveAttribute("data-lida", "true");
  });

  test("AC-0008-03 AC-0008-05 the same notice for every perfil, read by each alone", async ({ page, browser }) => {
    const ata = await endingIn(20);
    await signIn(page, GESTOR.email, GESTOR.password);
    await openBell(page);
    await aviso(page, ata.number).click();
    await expect(page).toHaveURL(new RegExp(`/atas/${ata.id}$`));

    const servidor = await member("servidor");
    const other = await browser.newPage();
    await signIn(other, servidor.email, servidor.password);
    await openBell(other);

    await expect(aviso(other, ata.number)).toContainText("Vai vencer");
    await expect(aviso(other, ata.number)).toHaveAttribute("data-lida", "false");
    await other.close();
  });

  test("AC-0008-05 marking every notice read", async ({ page }) => {
    await endingIn(10);
    const auditor = await member("auditor");
    await signIn(page, auditor.email, auditor.password);
    await expect(page.getByTestId("bell-count")).toBeVisible();

    await openBell(page);
    await page.getByRole("menuitem", { name: "Marcar todas como lidas" }).click();

    await expect(page.getByTestId("bell-count")).toHaveCount(0);
  });
});
