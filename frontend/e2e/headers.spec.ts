import { expect, test } from "@playwright/test";

const PAGES = ["/login", "/invite", "/reset-password", "/auth/callback?error=x"];

function directive(policy: string, name: string): string {
  return policy.split(";").map((d) => d.trim()).find((d) => d.startsWith(`${name} `)) ?? "";
}

test.describe("AC-0010-53 only the page's own scripts run", () => {
  for (const path of PAGES) {
    test(`${path} carries a nonce policy without unsafe script sources`, async ({ page }) => {
      const response = await page.goto(path);
      const policy = response?.headers()["content-security-policy"] ?? "";
      const scripts = directive(policy, "script-src");
      expect(scripts).toMatch(/'nonce-[A-Za-z0-9+/=]+'/);
      expect(scripts).toContain("'strict-dynamic'");
      expect(scripts).not.toContain("'unsafe-inline'");
      expect(scripts).not.toContain("'unsafe-eval'");
    });
  }

  test("each request gets a fresh nonce", async ({ page }) => {
    const nonceOf = async () =>
      (await page.goto("/login"))?.headers()["content-security-policy"]?.match(/nonce-([^']+)/)?.[1];
    expect(await nonceOf()).not.toBe(await nonceOf());
  });

  // What the policy stops is injected *markup* turning into execution. A
  // script created by code that already runs is trusted under 'strict-dynamic'
  // by design: an attacker with execution is past what any CSP can take back.
  test("an injected javascript: link does not run", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      document.body.insertAdjacentHTML(
        "beforeend",
        '<a id="injected" href="javascript:window.__injected = true">x</a>',
      );
    });
    await page.locator("#injected").click();
    await page.waitForTimeout(500);
    expect(await page.evaluate(() => (window as { __injected?: boolean }).__injected)).toBeUndefined();
  });

  test("an injected event handler does not run", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      document.body.insertAdjacentHTML(
        "beforeend",
        '<img src="/nao-existe.png" onerror="window.__injected = true">',
      );
    });
    await page.waitForTimeout(500);
    expect(await page.evaluate(() => (window as { __injected?: boolean }).__injected)).toBeUndefined();
  });

  test("the page's own scripts still run", async ({ page }) => {
    await page.goto("/login");
    // Hydration happened: the submit button is enabled only once React owns the page.
    await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeEnabled();
  });
});

test.describe("AC-0010-54 no page can be framed or sniffed", () => {
  for (const path of PAGES) {
    test(`${path} forbids framing and sniffing`, async ({ page }) => {
      const headers = (await page.goto(path))?.headers() ?? {};
      expect(directive(headers["content-security-policy"] ?? "", "frame-ancestors")).toBe(
        "frame-ancestors 'none'",
      );
      expect(headers["x-frame-options"]).toBe("DENY");
      expect(headers["x-content-type-options"]).toBe("nosniff");
      const maxAge = Number(headers["strict-transport-security"]?.match(/max-age=(\d+)/)?.[1]);
      expect(maxAge).toBeGreaterThanOrEqual(31536000);
    });
  }

  test("the token pages keep the stricter referrer policy", async ({ page }) => {
    for (const path of ["/invite", "/reset-password"]) {
      const headers = (await page.goto(path))?.headers() ?? {};
      expect(headers["referrer-policy"]).toBe("no-referrer");
    }
    const login = (await page.goto("/login"))?.headers() ?? {};
    expect(login["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  });
});
