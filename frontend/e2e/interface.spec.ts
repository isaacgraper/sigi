import { readFileSync } from "node:fs";

import { expect, type Page, test } from "@playwright/test";

import { GESTOR, invite, member, openFromSidebar, pathOf, signIn } from "./helpers";

// SPEC-0011: the frame every page sits in. The test frontend runs with
// SUPPORT_CONTACT_EMAIL=suporte@sc.gov.br.
const CONTACT = "suporte@sc.gov.br";
const VERSION = (JSON.parse(readFileSync("package.json", "utf8")) as { version: string }).version;

const sidebarLinks = (page: Page) =>
  page.getByTestId("sidebar").getByRole("navigation", { name: "Principal" }).getByRole("link");

const breadcrumb = (page: Page) => page.getByRole("navigation", { name: "Trilha de navegação" });

/** The properties the element's current animation keyframes touch, read from the CSSOM. */
async function animatedProperties(page: Page, selector: string) {
  return page.evaluate((sel) => {
    const element = document.querySelector(sel);
    if (!element) throw new Error(`no element for ${sel}`);
    const name = getComputedStyle(element).animationName;
    const properties = new Set<string>();
    const walk = (rules: CSSRuleList) => {
      for (const rule of Array.from(rules)) {
        if (rule instanceof CSSKeyframesRule && rule.name === name) {
          for (const frame of Array.from(rule.cssRules) as CSSKeyframeRule[]) {
            for (let i = 0; i < frame.style.length; i++) properties.add(frame.style[i]);
          }
        } else if ("cssRules" in rule) {
          walk((rule as CSSGroupingRule).cssRules);
        }
      }
    };
    for (const sheet of Array.from(document.styleSheets)) walk(sheet.cssRules);
    return { name, properties: [...properties].sort() };
  }, selector);
}

