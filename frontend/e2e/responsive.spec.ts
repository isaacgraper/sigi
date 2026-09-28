import { expect, type Page, test } from "@playwright/test";

import { GESTOR, signIn } from "./helpers";

// RNF06 / AC-0010-43. The member table may scroll inside its own frame; the
// page itself never scrolls sideways.
async function noHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
}

for (const width of [360, 768, 1440]) {
  test(`AC-0010-43 every page holds at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/login", "/invite", "/reset-password", "/auth/callback?error=x"]) {
      await page.goto(path);
      await noHorizontalOverflow(page);
    }
    await signIn(page, GESTOR.email, GESTOR.password);
    await noHorizontalOverflow(page);
    await page.goto("/members");
    await expect(page.getByTestId("member-row").first()).toBeVisible();
    await noHorizontalOverflow(page);
  });
}
