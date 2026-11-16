import { expect, type Page } from "@playwright/test";

async function commitRange(page: Page, id: string, value: string) {
  await page.locator(id).evaluate((input, next) => {
    const field = input as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    setter?.call(field, next);
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
  }, value);
}

export class DashboardPage {
  constructor(private readonly page: Page) {}

  async openMorning() {
    await this.page.goto("/");
    await expect(this.page.getByRole("heading", { level: 1 })).toHaveText("WK-008", { timeout: 15000 });
  }

  async generatePlan() {
    const solve = this.page.waitForResponse(
      (response) => response.url().includes("/api/optimization/solve") && response.request().method() === "POST",
    );
    await this.page.getByRole("button", { name: "Generate today's plan" }).click();
    expect((await solve).ok()).toBeTruthy();
  }

  async openPlan() {
    await this.page.goto("/planner");
    await expect(this.page.locator("#crew")).toBeVisible({ timeout: 15000 });
  }

  async setCrew(value: string) {
    const solve = this.page.waitForResponse(
      (response) => response.url().includes("/api/optimization/solve") && response.request().method() === "POST",
    );
    await commitRange(this.page, "#crew", value);
    expect((await solve).ok()).toBeTruthy();
  }

  async prepareSummary() {
    await this.page.goto("/reports");
    const prepare = this.page.getByRole("button", { name: "Prepare summary" });
    await expect(prepare).toBeEnabled({ timeout: 15000 });
    const report = this.page.waitForResponse(
      (response) => response.url().includes("/api/reports/generate") && response.request().method() === "POST",
    );
    await prepare.click();
    expect((await report).ok()).toBeTruthy();
    return this.page.locator("iframe.report-frame");
  }
}