test.describe("SPEC-0011 the shell", () => {
  test("AC-0011-01 the sidebar lists the perfil's modules in a fixed order", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await expect(sidebarLinks(page)).toHaveText(["Painel", "Membros"]);
    await expect(sidebarLinks(page).first()).toHaveAttribute("aria-current", "page");

    await openFromSidebar(page, "Membros");
    await expect(page).toHaveURL(/\/members$/);
    await expect(sidebarLinks(page).nth(1)).toHaveAttribute("aria-current", "page");
    await expect(sidebarLinks(page).first()).not.toHaveAttribute("aria-current", "page");
  });

  test("AC-0011-01 a servidor's sidebar lists only Painel", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await expect(sidebarLinks(page)).toHaveText(["Painel"]);
  });

  test("AC-0011-02 the sidebar collapses to icons without losing its names", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Recolher menu lateral" }).click();

    const sidebar = page.getByTestId("sidebar");
    await expect(sidebar).toHaveAttribute("data-collapsed", "true");
    expect((await sidebar.boundingBox())?.width).toBe(64);
    // The name is still each link's accessible name...
    await expect(sidebarLinks(page)).toHaveCount(2);
    await expect(page.getByTestId("sidebar").getByRole("link", { name: "Membros" })).toBeVisible();
    // ...and shows on hover.
    const link = page.getByTestId("sidebar").getByRole("link", { name: "Membros" });
    const tooltip = link.getByTestId("nav-tooltip");
    await expect(tooltip).toHaveCSS("opacity", "0");
    await link.hover();
    await expect(tooltip).toHaveCSS("opacity", "1");
    await expect(tooltip).toHaveText("Membros");
  });

  test("AC-0011-02 the name also shows on keyboard focus", async ({ page, browserName }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Recolher menu lateral" }).focus();
    await page.keyboard.press("Enter");
    const link = page.getByTestId("sidebar").getByRole("link", { name: "Membros" });
    const tooltip = link.getByTestId("nav-tooltip");
    await expect(tooltip).toHaveCSS("opacity", "0");
    if (browserName === "webkit") {
      // WebKit does not Tab to plain links by default, and it counts a scripted
      // focus right after a key press as keyboard focus.
      await link.focus();
    } else {
      // A real keyboard move. Firefox matches :focus-visible on a scripted focus
      // only when focus last moved by keyboard, and pressing Enter moves nothing,
      // so `link.focus()` here never showed the name there. "Membros" is the
      // last link before the collapse control.
      await page.keyboard.press("Shift+Tab");
    }
    await expect(link).toBeFocused();
    await expect(tooltip).toHaveCSS("opacity", "1");
  });

  test("AC-0011-03 the collapse is remembered", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Recolher menu lateral" }).click();
    await page.reload();
    await expect(page.getByTestId("me-email")).toBeVisible();
    await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "true");

    await page.goto("/members");
    await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "true");

    await page.getByRole("button", { name: "Expandir menu lateral" }).click();
    await page.reload();
    await expect(page.getByTestId("sidebar")).toHaveAttribute("data-collapsed", "false");
  });

  for (const width of [360, 768]) {
    test(`AC-0011-04 below 1024 px the sidebar becomes a drawer (${width}px)`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await signIn(page, GESTOR.email, GESTOR.password);
      await expect(page.getByTestId("sidebar")).toBeHidden();

      await page.getByRole("button", { name: "Abrir menu" }).click();
      const drawer = page.getByTestId("drawer");
      await expect(drawer).toBeVisible();
      await expect(drawer.getByRole("navigation", { name: "Principal" }).getByRole("link")).toHaveText([
        "Painel",
        "Membros",
      ]);
    });
  }

  test("AC-0011-05 the drawer closes on Escape and returns focus", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await signIn(page, GESTOR.email, GESTOR.password);
    const button = page.getByRole("button", { name: "Abrir menu" });
    await button.click();
    await expect(page.getByTestId("drawer")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("drawer")).toBeHidden();
    await expect(button).toBeFocused();
  });

  test("AC-0011-05 the drawer closes on the backdrop and returns focus", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await signIn(page, GESTOR.email, GESTOR.password);
    const button = page.getByRole("button", { name: "Abrir menu" });
    await button.click();
    await expect(page.getByTestId("drawer")).toBeVisible();
    // The drawer is 288 px wide; the backdrop is the strip to its right.
    await page.mouse.click(340, 400);
    await expect(page.getByTestId("drawer")).toBeHidden();
    await expect(button).toBeFocused();
  });

  test("AC-0011-05 the drawer closes when an entry is followed", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Abrir menu" }).click();
    await page.getByTestId("drawer").getByRole("link", { name: "Membros" }).click();
    await expect(page).toHaveURL(/\/members$/);
    await expect(page.getByTestId("drawer")).toBeHidden();
  });

  test("AC-0011-06 focus stays in the open drawer", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Abrir menu" }).click();
    await expect(page.getByTestId("drawer")).toBeVisible();
    for (const key of ["Tab", "Tab", "Tab", "Tab", "Tab", "Shift+Tab", "Shift+Tab", "Shift+Tab", "Shift+Tab"]) {
      await page.keyboard.press(key);
      const inside = await page.evaluate(
        () => document.querySelector("[data-testid=drawer]")?.contains(document.activeElement) ?? false,
      );
      expect(inside, `focus left the drawer after ${key}`).toBe(true);
    }
  });

  test("AC-0011-07 the header shows where the usuario is", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await expect(breadcrumb(page).getByRole("listitem")).toHaveText(["Painel"]);
    await expect(breadcrumb(page).getByRole("link")).toHaveCount(0);
    await expect(breadcrumb(page).getByText("Painel")).toHaveAttribute("aria-current", "page");

    await openFromSidebar(page, "Membros");
    await expect(breadcrumb(page).getByRole("listitem")).toHaveText(["Painel", "Membros"]);
    await expect(breadcrumb(page).getByRole("link", { name: "Painel" })).toHaveAttribute("href", "/dashboard");
    await expect(breadcrumb(page).getByRole("link", { name: "Membros" })).toHaveCount(0);
    await expect(breadcrumb(page).getByText("Membros")).toHaveAttribute("aria-current", "page");
  });

  test("AC-0011-08 the user menu names who is signed in", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.getByRole("button", { name: "Menu do usuário" }).click();
    const identity = page.getByTestId("menu-identity");
    await expect(identity).toContainText(GESTOR.email);
    await expect(identity).toContainText("Gestor");
    await page.getByRole("menuitem", { name: "Sair" }).click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("AC-0011-09 a skip link comes first, signed out", async ({ page }) => {
    await page.goto("/login");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Ir para o conteúdo" });
    await expect(skip).toBeFocused();
    await expect(skip).toBeVisible();
    await page.keyboard.press("Enter");
    expect(await page.evaluate(() => document.activeElement?.id)).toBe("content");
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.getElementById("content")?.contains(document.activeElement))).toBe(true);
  });

  test("AC-0011-09 a skip link comes first, signed in", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/members");
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Ir para o conteúdo" });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    expect(await page.evaluate(() => document.activeElement?.tagName)).toBe("MAIN");
  });

  test("AC-0011-10 the footer names the version and the contact", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    const footer = page.getByTestId("footer");
    await expect(footer).toContainText("SIGI");
    await expect(footer.getByTestId("footer-version")).toHaveText(`v${VERSION}`);
    await expect(footer.getByTestId("footer-contact")).toHaveText(`Fale com o gestor: ${CONTACT}`);
  });
});

