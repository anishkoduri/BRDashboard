import { expect, test } from "@playwright/test";

test.describe("key screens", () => {
  test("morning names the priority lot", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("WK-008", { timeout: 15000 });
    await expect(page.getByRole("button", { name: "Generate today's plan" })).toBeVisible();
  });

  test("plan shows the crew control", async ({ page }) => {
    await page.goto("/planner");
    await expect(page.locator("#crew")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("summary offers prepare", async ({ page }) => {
    await page.goto("/reports");
    await expect(page.getByRole("button", { name: "Prepare summary" })).toBeVisible({ timeout: 15000 });
  });

  test("decisions names the three columns", async ({ page }) => {
    await page.goto("/decisions");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Current, proposed, and hypothetical", { timeout: 15000 });
  });

  test("evidence names what is known", async ({ page }) => {
    await page.goto("/evidence");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("What is known", { timeout: 15000 });
  });
});
