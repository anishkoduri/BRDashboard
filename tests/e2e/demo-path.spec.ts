import { expect, test } from "@playwright/test";
import { DashboardPage } from "./dashboard.page";

test.describe("demo path", () => {
  test.describe.configure({ mode: "serial" });

  test("morning, generate, crew cut, and summary", async ({ page }) => {
    test.setTimeout(120000);
    const dashboard = new DashboardPage(page);

    await dashboard.openMorning();
    await dashboard.generatePlan();
    await dashboard.openPlan();
    await dashboard.setCrew("0.4");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText("PC staff hours does not fit PC-022.");
    await expect(page.getByText("Does not fit.")).toBeVisible();
    await expect(page.getByText(/17\s+moved off the week/)).toBeVisible();

    const frame = await dashboard.prepareSummary();
    await expect(frame).toBeVisible();
    const summary = await frame.getAttribute("srcdoc");
    expect(summary).toContain("PC staff hours does not fit PC-022.");
    expect(summary).toContain("Priority lot WK-008");
    expect(summary).toContain("one course");

    await dashboard.openPlan();
    await dashboard.setCrew("1");
    await expect(page.locator("#crew")).toHaveValue("1");
  });
});