test.describe("SPEC-0011 the page template", () => {
  test("AC-0011-11 every page has one title, and the tab says it", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    for (const path of ["/dashboard", "/members"]) {
      await page.goto(path);
      const heading = page.getByRole("heading", { level: 1 });
      await expect(heading).toHaveCount(1);
      await expect(page).toHaveTitle(`${await heading.textContent()} · SIGI`);
    }
  });

  test("AC-0011-12 the page's primary action sits with its title", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await openFromSidebar(page, "Membros");
    const header = page.getByTestId("page-header");
    await expect(header.getByRole("heading", { level: 1, name: "Membros" })).toBeVisible();
    await expect(header.getByRole("button", { name: "Convidar membro" })).toBeVisible();
  });
});

test.describe("SPEC-0011 the dashboard", () => {
  test("AC-0011-13 the dashboard offers one tile per module", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    const names = (await sidebarLinks(page).allTextContents()).slice(1);
    const tiles = page.getByTestId("module-tile");
    await expect(tiles).toHaveCount(names.length);
    await expect(tiles.first()).toContainText("Membros");
    await expect(tiles.first()).toContainText("Quem tem acesso ao SIGI.");
    await expect(tiles.first()).toHaveAttribute("href", "/members");
    await tiles.first().click();
    await expect(page).toHaveURL(/\/members$/);
  });

  test("AC-0011-14 a perfil with no module is told so", async ({ page }) => {
    const servidor = await member("servidor");
    await signIn(page, servidor.email, servidor.password);
    await expect(page.getByTestId("module-tile")).toHaveCount(0);
    await expect(page.getByTestId("no-modules")).toHaveText(
      "Os módulos do SIGI aparecerão aqui conforme forem liberados.",
    );
  });
});

test.describe("SPEC-0011 signed-out and status pages", () => {
  test("AC-0011-15 the signed-out frame shows the brand beside the form", async ({ page }) => {
    const { link } = await invite("servidor");
    const pages = ["/login", pathOf(link), "/reset-password", "/auth/callback?error=access_denied"];
    for (const path of pages) {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(path);
      const panel = page.getByTestId("brand-panel");
      await expect(panel).toBeVisible();
      await expect(panel).toContainText("SIGI");
      await expect(panel.locator("img[data-illustration=login]")).toBeVisible();

      for (const width of [360, 768]) {
        await page.setViewportSize({ width, height: 900 });
        await expect(panel).toBeHidden();
      }
    }
  });

  test("AC-0011-16 the not-found page carries its illustration", async ({ page }) => {
    await page.goto("/nao-existe");
    const art = page.locator("img[data-illustration=not-found]");
    await expect(art).toBeVisible();
    const heading = page.getByRole("heading", { name: "Página não encontrada" });
    expect((await art.boundingBox())!.y).toBeLessThan((await heading.boundingBox())!.y);
  });

  test("AC-0011-16 the error page carries its illustration", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.route("**/api/v1/usuarios?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: null, total: 0, page: 1, size: 20 }),
      }),
    );
    await openFromSidebar(page, "Membros");
    const art = page.locator("img[data-illustration=error]");
    await expect(art).toBeVisible();
    const heading = page.getByRole("heading", { name: "Algo deu errado" });
    expect((await art.boundingBox())!.y).toBeLessThan((await heading.boundingBox())!.y);
  });

  test("AC-0011-17 illustrations are decoration only", async ({ page }) => {
    for (const path of ["/login", "/nao-existe"]) {
      await page.goto(path);
      const art = page.locator("img[data-illustration]");
      await expect(art).toHaveCount(1);
      await expect(art).toHaveAttribute("alt", "");
      // Hidden from assistive technology: no image in the accessibility tree.
      await expect(page.getByRole("img")).toHaveCount(0);
      await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    }
  });
});

test.describe("SPEC-0011 loading and empty states", () => {
  test("AC-0011-18 a loading page shows its shape, not a blank", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route("**/api/v1/usuarios?*", async (route) => {
      await held;
      await route.continue();
    });
    await openFromSidebar(page, "Membros");

    await expect(page.getByTestId("sidebar")).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Carregando..." })).toHaveCount(1);
    await expect(page.getByTestId("member-row")).toHaveCount(0);

    release();
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Carregando..." })).toHaveCount(0);
  });

  test("AC-0011-18 restoring the session shows the shell's frame", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route("**/api/v1/auth/me", async (route) => {
      await held;
      await route.continue();
    });
    await page.reload();
    await expect(page.getByTestId("page-skeleton")).toBeVisible();
    await expect(page.getByRole("status").filter({ hasText: "Carregando..." })).toHaveCount(1);
    release();
    await expect(page.getByTestId("me-email")).toHaveText(GESTOR.email);
  });

  test("AC-0011-19 an empty table says so, and offers the action", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.route("**/api/v1/usuarios?*", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 20 }),
      }),
    );
    await openFromSidebar(page, "Membros");
    const empty = page.getByTestId("empty-state");
    await expect(empty.locator("img[data-illustration=empty]")).toBeVisible();
    await expect(empty).toContainText("Nenhum membro encontrado.");
    await empty.getByRole("button", { name: "Convidar o primeiro membro" }).click();
    await expect(page.getByRole("dialog", { name: "Convidar membro" })).toBeVisible();
  });

  test("AC-0011-19 past the last page, the way back is offered", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await page.goto("/members?page=9999");
    const empty = page.getByTestId("empty-state");
    await expect(empty).toContainText("Nenhum membro encontrado.");
    await empty.getByRole("link", { name: "Voltar à primeira página" }).click();
    await expect(page.getByTestId("member-row").first()).toBeVisible();
  });

  test("AC-0011-20 a page's code loads when the page is opened", async ({ page }) => {
    const scripts: string[] = [];
    page.on("response", async (response) => {
      if (response.request().resourceType() === "script") scripts.push(await response.text());
    });

    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    expect(scripts.length).toBeGreaterThan(0);
    expect(scripts.filter((body) => body.includes("Convidar membro"))).toHaveLength(0);

    // The control: the same words do arrive once the members page is opened.
    await page.getByLabel("E-mail institucional").fill(GESTOR.email);
    await page.getByLabel("Senha", { exact: true }).fill(GESTOR.password);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await openFromSidebar(page, "Membros");
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(scripts.filter((body) => body.includes("Convidar membro")).length).toBeGreaterThan(0);
  });
});

test.describe("SPEC-0011 motion", () => {
  test("AC-0011-21 reduced motion removes movement", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await signIn(page, GESTOR.email, GESTOR.password);

    await page.getByRole("button", { name: "Menu do usuário" }).click();
    const menu = await animatedProperties(page, "[role=menu]");
    expect(menu.properties).toEqual(["opacity"]);
    await page.keyboard.press("Escape");

    await openFromSidebar(page, "Membros");
    await page.getByRole("button", { name: "Convidar membro" }).click();
    const dialog = await animatedProperties(page, "[role=dialog]");
    expect(dialog.properties).toEqual(["opacity"]);
    await page.keyboard.press("Escape");

    await page.setViewportSize({ width: 360, height: 800 });
    await page.getByRole("button", { name: "Abrir menu" }).click();
    const drawer = await animatedProperties(page, "[data-testid=drawer]");
    expect(drawer.properties).toEqual(["opacity"]);
  });

  test("AC-0011-21 the control: without the preference, dialogs and the drawer move", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await signIn(page, GESTOR.email, GESTOR.password);
    await openFromSidebar(page, "Membros");
    await page.getByRole("button", { name: "Convidar membro" }).click();
    expect((await animatedProperties(page, "[role=dialog]")).properties).toContain("transform");
    await page.keyboard.press("Escape");

    await page.setViewportSize({ width: 360, height: 800 });
    await page.getByRole("button", { name: "Abrir menu" }).click();
    expect((await animatedProperties(page, "[data-testid=drawer]")).properties).toEqual(["transform"]);
  });

  test("AC-0011-22 navigation does not animate", async ({ page }) => {
    await signIn(page, GESTOR.email, GESTOR.password);
    await openFromSidebar(page, "Membros");
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    const running = await page.evaluate(
      () => document.querySelector("main")?.getAnimations({ subtree: true }).length ?? -1,
    );
    expect(running).toBe(0);
  });
});
